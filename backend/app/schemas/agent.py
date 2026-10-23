import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.chat import Citation

class AgentType(str, Enum):
    PLANNER = "planner"
    RESEARCH = "research"
    MEMORY = "memory"
    PROJECT = "project"
    TASK = "task"
    CALENDAR = "calendar"
    EXECUTION = "execution"
    ORCHESTRATOR = "orchestrator"

class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRIED = "retried"
    SKIPPED = "skipped"

class UserIntent(str, Enum):
    INTERVIEW_PREP = "interview_prep"
    PROJECT_PLANNING = "project_planning"
    RESEARCH_QUERY = "research_query"
    TASK_GENERATION = "task_generation"
    GENERAL_ASSISTANCE = "general_assistance"

class AgentActivity(BaseModel):
    agent: AgentType
    activity: str
    status: AgentStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentState(BaseModel):
    run_id: uuid.UUID
    agent: AgentType
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    status: AgentStatus = AgentStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: Optional[str] = None
    retries: int = 0

    model_config = ConfigDict(from_attributes=True)

# 1. Planner Schemas
class SubTaskItem(BaseModel):
    step: int
    title: str
    description: str
    assigned_agent: AgentType
    status: str = "pending"

class PlannerOutput(BaseModel):
    intent: UserIntent
    goal: str
    summary: str
    subtasks: List[SubTaskItem]
    required_agents: List[AgentType]

# 2. Research Schemas
class FactItem(BaseModel):
    fact: str
    source_type: str  # document, graph, external
    source_name: str
    confidence: float = 1.0

class ResearchEvidence(BaseModel):
    query: str
    facts: List[FactItem] = []
    documents: List[Dict[str, Any]] = []
    graph_entities: List[Dict[str, Any]] = []
    citations: List[Citation] = []
    external_sources: List[Dict[str, Any]] = []
    summary: str = ""

# 3. Memory Schemas
class MemoryRecallItem(BaseModel):
    memory_id: str
    content: str
    memory_type: str
    importance: float
    relevance_score: float

class MemoryRecallOutput(BaseModel):
    memories: List[MemoryRecallItem] = []
    retrieved_count: int = 0
    total_evaluated: int = 0
    synthesis: str = ""

# 4. Project Schemas
class ProjectMatch(BaseModel):
    project_id: str
    project_name: str
    description: str
    matched_skills: List[str] = []
    relevance_score: float = 1.0
    alignment_notes: str = ""

class ProjectAnalysisOutput(BaseModel):
    matched_projects: List[ProjectMatch] = []
    identified_gaps: List[str] = []
    recommended_focus: List[str] = []
    summary: str = ""

# 5. Task Schemas
class GeneratedTaskItem(BaseModel):
    title: str
    description: str
    priority: str = "medium"  # low, medium, high, urgent
    due_date_offset_days: Optional[int] = 1
    category: str = "prep"

class TaskPlanOutput(BaseModel):
    tasks: List[GeneratedTaskItem] = []
    created_count: int = 0
    summary: str = ""

# 6. Calendar Schemas
class CalendarEventProposal(BaseModel):
    title: str
    description: str
    start_time_offset_hours: int = 2
    duration_minutes: int = 60
    event_type: str = "study_block"  # study_block, interview, mock_session, deadline

class CalendarAgentOutput(BaseModel):
    events: List[CalendarEventProposal] = []
    schedule_summary: str = ""

# 7. Execution Schemas
class ExecutedActionItem(BaseModel):
    action_type: str
    target: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ExecutionAgentOutput(BaseModel):
    actions: List[ExecutedActionItem] = []
    success: bool = True
    summary: str = ""

# Orchestration Full Result
class OrchestrationRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None
    document_ids: Optional[List[uuid.UUID]] = None
    auto_execute_tasks: bool = False
    auto_schedule_calendar: bool = False

class OrchestrationResult(BaseModel):
    run_id: uuid.UUID
    intent: UserIntent
    plan: PlannerOutput
    agent_states: List[AgentState]
    final_response: str
    citations: List[Citation] = []
    created_tasks: List[Dict[str, Any]] = []
    suggested_calendar_events: List[CalendarEventProposal] = []
    execution_summary: Dict[str, Any] = Field(default_factory=dict)
