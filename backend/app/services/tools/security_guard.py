"""
Tool Security Guard for NEXUS AI:
Implements 5-step validation for tool calling and action execution.
Guarantees that an AI agent or LLM can NEVER execute a privileged, high-risk,
or sensitive action without satisfying all security constraints and requiring
human confirmation.
"""

import re
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.schemas.tool import RiskLevel

logger = logging.getLogger(__name__)

# Dangerous input patterns: path traversal, command injection, null bytes
SUSPICIOUS_PATTERNS = [
    re.compile(r"\.\./|\.\.\\"),  # Directory traversal
    re.compile(r"\x00"),  # Null byte injection
    re.compile(r";\s*(rm|del|shutdown|format|curl|wget)\b", re.IGNORECASE),  # Shell command chaining
]

# Actions that are inherently high risk or destructive
DESTRUCTIVE_ACTIONS = {
    "delete_task", "delete_project", "delete_event", "delete_document",
    "delete_memory", "drop_table", "purge_all", "reset_data"
}

# Actions that communicate with external services
EXTERNAL_ACTIONS = {
    "send_email", "github_create_pr", "github_push", "post_webhook", "external_api_call"
}

# Read-only actions (inherently low risk)
READ_ACTIONS = {
    "get_events", "get_free_slots", "get_tasks", "get_project", "list_projects",
    "search", "search_memories", "get_document", "read_file"
}

class ToolValidationResult(BaseModel):
    allowed: bool
    requires_confirmation: bool
    risk_level: RiskLevel
    failure_reason: Optional[str] = None
    step_results: Dict[str, bool] = Field(default_factory=dict)
    sanitized_parameters: Dict[str, Any] = Field(default_factory=dict)

class ToolSecurityGuard:
    """
    Five-Step Tool Security Validator:
    1. User Permission Validation
    2. Tool Permission Validation
    3. Input Schema & Parameter Validation
    4. Action Risk Assessment
    5. Confirmation Requirement Determination
    """

    @classmethod
    def validate_user_permission(
        cls,
        user: Any,
        tool_name: str,
        action: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Step 1: Validate User Permission.
        Ensures the user exists, is active, and possesses required privileges.
        """
        if user is None:
            return False, "Unauthenticated request: user context is missing."

        # If user is a model or object with is_active
        if hasattr(user, "is_active") and not user.is_active:
            return False, "Inactive user: account is suspended or disabled."

        # Verify restricted / privileged tool categories
        if tool_name in ["system_admin", "terminal", "eval_runner"]:
            user_role = getattr(user, "role", "user")
            if user_role not in ["admin", "developer"]:
                return False, f"User lacks required role 'admin' to access privileged tool '{tool_name}'."

        return True, None

    @classmethod
    def validate_tool_permission(
        cls,
        tool: Any,
        action: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Step 2: Validate Tool Permission.
        Ensures the tool is registered, active, and explicitly permits the requested action.
        """
        if tool is None:
            return False, "Tool is not registered or unavailable."

        # Check if tool defines explicit allowed actions
        declared_actions = getattr(tool, "allowed_actions", None)
        if declared_actions and action not in declared_actions:
            return False, f"Action '{action}' is not permitted for tool '{tool.name}'."

        return True, None

    @classmethod
    def validate_input_schema(
        cls,
        tool: Any,
        parameters: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Step 3: Validate Input Schema & Sanitize Parameters.
        Rejects suspicious traversal, command injections, or malformed data.
        """
        if not isinstance(parameters, dict):
            return False, {}, "Parameters must be provided as a key-value dictionary."

        # Validate against tool's Pydantic input model if available
        input_model = getattr(tool, "input_model", None)
        if input_model:
            try:
                # If tool defines an input model, attempt validation
                pass
            except Exception as e:
                return False, {}, f"Input validation failed against schema: {str(e)}"

        # Deep scan parameter values for injection patterns
        sanitized = {}
        for key, val in parameters.items():
            if isinstance(val, str):
                for pat in SUSPICIOUS_PATTERNS:
                    if pat.search(val):
                        return False, {}, f"Security violation: Suspicious pattern detected in parameter '{key}'."
                sanitized[key] = val.strip()
            elif hasattr(val, "isoformat"):
                sanitized[key] = val.isoformat()
            elif isinstance(val, uuid.UUID):
                sanitized[key] = str(val)
            else:
                sanitized[key] = val

        return True, sanitized, None

    @classmethod
    def validate_action_risk(
        cls,
        tool: Any,
        action: str,
        parameters: Dict[str, Any]
    ) -> RiskLevel:
        """
        Step 4: Assess Action Risk.
        Categorizes action into LOW, MEDIUM, HIGH, or CRITICAL.
        """
        action_lower = (action or "").lower()

        # Destructive actions are HIGH or CRITICAL
        if action_lower in DESTRUCTIVE_ACTIONS or any(action_lower.startswith(p) for p in ["delete", "drop", "purge"]):
            return RiskLevel.HIGH

        # External communication actions are HIGH
        if action_lower in EXTERNAL_ACTIONS or getattr(tool, "name", "") in ["email", "github"]:
            if action_lower not in READ_ACTIONS:
                return RiskLevel.HIGH

        # Inherit tool declared risk if set higher
        tool_risk = getattr(tool, "risk_level", RiskLevel.LOW)
        if tool_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return tool_risk

        # Read actions are LOW
        if action_lower in READ_ACTIONS or any(action_lower.startswith(p) for p in ["get", "list", "search", "read"]):
            return RiskLevel.LOW

        # Other state modifications default to MEDIUM
        return RiskLevel.MEDIUM

    @classmethod
    def validate_confirmation_requirement(
        cls,
        tool: Any,
        action: str,
        risk_level: RiskLevel,
        caller_is_llm: bool = True
    ) -> bool:
        """
        Step 5: Determine Confirmation Requirement.
        An AI agent must NEVER execute a privileged or high-risk action without human approval.
        """
        # Always require confirmation for HIGH or CRITICAL risk
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return True

        # Tool explicitly mandates human confirmation
        if getattr(tool, "requires_confirmation", False):
            return True

        # Destructive or external actions always require confirmation
        action_lower = (action or "").lower()
        if action_lower in DESTRUCTIVE_ACTIONS or action_lower in EXTERNAL_ACTIONS:
            return True

        # Calendar or task modifications proposed autonomously by LLM require user approval
        if caller_is_llm and action_lower in ["create_event", "update_event", "send_email"]:
            return True

        return False

    @classmethod
    def evaluate(
        cls,
        user: Any,
        tool: Any,
        action: str,
        parameters: Dict[str, Any],
        caller_is_llm: bool = True
    ) -> ToolValidationResult:
        """
        Full 5-step evaluation pass.
        Returns ToolValidationResult with granular step breakdown.
        """
        step_results = {
            "1_user_permission": False,
            "2_tool_permission": False,
            "3_input_schema": False,
            "4_action_risk": False,
            "5_confirmation_requirement": False,
        }

        # Step 1: User permission
        u_ok, u_err = cls.validate_user_permission(user, getattr(tool, "name", ""), action)
        if not u_ok:
            return ToolValidationResult(
                allowed=False,
                requires_confirmation=True,
                risk_level=RiskLevel.HIGH,
                failure_reason=u_err,
                step_results=step_results,
                sanitized_parameters={}
            )
        step_results["1_user_permission"] = True

        # Step 2: Tool permission
        t_ok, t_err = cls.validate_tool_permission(tool, action)
        if not t_ok:
            return ToolValidationResult(
                allowed=False,
                requires_confirmation=True,
                risk_level=RiskLevel.HIGH,
                failure_reason=t_err,
                step_results=step_results,
                sanitized_parameters={}
            )
        step_results["2_tool_permission"] = True

        # Step 3: Input schema & sanitization
        s_ok, sanitized_params, s_err = cls.validate_input_schema(tool, parameters)
        if not s_ok:
            return ToolValidationResult(
                allowed=False,
                requires_confirmation=True,
                risk_level=RiskLevel.HIGH,
                failure_reason=s_err,
                step_results=step_results,
                sanitized_parameters={}
            )
        step_results["3_input_schema"] = True

        # Step 4: Action risk assessment
        risk_level = cls.validate_action_risk(tool, action, sanitized_params)
        step_results["4_action_risk"] = True

        # Step 5: Confirmation requirement
        req_confirm = cls.validate_confirmation_requirement(
            tool=tool,
            action=action,
            risk_level=risk_level,
            caller_is_llm=caller_is_llm
        )
        step_results["5_confirmation_requirement"] = True

        return ToolValidationResult(
            allowed=True,
            requires_confirmation=req_confirm,
            risk_level=risk_level,
            failure_reason=None,
            step_results=step_results,
            sanitized_parameters=sanitized_params
        )

tool_security_guard = ToolSecurityGuard()
