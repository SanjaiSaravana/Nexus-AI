import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentType,
    MemoryRecallItem,
    MemoryRecallOutput
)
from app.models.memory import Memory
from app.services.agents.base import BaseAgent
from app.services.memory_service import memory_service

class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type=AgentType.MEMORY,
            name="Memory Agent",
            description="Selectively retrieves contextually relevant memories using semantic relevance and importance weights.",
            activity_message="Checking memory..."
        )

    async def _process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        query = input_data.get("query") or input_data.get("message") or context.get("message", "")

        # Count total memories in user store (for audit/verification that we do not retrieve all)
        count_stmt = select(func.count(Memory.id)).where(Memory.user_id == user_id)
        count_res = await db.execute(count_stmt)
        total_in_db = count_res.scalar() or 0

        # Retrieve top semantically scored memories
        # Strictly limited top_k (max 5)
        raw_retrieved = await memory_service.retrieve_memories(
            db=db,
            user_id=user_id,
            query=query,
            top_k=5
        )

        recalled_items: List[MemoryRecallItem] = []

        # Filter strictly by composite relevance and importance
        # Threshold: relevance score >= 0.40 and importance >= 0.35
        for mem, score in raw_retrieved:
            # Importance is normalized 0.0 to 1.0 (or 1 to 10 scaled to 0.1-1.0)
            imp_norm = mem.importance if mem.importance <= 1.0 else (mem.importance / 10.0)
            composite_score = (0.6 * float(score)) + (0.4 * imp_norm)

            if composite_score >= 0.35:
                recalled_items.append(
                    MemoryRecallItem(
                        memory_id=str(mem.id),
                        content=mem.content,
                        memory_type=mem.memory_type,
                        importance=round(float(mem.importance), 2),
                        relevance_score=round(composite_score, 3)
                    )
                )

        # Sort by composite score descending
        recalled_items.sort(key=lambda x: x.relevance_score, reverse=True)

        # Cap output to top 4 most pertinent items
        final_items = recalled_items[:4]

        synthesis_lines = [f"- [{item.memory_type.upper()}] {item.content}" for item in final_items]
        synthesis = "\n".join(synthesis_lines) if synthesis_lines else "No high-salience memories matched query criteria."

        output = MemoryRecallOutput(
            memories=final_items,
            retrieved_count=len(final_items),
            total_evaluated=total_in_db,
            synthesis=synthesis
        )
        return output.model_dump()

    async def _fallback(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession,
        user_id: uuid.UUID,
        error: Exception
    ) -> Optional[Dict[str, Any]]:
        # Degraded fallback with empty or safe memory list
        output = MemoryRecallOutput(
            memories=[],
            retrieved_count=0,
            total_evaluated=0,
            synthesis="Memory retrieval bypassed due to fallback."
        )
        return output.model_dump()

memory_agent = MemoryAgent()
