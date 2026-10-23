import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationResponse,
    ProactivePreferencesResponse,
    ProactivePreferencesUpdate,
    RecommendationActionRequest
)
from app.services.proactive.service import proactive_service

router = APIRouter()

@router.get("", response_model=List[RecommendationResponse])
async def list_active_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns active AI recommendations for the authenticated user.
    If no active recommendations are cached, automatically evaluates proactive intelligence.
    """
    active = await proactive_service.get_active_recommendations(user_id=current_user.id, db=db)
    if not active:
        active = await proactive_service.generate_recommendations(user_id=current_user.id, db=db)
    return active

@router.post("/generate", response_model=List[RecommendationResponse])
async def trigger_proactive_detection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Explicitly evaluates proactive intelligence across calendar, documents, tasks,
    deadlines, goals, and conflicts to generate fresh AI recommendations.
    """
    return await proactive_service.generate_recommendations(user_id=current_user.id, db=db)

@router.post("/{recommendation_id}/dismiss", response_model=RecommendationResponse)
async def dismiss_ai_recommendation(
    recommendation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Dismisses a recommendation so it will not appear in the dashboard or notifications.
    """
    try:
        return await proactive_service.dismiss_recommendation(
            recommendation_id=recommendation_id,
            user_id=current_user.id,
            db=db
        )
    except LookupError as not_found_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(not_found_err))

@router.post("/{recommendation_id}/act")
async def execute_recommendation_action(
    recommendation_id: uuid.UUID,
    payload: Optional[RecommendationActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes the proactive action suggested by NEXUS (e.g., generating an interview preparation plan).
    The system asks before taking action; user approval triggers execution.
    """
    try:
        return await proactive_service.execute_recommendation_action(
            recommendation_id=recommendation_id,
            user_id=current_user.id,
            db=db
        )
    except LookupError as not_found_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(not_found_err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/preferences", response_model=ProactivePreferencesResponse)
async def get_proactive_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves proactive intelligence and notification anti-spam preferences.
    """
    return await proactive_service.get_preferences(user_id=current_user.id, db=db)

@router.put("/preferences", response_model=ProactivePreferencesResponse)
async def update_proactive_preferences(
    request: ProactivePreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates proactive intelligence preferences (enable/disable, frequency, daily limits, muted categories).
    """
    updates = request.model_dump(exclude_unset=True)
    return await proactive_service.update_preferences(
        user_id=current_user.id,
        updates=updates,
        db=db
    )
