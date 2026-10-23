import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.agent import (
    OrchestrationRequest,
    OrchestrationResult
)
from app.schemas.tool import ActionProposalResponse
from app.services.workflows.interview_prep import interview_prep_workflow

router = APIRouter()

@router.post("/interview-prep", response_model=OrchestrationResult)
async def run_flagship_interview_prep(
    request: OrchestrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes the flagship 16-step NEXUS interview preparation workflow end-to-end:
    Intent detection, calendar lookup, JD parsing, skill comparison, gap analysis,
    task persistence, calendar action proposal (HITL confirmation), memory storage,
    and final summary synthesis.
    """
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    result = await interview_prep_workflow.execute(
        request=request,
        user_id=current_user.id,
        db=db
    )
    return result

@router.post("/interview-prep/approve-calendar/{proposal_id}", response_model=ActionProposalResponse)
async def approve_interview_prep_calendar(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Step 14: Confirms user approval for the staged calendar action proposal,
    executing event creation in the user calendar and recording in the audit log.
    """
    try:
        proposal, execution_result = await interview_prep_workflow.create_approved_event(
            proposal_id=proposal_id,
            user_id=current_user.id,
            db=db
        )
        return proposal
    except LookupError as not_found_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(not_found_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
