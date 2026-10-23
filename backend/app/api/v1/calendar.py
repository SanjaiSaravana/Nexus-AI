import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.tool import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse
)
from app.services.tools.calendar_tool import calendar_tool

router = APIRouter()

@router.get("/events", response_model=List[CalendarEventResponse])
async def list_calendar_events(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves calendar events for the authenticated user."""
    res = await calendar_tool.get_events(
        user_id=current_user.id,
        params={"start_time": start_time, "end_time": end_time},
        db=db
    )
    return [CalendarEventResponse(**e) for e in res["events"]]

@router.get("/free-slots")
async def get_free_calendar_slots(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Detects open calendar slots between busy intervals."""
    return await calendar_tool.get_free_slots(
        user_id=current_user.id,
        params={"date": date},
        db=db
    )

@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    event_in: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a calendar event."""
    res = await calendar_tool.create_event(
        user_id=current_user.id,
        params=event_in.model_dump(),
        db=db
    )
    return CalendarEventResponse(
        id=uuid.UUID(res["id"]),
        user_id=current_user.id,
        title=res["title"],
        description=event_in.description,
        start_time=event_in.start_time,
        end_time=event_in.end_time,
        location=event_in.location,
        event_type=res["event_type"],
        is_all_day=event_in.is_all_day,
        created_at=event_in.start_time,
        updated_at=event_in.start_time
    )

@router.patch("/events/{event_id}", response_model=Dict[str, Any])
async def update_calendar_event(
    event_id: uuid.UUID,
    event_in: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates a calendar event."""
    params = event_in.model_dump(exclude_unset=True)
    params["event_id"] = event_id
    try:
        return await calendar_tool.update_event(
            user_id=current_user.id,
            params=params,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes a calendar event."""
    try:
        await calendar_tool.delete_event(
            user_id=current_user.id,
            params={"event_id": event_id},
            db=db
        )
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
