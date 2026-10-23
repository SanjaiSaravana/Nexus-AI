import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base, GUID

def utcnow():
    return datetime.now(timezone.utc)

def ensure_json_serializable(data):
    if isinstance(data, (datetime, )):
        return data.isoformat()
    elif isinstance(data, uuid.UUID):
        return str(data)
    elif isinstance(data, dict):
        return {k: ensure_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple, set)):
        return [ensure_json_serializable(item) for item in data]
    return data

def sanitize_parameters(params: dict) -> dict:
    """Sanitizes sensitive information from parameters before audit logging."""
    if not isinstance(params, dict):
        return {}
    sensitive_keys = {"password", "token", "secret", "authorization", "auth", "api_key", "credentials", "access_token"}
    sanitized = {}
    for k, v in params.items():
        if any(sk in k.lower() for sk in sensitive_keys):
            sanitized[k] = "******"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_parameters(v)
        elif isinstance(v, list):
            sanitized[k] = [sanitize_parameters(item) if isinstance(item, dict) else ensure_json_serializable(item) for item in v]
        elif isinstance(v, datetime):
            sanitized[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            sanitized[k] = str(v)
        else:
            sanitized[k] = ensure_json_serializable(v)
    return sanitized

class ActionProposal(Base):
    __tablename__ = "action_proposals"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)  # e.g., calendar.create_event, task.create_task
    tool_name = Column(String(50), nullable=False, index=True)    # calendar, task, email, github, document, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(JSON, default=dict, nullable=False)
    risk_level = Column(String(20), default="low", nullable=False)  # read_only, low, medium, high, critical
    requires_confirmation = Column(Boolean, default=True, nullable=False)
    status = Column(String(30), default="pending", nullable=False, index=True)  # pending, approved, rejected, executed, failed
    result = Column(JSON, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="action_proposals")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    tool = Column(String(50), nullable=False, index=True)
    parameters = Column(JSON, default=dict, nullable=False)  # Sanitized parameters
    approval_status = Column(String(30), nullable=False, index=True)  # auto_approved, user_approved, rejected, bypassed
    status = Column(String(30), nullable=False, index=True)  # success, failed, rejected
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    proposal_id = Column(GUID(), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
