import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"

class ApprovalStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    USER_APPROVED = "approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    BYPASSED = "bypassed"

# Tool Schema Representation
class ToolDefinitionResponse(BaseModel):
    name: str
    description: str
    category: str
    risk_level: RiskLevel
    requires_confirmation: bool
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    permissions: List[str] = []

class ToolExecutionResult(BaseModel):
    tool: str
    action: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

# Action Proposal Schemas
class ActionProposalCreate(BaseModel):
    tool_name: str
    action_type: str
    title: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ActionProposalResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action_type: str
    tool_name: str
    title: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    risk_level: str
    requires_confirmation: bool
    status: str
    result: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ActionApprovalRequest(BaseModel):
    approved: bool
    reason: Optional[str] = None

# Audit Log Schemas
class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    tool: str
    parameters: Dict[str, Any]
    approval_status: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    proposal_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# 1. Calendar Tool Specific Schemas
class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    event_type: str = "interview"
    is_all_day: bool = False

class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    event_type: Optional[str] = None

class CalendarEventResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    event_type: str
    is_all_day: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FreeSlotItem(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_minutes: int

# 2. Task Tool Specific Schemas
class TaskToolCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    priority: str = "medium"
    due_date: Optional[str] = None  # YYYY-MM-DD

class TaskToolUpdate(BaseModel):
    task_id: uuid.UUID
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None

# 3. Email Tool Specific Schemas
class EmailSendInput(BaseModel):
    recipient: str
    subject: str
    body: str
    cc: Optional[List[str]] = None

# 4. GitHub Tool Specific Schemas
class GitHubCreateIssueInput(BaseModel):
    repository: str
    title: str
    body: str
    labels: Optional[List[str]] = None
