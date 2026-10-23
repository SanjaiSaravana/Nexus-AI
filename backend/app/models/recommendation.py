import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base, GUID

def utcnow():
    return datetime.now(timezone.utc)

class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    recommendation = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    priority_score = Column(Float, default=0.5, nullable=False, index=True)
    priority_level = Column(String(20), default="medium", nullable=False)  # urgent, high, medium, low
    related_goal = Column(String(255), nullable=True)
    related_deadline = Column(String(100), nullable=True)
    action_type = Column(String(100), nullable=True)
    action_payload = Column(JSON, default=dict, nullable=False)
    status = Column(String(30), default="active", nullable=False, index=True)  # active, dismissed, executed
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="recommendations")

class ProactivePreferences(Base):
    __tablename__ = "proactive_preferences"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    frequency = Column(String(30), default="daily", nullable=False)  # immediate, hourly, daily
    max_daily_recommendations = Column(Integer, default=5, nullable=False)
    muted_categories = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="proactive_preferences")
