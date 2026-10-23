import abc
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import AgentType, AgentStatus, AgentState

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

class BaseAgent(abc.ABC):
    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        description: str,
        activity_message: str,
        max_retries: int = 2
    ):
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.activity_message = activity_message
        self.max_retries = max_retries

    @abc.abstractmethod
    async def _process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Core agent logic returning structured dictionary conforming to agent schema."""
        pass

    async def _fallback(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID,
        error: Exception
    ) -> Optional[Dict[str, Any]]:
        """Graceful fallback when execution fails after retries. Default returns safe empty structure."""
        logger.warning(f"Agent {self.name} utilizing default fallback after failure: {error}")
        return None

    async def run(
        self,
        run_id: uuid.UUID,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> AgentState:
        """Executes the agent with state tracking, error handling, retries, and fallback."""
        state = AgentState(
            run_id=run_id,
            agent=self.agent_type,
            input=input_data,
            status=AgentStatus.RUNNING,
            start_time=utcnow(),
            retries=0
        )

        attempts = 0
        last_exception: Optional[Exception] = None

        while attempts <= self.max_retries:
            try:
                result_output = await self._process(
                    input_data=input_data,
                    context=context,
                    db=db,
                    user_id=user_id
                )
                state.output = result_output
                state.status = AgentStatus.COMPLETED
                state.end_time = utcnow()
                return state
            except Exception as e:
                last_exception = e
                attempts += 1
                state.retries = attempts
                logger.warning(
                    f"Agent {self.name} failed attempt {attempts}/{self.max_retries + 1}: {e}"
                )
                if attempts <= self.max_retries:
                    state.status = AgentStatus.RETRIED
                    await asyncio.sleep(0.05 * attempts)

        # Retries exhausted - execute fallback
        state.errors = f"{type(last_exception).__name__}: {str(last_exception)}"
        try:
            fallback_output = await self._fallback(
                input_data=input_data,
                context=context,
                db=db,
                user_id=user_id,
                error=last_exception
            )
            if fallback_output is not None:
                state.output = fallback_output
                state.status = AgentStatus.COMPLETED
            else:
                state.status = AgentStatus.FAILED
        except Exception as fb_err:
            state.errors = f"Primary error: {state.errors}; Fallback error: {str(fb_err)}"
            state.status = AgentStatus.FAILED

        state.end_time = utcnow()
        return state
