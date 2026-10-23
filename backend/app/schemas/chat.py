import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class Citation(BaseModel):
    citation_id: str
    document_id: str
    document_name: str
    chunk_id: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    excerpt: str
    relevance_score: float

class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: List[Citation] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class ConversationDetailResponse(ConversationResponse):
    messages: List[ChatMessageResponse] = []

class ChatQueryRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None
    document_ids: Optional[List[uuid.UUID]] = None
    top_k: int = 5

class ChatQueryResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: List[Citation] = []
