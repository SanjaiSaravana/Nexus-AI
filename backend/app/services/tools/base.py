import abc
import time
import logging
import uuid
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    RiskLevel,
    ToolDefinitionResponse,
    ToolExecutionResult
)

logger = logging.getLogger(__name__)

class BaseTool(abc.ABC):
    """Abstract base class for all NEXUS secure tools."""

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        risk_level: RiskLevel = RiskLevel.LOW,
        requires_confirmation: bool = False,
        permissions: Optional[List[str]] = None,
        input_model: Optional[Type[BaseModel]] = None,
        output_model: Optional[Type[BaseModel]] = None,
        db_session: Optional[AsyncSession] = None,
        user_id: Optional[Any] = None,
        **kwargs
    ):
        self.name = name
        self.description = description
        self.category = category
        self.risk_level = risk_level
        self.requires_confirmation = requires_confirmation
        self.permissions = permissions or []
        self.input_model = input_model
        self.output_model = output_model
        self.db_session = db_session
        self.user_id = user_id

    def get_definition(self) -> ToolDefinitionResponse:
        input_schema = self.input_model.model_json_schema() if self.input_model else {"type": "object"}
        output_schema = self.output_model.model_json_schema() if self.output_model else {"type": "object"}
        return ToolDefinitionResponse(
            name=self.name,
            description=self.description,
            category=self.category,
            risk_level=self.risk_level,
            requires_confirmation=self.requires_confirmation,
            permissions=self.permissions,
            input_schema=input_schema,
            output_schema=output_schema
        )

    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validates parameters and ensures JSON-safe primitives (dates to ISO strings, UUIDs to str)."""
        if not isinstance(params, dict):
            return {}
        cleaned = {}
        for k, v in params.items():
            if hasattr(v, "isoformat"):
                cleaned[k] = v.isoformat()
            elif isinstance(v, uuid.UUID):
                cleaned[k] = str(v)
            elif isinstance(v, dict):
                cleaned[k] = {
                    dk: dv.isoformat() if hasattr(dv, "isoformat") else str(dv) if isinstance(dv, uuid.UUID) else dv
                    for dk, dv in v.items()
                }
            elif isinstance(v, list):
                cleaned[k] = [
                    item.isoformat() if hasattr(item, "isoformat") else str(item) if isinstance(item, uuid.UUID) else item
                    for item in v
                ]
            else:
                cleaned[k] = v
        return cleaned

    @abc.abstractmethod
    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Internal execution method implemented by concrete tools."""
        pass

    async def execute(
        self,
        *args,
        **kwargs
    ) -> ToolExecutionResult:
        """
        Executes the tool action with validation, timing, and robust error handling.
        Supports:
          execute(action, user_id, params, db)
          execute({"action": "create_event", ...})
          execute(action=..., user_id=..., params=..., db=...)
        """
        start_time = time.time()
        action = None
        user_id = None
        params = {}
        db = None

        if len(args) == 1 and isinstance(args[0], dict):
            payload = dict(args[0])
            action = payload.pop("action", "")
            params = payload
            user_id = kwargs.get("user_id") or self.user_id
            db = kwargs.get("db") or kwargs.get("db_session") or self.db_session
        elif len(args) >= 1:
            action = args[0]
            user_id = args[1] if len(args) > 1 else kwargs.get("user_id") or self.user_id
            params = args[2] if len(args) > 2 else kwargs.get("params", {})
            db = args[3] if len(args) > 3 else kwargs.get("db") or kwargs.get("db_session") or self.db_session
        else:
            action = kwargs.get("action", "")
            user_id = kwargs.get("user_id") or self.user_id
            params = kwargs.get("params", {})
            db = kwargs.get("db") or kwargs.get("db_session") or self.db_session

        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except (ValueError, AttributeError):
                user_id = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

        try:
            from app.services.tools.security_guard import tool_security_guard
            s_ok, cleaned_params, s_err = tool_security_guard.validate_input_schema(self, params)
            if not s_ok:
                return ToolExecutionResult(
                    tool=self.name,
                    action=action or "",
                    success=False,
                    error=s_err or "Invalid parameters",
                    execution_time_ms=round((time.time() - start_time) * 1000.0, 2)
                )

            validated_params = self.validate_parameters(cleaned_params)
            result_data = await self._execute_action(
                action=action,
                user_id=user_id,
                params=validated_params,
                db=db
            )
            elapsed_ms = (time.time() - start_time) * 1000.0
            return ToolExecutionResult(
                tool=self.name,
                action=action or "",
                success=True,
                data=result_data,
                execution_time_ms=round(elapsed_ms, 2)
            )
        except Exception as err:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Error executing tool {self.name}.{action}: {err}", exc_info=True)
            return ToolExecutionResult(
                tool=self.name,
                action=action or "",
                success=False,
                error=str(err),
                execution_time_ms=round(elapsed_ms, 2)
            )
