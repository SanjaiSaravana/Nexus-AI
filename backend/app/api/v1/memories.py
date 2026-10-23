import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.memory import Memory, MemoryType
from app.schemas.memory import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    MemoryStatsResponse,
    MemoryExtractRequest,
    MemoryExtractResponse,
    ExtractedMemoryItem
)
from app.services.memory_service import memory_service, utcnow
from app.services.embedding import embedding_service

router = APIRouter(tags=["memories"])

@router.get("", response_model=List[MemoryResponse])
async def list_memories(
    memory_type: Optional[str] = Query(None, description="semantic, episodic, procedural, working"),
    search: Optional[str] = Query(None, description="Search term across memory content"),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List memories for the current user with optional filtering by type and search terms."""
    stmt = (
        select(Memory)
        .where(Memory.user_id == current_user.id)
        .where(Memory.importance >= min_importance)
    )
    if memory_type:
        stmt = stmt.where(Memory.memory_type == memory_type)
    if search:
        search_term = f"%{search.strip().lower()}%"
        stmt = stmt.where(func.lower(Memory.content).like(search_term))

    stmt = stmt.order_by(Memory.importance.desc(), Memory.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get aggregated memory statistics across all types for the current user."""
    stmt = select(Memory).where(Memory.user_id == current_user.id)
    res = await db.execute(stmt)
    memories = res.scalars().all()

    total = len(memories)
    semantic_count = sum(1 for m in memories if m.memory_type == MemoryType.SEMANTIC.value)
    episodic_count = sum(1 for m in memories if m.memory_type == MemoryType.EPISODIC.value)
    procedural_count = sum(1 for m in memories if m.memory_type == MemoryType.PROCEDURAL.value)
    working_count = sum(1 for m in memories if m.memory_type == MemoryType.WORKING.value)
    avg_imp = (sum(m.importance for m in memories) / total) if total > 0 else 0.0

    return MemoryStatsResponse(
        total=total,
        semantic_count=semantic_count,
        episodic_count=episodic_count,
        procedural_count=procedural_count,
        working_count=working_count,
        avg_importance=round(avg_imp, 2)
    )

@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually create or consolidate a memory for the current user."""
    candidate = {
        "content": data.content.strip(),
        "memory_type": data.memory_type,
        "importance": data.importance,
        "reason": "Manually entered user memory",
        "entities": data.mem_metadata.get("entities", [])
    }
    mem, _ = await memory_service.deduplicate_and_store(
        db,
        user_id=current_user.id,
        candidate=candidate,
        source=data.source,
        source_id=data.source_id
    )
    return mem

@router.post("/extract", response_model=MemoryExtractResponse)
async def extract_memories_endpoint(
    data: MemoryExtractRequest,
    current_user: User = Depends(get_current_user)
):
    """Extract candidate memories from arbitrary text without saving them."""
    candidates = memory_service.extract_memories(data.text)
    items = [
        ExtractedMemoryItem(
            content=c["content"],
            memory_type=c["memory_type"],
            importance=c["importance"],
            reason=c.get("reason", "Detected user fact"),
            entities=c.get("entities", [])
        )
        for c in candidates
    ]
    return MemoryExtractResponse(extracted=items)

@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details of a specific memory."""
    stmt = (
        select(Memory)
        .where(Memory.id == memory_id)
        .where(Memory.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    mem = res.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return mem

@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: uuid.UUID,
    data: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update memory content, type, importance, or metadata."""
    stmt = (
        select(Memory)
        .where(Memory.id == memory_id)
        .where(Memory.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    mem = res.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    if data.content is not None and data.content.strip():
        mem.content = data.content.strip()
        mem.embedding = await embedding_service.get_embedding(mem.content)

    if data.memory_type is not None:
        mem.memory_type = data.memory_type

    if data.importance is not None:
        mem.importance = data.importance

    if data.mem_metadata is not None:
        mem.mem_metadata = data.mem_metadata

    mem.updated_at = utcnow()
    await db.commit()
    await db.refresh(mem)
    return mem

@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a memory permanently, ensuring strict user isolation."""
    stmt = (
        select(Memory)
        .where(Memory.id == memory_id)
        .where(Memory.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    mem = res.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    await db.delete(mem)
    await db.commit()
    return None
