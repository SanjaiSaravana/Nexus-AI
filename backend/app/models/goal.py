import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Date
from sqlalchemy.orm import relationship
from app.core.database import Base, GUID

def utcnow():
    return datetime.now(timezone.utc)

class Goal(Base):
    __tablename__ = "goals"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="personal", nullable=False, index=True)  # career, learning, personal, fitness, financial
    status = Column(String(50), default="active", nullable=False, index=True)  # active, completed, on_hold, cancelled
    progress_pct = Column(Integer, default=0, nullable=False)
    target_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="goals")
