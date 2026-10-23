import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentResponse, DocumentDetailResponse, DocumentUploadResponse
from app.services.document_pipeline import document_pipeline
from app.services.embedding import embedding_service
from app.services.graph.graph_service import graph_service
from app.core.config import settings

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload and ingest a document through parsing, cleaning, chunking, and embedding."""
    file_bytes = await file.read()
    file_size = len(file_bytes)
    filename = file.filename or "uploaded_document"
    sanitized_filename = document_pipeline.sanitize_filename(filename)

    # 1. Validation (extension, size, path traversal, magic bytes, malicious scripts)
    doc_type = document_pipeline.validate_file(
        filename=sanitized_filename,
        file_size=file_size,
        max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
        file_bytes=file_bytes
    )

    # 2. Parsing & Text extraction
    sections = document_pipeline.parse_document(sanitized_filename, file_bytes)

    # 3. Semantic Chunking
    chunks_data = document_pipeline.semantic_chunk(sections)

    if not chunks_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document contained no parseable semantic chunks."
        )

    # 4. Generate Embeddings for chunks
    chunk_texts = [c["content"] for c in chunks_data]
    embeddings = await embedding_service.get_embeddings(chunk_texts)

    # 5. Persist Document Record
    doc = Document(
        user_id=current_user.id,
        filename=sanitized_filename,
        document_type=doc_type,
        file_size=file_size,
        status="processed",
        doc_metadata={
            "mime_type": file.content_type,
            "section_count": len(sections),
            "chunk_count": len(chunks_data),
            "character_count": sum(len(c["content"]) for c in chunks_data)
        }
    )
    db.add(doc)
    await db.flush()

    # 6. Persist Document Chunks with Embeddings
    for idx, (c_data, emb) in enumerate(zip(chunks_data, embeddings)):
        chunk = DocumentChunk(
            document_id=doc.id,
            user_id=current_user.id,
            chunk_index=idx,
            content=c_data["content"],
            page_number=c_data.get("page_number", 1),
            section_heading=c_data.get("section_heading", "General"),
            metadata_json=c_data.get("metadata", {}),
            embedding=emb
        )
        db.add(chunk)

    await db.commit()
    await db.refresh(doc)

    # 7. Knowledge Graph Entity & Relationship Extraction -> Neo4j
    try:
        full_doc_text = "\n\n".join(c["content"] for c in chunks_data)
        user_name = current_user.profile.full_name if (current_user.profile and current_user.profile.full_name) else current_user.username
        await graph_service.ingest_document_entities(
            user_id=current_user.id,
            document_id=doc.id,
            filename=doc.filename,
            text=full_doc_text,
            user_name=user_name
        )
    except Exception:
        pass

    response_doc = DocumentResponse(
        id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        document_type=doc.document_type,
        file_size=doc.file_size,
        status=doc.status,
        doc_metadata=doc.doc_metadata,
        chunk_count=len(chunks_data),
        created_at=doc.created_at,
        updated_at=doc.updated_at
    )

    return DocumentUploadResponse(
        message=f"Document '{filename}' ingested successfully with {len(chunks_data)} chunks.",
        document=response_doc,
        chunks_created=len(chunks_data)
    )

@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all documents owned by current user with chunk count."""
    stmt = (
        select(Document, func.count(DocumentChunk.id).label("chunk_count"))
        .outerjoin(DocumentChunk, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == current_user.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    documents = []
    for doc, c_count in rows:
        documents.append(
            DocumentResponse(
                id=doc.id,
                user_id=doc.user_id,
                filename=doc.filename,
                document_type=doc.document_type,
                file_size=doc.file_size,
                status=doc.status,
                doc_metadata=doc.doc_metadata,
                chunk_count=c_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
        )
    return documents

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document details and preview chunks."""
    stmt = (
        select(Document)
        .options(selectinload(Document.chunks))
        .where(Document.id == document_id, Document.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return DocumentDetailResponse(
        id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        document_type=doc.document_type,
        file_size=doc.file_size,
        status=doc.status,
        doc_metadata=doc.doc_metadata,
        chunk_count=len(doc.chunks),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        chunks=doc.chunks
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document and all associated chunks."""
    stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    await db.delete(doc)
    await db.commit()
    return None
