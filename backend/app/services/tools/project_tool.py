import uuid
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import RiskLevel
from app.models.project import Project
from app.services.tools.base import BaseTool

class ProjectTool(BaseTool):
    """Project Tool providing project listing, analysis, and creation."""

    def __init__(self):
        super().__init__(
            name="projects",
            description="Manage user repositories and projects: list, inspect tasks, and create projects.",
            category="productivity",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            permissions=["projects:read", "projects:write"]
        )

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        if action == "list_projects":
            stmt = select(Project).options(selectinload(Project.tasks)).where(Project.user_id == user_id)
            res = await db.execute(stmt)
            projs = res.scalars().all()
            return {
                "projects": [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "description": p.description,
                        "status": p.status,
                        "task_count": len(p.tasks)
                    }
                    for p in projs
                ],
                "count": len(projs)
            }
        elif action == "create_project":
            proj = Project(
                user_id=user_id,
                name=params["name"],
                description=params.get("description"),
                status=params.get("status", "active")
            )
            db.add(proj)
            await db.flush()
            return {
                "id": str(proj.id),
                "name": proj.name,
                "status": proj.status,
                "action": "created"
            }
        else:
            raise ValueError(f"Unknown project action '{action}'. Supported: list_projects, create_project")

project_tool = ProjectTool()
