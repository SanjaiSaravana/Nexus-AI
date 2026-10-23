import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class RecommendationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category: str
    title: str
    recommendation: str
    reason: str
    priority_score: float = Field(..., ge=0.0, le=1.0)
    priority_level: str  # urgent, high, medium, low
    related_goal: Optional[str] = None
    related_deadline: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: datetime
    dismissed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ProactivePreferencesResponse(BaseModel):
    enabled: bool = True
    frequency: str = "daily"  # immediate, hourly, daily
    max_daily_recommendations: int = 5
    muted_categories: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class ProactivePreferencesUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[str] = None
    max_daily_recommendations: Optional[int] = Field(None, ge=1, le=20)
    muted_categories: Optional[List[str]] = None

class RecommendationActionRequest(BaseModel):
    action_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
