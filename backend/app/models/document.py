import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base, GUID, VectorType
from app.core.config import settings

def utcnow():
    return datetime.now(timezone.utc)

class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)  # pdf, docx, txt, md, csv
    file_size = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="processed", nullable=False, index=True)  # processing, processed, failed
    doc_metadata = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_heading = Column(String(255), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    embedding = Column(VectorType(dim=settings.EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    document = relationship("Document", back_populates="chunks")
    user = relationship("User", back_populates="document_chunks")
