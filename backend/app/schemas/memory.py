import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class MemoryBase(BaseModel):
    content: str
    memory_type: str = Field(default="semantic", description="semantic, episodic, procedural, working")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = Field(default="conversation")
    source_id: Optional[str] = None
    mem_metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryCreate(BaseModel):
    content: str
    memory_type: str = Field(default="semantic")
    importance: float = Field(default=0.7, ge=0.0, le=1.0)
    source: str = Field(default="manual")
    source_id: Optional[str] = None
    mem_metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[str] = None
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mem_metadata: Optional[Dict[str, Any]] = None

class MemoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    memory_type: str
    content: str
    importance: float
    source: str
    source_id: Optional[str] = None
    mem_metadata: Dict[str, Any] = Field(default_factory=dict)
    access_count: int = 0
    last_accessed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MemoryStatsResponse(BaseModel):
    total: int
    semantic_count: int
    episodic_count: int
    procedural_count: int
    working_count: int
    avg_importance: float

class MemoryExtractRequest(BaseModel):
    text: str
    context: Optional[str] = None

class ExtractedMemoryItem(BaseModel):
    content: str
    memory_type: str
    importance: float
    reason: str
    entities: List[str] = Field(default_factory=list)

class MemoryExtractResponse(BaseModel):
    extracted: List[ExtractedMemoryItem]
