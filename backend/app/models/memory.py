import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base, GUID, VectorType
from app.core.config import settings

def utcnow():
    return datetime.now(timezone.utc)

class MemoryType(str, Enum):
    SEMANTIC = "semantic"       # Facts about user (skills, knowledge, roles)
    EPISODIC = "episodic"       # Past events, experiences, sessions
    PROCEDURAL = "procedural"   # Preferences, workflows, habits
    WORKING = "working"         # Current active session / task context

class Memory(Base):
    __tablename__ = "memories"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_type = Column(String(32), nullable=False, index=True)
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5, nullable=False, index=True)
    source = Column(String(64), default="conversation", nullable=False)  # conversation, manual, task, document
    source_id = Column(String(255), nullable=True)                       # conversation_id, task_id, etc.
    mem_metadata = Column(JSON, default=dict, nullable=False)            # entities, topics, tags, etc.
    embedding = Column(VectorType(dim=settings.EMBEDDING_DIM), nullable=True)
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="memories")
