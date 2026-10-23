import uuid
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    RiskLevel,
    TaskToolCreate,
    TaskToolUpdate
)
from app.models.task import Task
from app.services.tools.base import BaseTool

def utcnow():
    return datetime.now(timezone.utc)

class TaskTool(BaseTool):
    """Task Management Tool providing task creation, updating, completion, and deletion."""

    def __init__(self, db_session: Optional[AsyncSession] = None, user_id: Optional[Any] = None, **kwargs):
        super().__init__(
            name="task",
            description="Manage user tasks: create, update, complete, and delete tasks.",
            category="productivity",
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False,  # Reads/creation can be auto-approved; deletions check action
            permissions=["task:read", "task:write"],
            input_model=TaskToolCreate,
            db_session=db_session,
            user_id=user_id,
            **kwargs
        )

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        if action == "create_task":
            return await self.create_task(user_id=user_id, params=params, db=db)
        elif action == "update_task":
            return await self.update_task(user_id=user_id, params=params, db=db)
        elif action == "complete_task":
            return await self.complete_task(user_id=user_id, params=params, db=db)
        elif action == "delete_task":
            return await self.delete_task(user_id=user_id, params=params, db=db)
        elif action == "list_tasks":
            return await self.list_tasks(user_id=user_id, params=params, db=db)
        else:
            raise ValueError(f"Unknown task action '{action}'. Supported: create_task, update_task, complete_task, delete_task, list_tasks")

    async def create_task(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        due_date_val = params.get("due_date")
        if due_date_val:
            if isinstance(due_date_val, str):
                due_date_val = date.fromisoformat(due_date_val)
            elif isinstance(due_date_val, datetime):
                due_date_val = due_date_val.date()

        proj_id = params.get("project_id")
        if proj_id and isinstance(proj_id, str):
            proj_id = uuid.UUID(proj_id)

        task = Task(
            user_id=user_id,
            project_id=proj_id,
            title=params["title"],
            description=params.get("description"),
            priority=params.get("priority", "medium"),
            status="todo",
            due_date=due_date_val
        )
        db.add(task)
        await db.flush()

        task_dict = {
            "id": str(task.id),
            "user_id": str(task.user_id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": str(task.due_date) if task.due_date else None,
            "action": "created"
        }

        return {
            "task": task_dict,
            "id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "due_date": str(task.due_date) if task.due_date else None,
            "action": "created"
        }

    async def update_task(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        task_id = params.get("task_id") or params.get("id")
        if not task_id:
            raise ValueError("Parameter 'task_id' is required for update_task")
        if isinstance(task_id, str):
            task_id = uuid.UUID(task_id)

        stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        if "title" in params:
            task.title = params["title"]
        if "description" in params:
            task.description = params["description"]
        if "status" in params:
            task.status = params["status"]
            if task.status == "completed" and not task.completed_at:
                task.completed_at = utcnow()
        if "priority" in params:
            task.priority = params["priority"]
        if "due_date" in params:
            d = params["due_date"]
            task.due_date = date.fromisoformat(d) if isinstance(d, str) else d

        await db.flush()

        task_dict = {
            "id": str(task.id),
            "user_id": str(task.user_id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": str(task.due_date) if task.due_date else None,
            "action": "updated"
        }

        return {
            "task": task_dict,
            "id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "action": "updated"
        }

    async def complete_task(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        task_id = params.get("task_id") or params.get("id")
        if not task_id:
            raise ValueError("Parameter 'task_id' is required for complete_task")
        if isinstance(task_id, str):
            task_id = uuid.UUID(task_id)

        stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        task.status = "completed"
        task.completed_at = utcnow()
        await db.flush()

        task_dict = {
            "id": str(task.id),
            "user_id": str(task.user_id),
            "title": task.title,
            "status": "completed",
            "priority": task.priority,
            "completed_at": task.completed_at.isoformat(),
            "action": "completed"
        }

        return {
            "task": task_dict,
            "id": str(task.id),
            "title": task.title,
            "status": "completed",
            "completed_at": task.completed_at.isoformat(),
            "action": "completed"
        }

    async def delete_task(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        task_id = params.get("task_id") or params.get("id")
        if not task_id:
            raise ValueError("Parameter 'task_id' is required for delete_task")
        if isinstance(task_id, str):
            task_id = uuid.UUID(task_id)

        stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        await db.delete(task)
        await db.flush()
        return {"id": str(task_id), "status": "deleted", "deleted": True}

    async def list_tasks(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        stmt = select(Task).where(Task.user_id == user_id)
        if "status" in params:
            stmt = stmt.where(Task.status == params["status"])
        if "priority" in params:
            stmt = stmt.where(Task.priority == params["priority"])

        stmt = stmt.order_by(Task.created_at.desc())
        res = await db.execute(stmt)
        tasks = res.scalars().all()
        return {
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": str(t.due_date) if t.due_date else None
                }
                for t in tasks
            ],
            "count": len(tasks)
        }

task_tool = TaskTool()
