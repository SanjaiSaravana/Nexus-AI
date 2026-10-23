import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[date] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None

class TaskResponse(TaskBase):
    id: uuid.UUID
    user_id: uuid.UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
