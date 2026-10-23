import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    RiskLevel,
    ActionStatus,
    ApprovalStatus,
    ToolExecutionResult
)
from app.models.action import ActionProposal, AuditLog, sanitize_parameters, ensure_json_serializable
from app.services.tools.registry import tool_registry
from app.services.tools.security_guard import tool_security_guard

def utcnow():
    return datetime.now(timezone.utc)

class ActionManager:
    """Central manager orchestrating permission checks, action proposals, approvals, execution, and audit logging."""

    def __init__(self):
        self.registry = tool_registry
        self.security_guard = tool_security_guard

    async def propose_action(
        self,
        user_id: uuid.UUID,
        tool_name: str,
        action_type: str,
        title: str,
        description: Optional[str],
        parameters: Dict[str, Any],
        db: AsyncSession,
        auto_execute_if_safe: bool = True
    ) -> Tuple[ActionProposal, bool, Optional[ToolExecutionResult]]:
        """
        Flow:
        Agent wants action -> 5-Step Security Evaluation -> Action proposal -> User confirmation (if needed) -> Execution -> Audit log.
        """
        tool = self.registry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' is not registered in NEXUS.")

        # 1. 5-Step Security Evaluation (User, Tool, Schema, Risk, Confirmation)
        validation = self.security_guard.evaluate(
            user=user_id,
            tool=tool,
            action=action_type,
            parameters=parameters,
            caller_is_llm=True
        )

        if not validation.allowed:
            raise PermissionError(f"Security validation failed: {validation.failure_reason}")

        validated_params = tool.validate_parameters(validation.sanitized_parameters)
        requires_confirmation = validation.requires_confirmation or (validation.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL])

        proposal = ActionProposal(
            user_id=user_id,
            action_type=action_type,
            tool_name=tool.name,
            title=title,
            description=description,
            parameters=ensure_json_serializable(validated_params),
            risk_level=validation.risk_level.value,
            requires_confirmation=requires_confirmation,
            status=ActionStatus.PENDING.value if requires_confirmation else ActionStatus.APPROVED.value
        )
        db.add(proposal)
        await db.flush()

        # 3. If confirmation required, return proposal immediately in pending state
        if requires_confirmation or not auto_execute_if_safe:
            return proposal, False, None

        # 4. Safe action: Auto-execute immediately
        result = await tool.execute(
            action=action_type,
            user_id=user_id,
            params=validated_params,
            db=db
        )

        proposal.status = ActionStatus.EXECUTED.value if result.success else ActionStatus.FAILED.value
        proposal.result = ensure_json_serializable(result.model_dump(mode="json"))
        proposal.error_message = result.error
        proposal.executed_at = utcnow()

        # 5. Record in Audit Log (Sanitizing secrets)
        audit = AuditLog(
            user_id=user_id,
            action=action_type,
            tool=tool.name,
            parameters=sanitize_parameters(validated_params),
            approval_status=ApprovalStatus.AUTO_APPROVED.value,
            status="success" if result.success else "failed",
            result=ensure_json_serializable(result.model_dump(mode="json")),
            error_message=result.error,
            proposal_id=proposal.id
        )
        db.add(audit)
        await db.flush()

        return proposal, True, result

    async def approve_action(
        self,
        proposal_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Tuple[ActionProposal, ToolExecutionResult]:
        """User explicitly approves a pending action proposal -> executes tool and logs audit record."""
        stmt = select(ActionProposal).where(
            ActionProposal.id == proposal_id,
            ActionProposal.user_id == user_id
        )
        res = await db.execute(stmt)
        proposal = res.scalar_one_or_none()
        if not proposal:
            raise LookupError(f"Action proposal '{proposal_id}' not found.")

        if proposal.status != ActionStatus.PENDING.value:
            raise ValueError(f"Cannot approve action proposal with status '{proposal.status}'. Must be 'pending'.")

        tool = self.registry.get(proposal.tool_name)
        if not tool:
            raise ValueError(f"Tool '{proposal.tool_name}' is not registered.")

        # Execute Tool Action
        result = await tool.execute(
            action=proposal.action_type,
            user_id=user_id,
            params=proposal.parameters,
            db=db
        )

        # Update Proposal
        proposal.status = ActionStatus.EXECUTED.value if result.success else ActionStatus.FAILED.value
        proposal.result = ensure_json_serializable(result.model_dump(mode="json"))
        proposal.error_message = result.error
        proposal.executed_at = utcnow()

        # Audit Log Record (with sanitized secrets)
        audit = AuditLog(
            user_id=user_id,
            action=proposal.action_type,
            tool=proposal.tool_name,
            parameters=sanitize_parameters(proposal.parameters),
            approval_status="approved",
            status="success" if result.success else "failed",
            result=ensure_json_serializable(result.model_dump(mode="json")),
            error_message=result.error,
            proposal_id=proposal.id
        )
        db.add(audit)
        await db.flush()

        return proposal, result

    async def reject_action(
        self,
        proposal_id: uuid.UUID,
        reason: Optional[str],
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> ActionProposal:
        """User rejects a pending action proposal -> records rejection in audit log."""
        stmt = select(ActionProposal).where(
            ActionProposal.id == proposal_id,
            ActionProposal.user_id == user_id
        )
        res = await db.execute(stmt)
        proposal = res.scalar_one_or_none()
        if not proposal:
            raise LookupError(f"Action proposal '{proposal_id}' not found.")

        if proposal.status != ActionStatus.PENDING.value:
            raise ValueError(f"Cannot reject action proposal with status '{proposal.status}'. Must be 'pending'.")

        proposal.status = ActionStatus.REJECTED.value
        proposal.rejection_reason = reason or "Rejected by user"

        # Audit Log Record
        audit = AuditLog(
            user_id=user_id,
            action=proposal.action_type,
            tool=proposal.tool_name,
            parameters=sanitize_parameters(proposal.parameters),
            approval_status="rejected",
            status="rejected",
            error_message=reason or "Rejected by user",
            proposal_id=proposal.id
        )
        db.add(audit)
        await db.flush()

        return proposal

    async def list_proposals(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        status_filter: Optional[str] = None
    ) -> List[ActionProposal]:
        stmt = select(ActionProposal).where(ActionProposal.user_id == user_id)
        if status_filter:
            stmt = stmt.where(ActionProposal.status == status_filter)
        stmt = stmt.order_by(ActionProposal.created_at.desc())
        res = await db.execute(stmt)
        return res.scalars().all()

    async def list_audit_logs(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 50
    ) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return res.scalars().all()

action_manager = ActionManager()
