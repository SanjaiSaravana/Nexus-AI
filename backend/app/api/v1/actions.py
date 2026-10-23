import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.tool import (
    ToolDefinitionResponse,
    ActionProposalCreate,
    ActionProposalResponse,
    ActionApprovalRequest,
    AuditLogResponse
)
from app.services.tools.action_manager import action_manager
from app.services.tools.registry import tool_registry

router = APIRouter()

@router.get("/tools", response_model=List[ToolDefinitionResponse])
async def list_available_tools(
    current_user: User = Depends(get_current_user)
):
    """Lists all security-scoped tools with input/output schemas and permission requirements."""
    return tool_registry.list_definitions()

@router.post("/propose", response_model=ActionProposalResponse, status_code=status.HTTP_201_CREATED)
async def propose_agent_action(
    request: ActionProposalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Proposes an action. If safe, auto-executes; if sensitive/high-risk, creates a pending proposal awaiting confirmation."""
    try:
        proposal, executed, result = await action_manager.propose_action(
            user_id=current_user.id,
            tool_name=request.tool_name,
            action_type=request.action_type,
            title=request.title,
            description=request.description,
            parameters=request.parameters,
            db=db,
            auto_execute_if_safe=True
        )
        return proposal
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

@router.get("/proposals", response_model=List[ActionProposalResponse])
async def list_action_proposals(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists action proposals for authenticated user."""
    return await action_manager.list_proposals(user_id=current_user.id, db=db, status_filter=status_filter)

@router.post("/proposals/{proposal_id}/approve", response_model=ActionProposalResponse)
async def approve_action_proposal(
    proposal_id: uuid.UUID,
    payload: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """User approves a pending action proposal -> executes tool and logs to audit trail."""
    try:
        proposal, result = await action_manager.approve_action(
            proposal_id=proposal_id,
            user_id=current_user.id,
            db=db
        )
        return proposal
    except LookupError as not_found_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(not_found_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

@router.post("/proposals/{proposal_id}/reject", response_model=ActionProposalResponse)
async def reject_action_proposal(
    proposal_id: uuid.UUID,
    payload: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """User rejects a pending action proposal -> records rejection in audit log."""
    try:
        reason = payload.get("reason") if payload else "Rejected by user"
        proposal = await action_manager.reject_action(
            proposal_id=proposal_id,
            reason=reason,
            user_id=current_user.id,
            db=db
        )
        return proposal
    except LookupError as not_found_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(not_found_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves immutable audit logs for the authenticated user (sensitive secrets sanitized)."""
    return await action_manager.list_audit_logs(user_id=current_user.id, db=db, limit=limit)
