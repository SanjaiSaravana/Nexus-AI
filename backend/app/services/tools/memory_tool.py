import uuid
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import RiskLevel
from app.models.memory import Memory, MemoryType
from app.services.tools.base import BaseTool
from app.services.memory_service import memory_service

class MemoryTool(BaseTool):
    """Personalized Memory Tool providing semantic search and memory storage."""

    def __init__(self):
        super().__init__(
            name="memory",
            description="Query user facts and preferences, or store high-salience memories.",
            category="memory",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            permissions=["memory:read", "memory:write"]
        )

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        if action == "search_memories":
            query = params.get("query", "")
            top_k = params.get("top_k", 5)
            results = await memory_service.retrieve_memories(
                db=db,
                user_id=user_id,
                query=query,
                top_k=top_k
            )
            return {
                "memories": [
                    {
                        "id": str(m.id),
                        "content": m.content,
                        "type": m.memory_type,
                        "importance": m.importance,
                        "score": round(float(s), 3)
                    }
                    for m, s in results
                ],
                "count": len(results)
            }
        elif action == "create_memory":
            content = params.get("content", "")
            mem_type = params.get("memory_type", MemoryType.SEMANTIC)
            importance = params.get("importance", 0.6)
            mem = await memory_service.store_memory(
                db=db,
                user_id=user_id,
                content=content,
                memory_type=mem_type,
                importance=importance,
                source="tool"
            )
            return {
                "id": str(mem.id),
                "content": mem.content,
                "type": mem.memory_type,
                "importance": mem.importance,
                "action": "created"
            }
        elif action == "delete_memory":
            mem_id = params.get("memory_id")
            if not mem_id:
                raise ValueError("Parameter 'memory_id' required")
            if isinstance(mem_id, str):
                mem_id = uuid.UUID(mem_id)
            stmt = select(Memory).where(Memory.id == mem_id, Memory.user_id == user_id)
            res = await db.execute(stmt)
            mem = res.scalar_one_or_none()
            if not mem:
                raise ValueError(f"Memory '{mem_id}' not found")
            await db.delete(mem)
            await db.flush()
            return {"id": str(mem_id), "status": "deleted"}
        else:
            raise ValueError(f"Unknown memory action '{action}'. Supported: search_memories, create_memory, delete_memory")

memory_tool = MemoryTool()
