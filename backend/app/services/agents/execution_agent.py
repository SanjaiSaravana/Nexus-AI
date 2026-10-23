import uuid
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    ExecutedActionItem,
    ExecutionAgentOutput
)
from app.models.task import Task
from app.services.agents.base import BaseAgent

class ExecutionAgent(BaseAgent):
    """Execution Agent Interface responsible for dispatching concrete actions (task persistence, scheduling, notifications)."""
    def __init__(self):
        super().__init__(
            agent_type=AgentType.EXECUTION,
            name="Execution Agent",
            description="Interface for executing concrete actions such as persisting generated tasks to the database.",
            activity_message="Executing actions..."
        )

    async def _process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        auto_execute = input_data.get("auto_execute_tasks", False) or context.get("auto_execute_tasks", False)
        task_data = context.get("task", {})
        tasks_to_create = task_data.get("tasks", [])

        actions: List[ExecutedActionItem] = []

        if auto_execute and tasks_to_create:
            today = date.today()
            created_count = 0
            for item in tasks_to_create:
                offset = item.get("due_date_offset_days", 1)
                due = today + timedelta(days=offset) if offset is not None else None
                
                db_task = Task(
                    user_id=user_id,
                    title=item.get("title", "New Task"),
                    description=item.get("description", ""),
                    priority=item.get("priority", "medium"),
                    status="todo",
                    due_date=due
                )
                db.add(db_task)
                created_count += 1
                actions.append(
                    ExecutedActionItem(
                        action_type="create_task",
                        target=item.get("title", "Task"),
                        status="success",
                        details={"priority": item.get("priority"), "due_date": str(due)}
                    )
                )

            await db.flush()
            summary = f"Execution Agent persisted {created_count} actionable task(s) into database."
        else:
            # Action prepared but execution deferred for user review
            for item in tasks_to_create:
                actions.append(
                    ExecutedActionItem(
                        action_type="staged_task",
                        target=item.get("title", "Task"),
                        status="staged_for_approval",
                        details={"priority": item.get("priority")}
                    )
                )
            summary = f"Execution Agent staged {len(actions)} task(s) for user confirmation."

        output = ExecutionAgentOutput(
            actions=actions,
            success=True,
            summary=summary
        )
        return output.model_dump()

    async def _fallback(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID,
        error: Exception
    ) -> Optional[Dict[str, Any]]:
        output = ExecutionAgentOutput(
            actions=[],
            success=False,
            summary=f"Execution skipped due to fallback: {str(error)}"
        )
        return output.model_dump()

execution_agent = ExecutionAgent()
