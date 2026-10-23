import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    RiskLevel,
    CalendarEventCreate,
    CalendarEventResponse,
    FreeSlotItem
)
from app.models.calendar import CalendarEvent
from app.services.tools.base import BaseTool

def utcnow():
    return datetime.now(timezone.utc)

def to_utc(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class CalendarTool(BaseTool):
    """Calendar Tool providing event management and free slot discovery with local database persistence."""

    def __init__(self, db_session: Optional[AsyncSession] = None, user_id: Optional[Any] = None, **kwargs):
        super().__init__(
            name="calendar",
            description="Manage user calendar events, detect free slots, and schedule preparation sessions.",
            category="productivity",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            permissions=["calendar:read", "calendar:write"],
            input_model=CalendarEventCreate,
            output_model=CalendarEventResponse,
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
        if action == "get_events":
            return await self.get_events(user_id=user_id, params=params, db=db)
        elif action == "get_free_slots":
            return await self.get_free_slots(user_id=user_id, params=params, db=db)
        elif action == "create_event":
            return await self.create_event(user_id=user_id, params=params, db=db)
        elif action == "update_event":
            return await self.update_event(user_id=user_id, params=params, db=db)
        elif action == "delete_event":
            return await self.delete_event(user_id=user_id, params=params, db=db)
        else:
            raise ValueError(f"Unknown calendar action '{action}'. Supported: get_events, get_free_slots, create_event, update_event, delete_event")

    async def get_events(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Retrieves user calendar events, optionally filtered by date range."""
        stmt = select(CalendarEvent).where(CalendarEvent.user_id == user_id)
        start_filter = params.get("start_time")
        end_filter = params.get("end_time")
        if start_filter:
            start_filter = to_utc(start_filter)
            stmt = stmt.where(CalendarEvent.end_time >= start_filter)
        if end_filter:
            end_filter = to_utc(end_filter)
            stmt = stmt.where(CalendarEvent.start_time <= end_filter)

        stmt = stmt.order_by(CalendarEvent.start_time.asc())
        res = await db.execute(stmt)
        events = res.scalars().all()
        return {
            "events": [
                {
                    "id": str(e.id),
                    "user_id": str(e.user_id),
                    "title": e.title,
                    "description": e.description,
                    "start_time": to_utc(e.start_time).isoformat(),
                    "end_time": to_utc(e.end_time).isoformat(),
                    "location": e.location,
                    "event_type": e.event_type,
                    "is_all_day": e.is_all_day,
                    "created_at": to_utc(e.created_at).isoformat(),
                    "updated_at": to_utc(e.updated_at).isoformat()
                }
                for e in events
            ],
            "count": len(events)
        }

    async def get_free_slots(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Calculates free blocks of time between busy intervals."""
        st_param = params.get("start_time")
        et_param = params.get("end_time")
        target_date_str = params.get("date")

        if st_param and et_param:
            day_start = to_utc(st_param)
            day_end = to_utc(et_param)
        elif target_date_str:
            target_date = to_utc(target_date_str)
            day_start = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            day_end = target_date.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            target_date = utcnow() + timedelta(days=1)
            day_start = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            day_end = target_date.replace(hour=18, minute=0, second=0, microsecond=0)

        min_duration = int(params.get("duration_minutes", 30))

        # Get existing events for that window
        stmt = (
            select(CalendarEvent)
            .where(
                and_(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.start_time < day_end,
                    CalendarEvent.end_time > day_start
                )
            )
            .order_by(CalendarEvent.start_time.asc())
        )
        res = await db.execute(stmt)
        events = res.scalars().all()

        free_slots: List[Dict[str, Any]] = []
        current_cursor = day_start

        for e in events:
            e_start = to_utc(e.start_time)
            e_end = to_utc(e.end_time)
            if e_start > current_cursor:
                duration_mins = int((e_start - current_cursor).total_seconds() / 60)
                if duration_mins >= min_duration:
                    free_slots.append({
                        "start_time": current_cursor.isoformat(),
                        "end_time": e_start.isoformat(),
                        "duration_minutes": duration_mins
                    })
            if e_end > current_cursor:
                current_cursor = e_end

        if current_cursor < day_end:
            duration_mins = int((day_end - current_cursor).total_seconds() / 60)
            if duration_mins >= min_duration:
                free_slots.append({
                    "start_time": current_cursor.isoformat(),
                    "end_time": day_end.isoformat(),
                    "duration_minutes": duration_mins
                })

        return {"free_slots": free_slots, "count": len(free_slots)}

    async def create_event(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Creates and persists a calendar event."""
        start_time = params["start_time"]
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        end_time = params["end_time"]
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)

        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")

        event = CalendarEvent(
            user_id=user_id,
            title=params["title"],
            description=params.get("description"),
            start_time=start_time,
            end_time=end_time,
            location=params.get("location"),
            event_type=params.get("event_type", "interview"),
            is_all_day=params.get("is_all_day", False)
        )
        db.add(event)
        await db.flush()

        event_dict = {
            "id": str(event.id),
            "user_id": str(event.user_id),
            "title": event.title,
            "description": event.description,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "location": event.location,
            "event_type": event.event_type,
            "is_all_day": event.is_all_day,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.updated_at.isoformat(),
            "status": "created"
        }

        return {
            "event": event_dict,
            "id": str(event.id),
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "event_type": event.event_type,
            "status": "created"
        }

    async def update_event(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Updates an existing calendar event."""
        event_id = params.get("event_id") or params.get("id")
        if not event_id:
            raise ValueError("Parameter 'event_id' is required for update_event")
        if isinstance(event_id, str):
            event_id = uuid.UUID(event_id)

        stmt = select(CalendarEvent).where(CalendarEvent.id == event_id, CalendarEvent.user_id == user_id)
        res = await db.execute(stmt)
        event = res.scalar_one_or_none()
        if not event:
            raise ValueError(f"Calendar event '{event_id}' not found.")

        if "title" in params:
            event.title = params["title"]
        if "description" in params:
            event.description = params["description"]
        if "start_time" in params:
            st = params["start_time"]
            event.start_time = datetime.fromisoformat(st) if isinstance(st, str) else st
        if "end_time" in params:
            et = params["end_time"]
            event.end_time = datetime.fromisoformat(et) if isinstance(et, str) else et
        if "location" in params:
            event.location = params["location"]
        if "event_type" in params:
            event.event_type = params["event_type"]

        await db.flush()

        event_dict = {
            "id": str(event.id),
            "user_id": str(event.user_id),
            "title": event.title,
            "description": event.description,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "location": event.location,
            "event_type": event.event_type,
            "is_all_day": event.is_all_day,
            "created_at": event.created_at.isoformat(),
            "updated_at": event.updated_at.isoformat(),
            "status": "updated"
        }

        return {
            "event": event_dict,
            "id": str(event.id),
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "location": event.location,
            "status": "updated"
        }

    async def delete_event(
        self,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Deletes a calendar event."""
        event_id = params.get("event_id") or params.get("id")
        if not event_id:
            raise ValueError("Parameter 'event_id' is required for delete_event")
        if isinstance(event_id, str):
            event_id = uuid.UUID(event_id)

        stmt = select(CalendarEvent).where(CalendarEvent.id == event_id, CalendarEvent.user_id == user_id)
        res = await db.execute(stmt)
        event = res.scalar_one_or_none()
        if not event:
            raise ValueError(f"Calendar event '{event_id}' not found.")

        await db.delete(event)
        await db.flush()
        return {"id": str(event_id), "status": "deleted", "deleted": True}

calendar_tool = CalendarTool()
