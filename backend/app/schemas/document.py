import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict

class DocumentChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentBase(BaseModel):
    filename: str
    document_type: str
    file_size: int
    status: str = "processed"
    doc_metadata: Dict[str, Any] = {}

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentDetailResponse(DocumentResponse):
    chunks: List[DocumentChunkResponse] = []

class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse
    chunks_created: int
