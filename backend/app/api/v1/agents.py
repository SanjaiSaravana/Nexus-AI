import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.agent import (
    OrchestrationRequest,
    OrchestrationResult,
    AgentType
)
from app.services.agents.orchestrator import orchestrator

router = APIRouter()

@router.post("/orchestrate", response_model=OrchestrationResult)
async def execute_multi_agent_orchestration(
    request: OrchestrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Executes full multi-agent orchestration pipeline across Planner, Research, Memory, Project, Task, and Calendar agents."""
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    result = await orchestrator.orchestrate(
        request=request,
        user_id=current_user.id,
        db=db
    )
    return result

@router.get("/runs/{run_id}", response_model=OrchestrationResult)
async def get_agent_run_audit(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    """Inspects detailed agent state audit, execution timings, and subtask results for an orchestration run."""
    run_data = orchestrator.get_run(run_id)
    if not run_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orchestration run '{run_id}' not found."
        )
    return run_data

@router.get("/definitions")
async def list_agent_definitions(
    current_user: User = Depends(get_current_user)
):
    """Lists registered agents in the Nexus Multi-Agent Architecture."""
    agents_list = []
    for agent_type, agent in orchestrator.agents.items():
        agents_list.append({
            "type": agent_type.value,
            "name": agent.name,
            "description": agent.description,
            "activity_message": agent.activity_message,
            "max_retries": agent.max_retries
        })
    return {"agents": agents_list, "count": len(agents_list)}
