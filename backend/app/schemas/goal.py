import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "personal"
    status: str = "active"
    progress_pct: int = Field(default=0, ge=0, le=100)
    target_date: Optional[date] = None

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    progress_pct: Optional[int] = Field(default=None, ge=0, le=100)
    target_date: Optional[date] = None

class GoalResponse(GoalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
