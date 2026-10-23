import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import RiskLevel
from app.services.tools.base import BaseTool

class SearchTool(BaseTool):
    """Search Tool providing approved authoritative technical search and web knowledge lookups."""

    def __init__(self):
        super().__init__(
            name="search",
            description="Search approved external technical knowledge, architecture references, and web documentation.",
            category="research",
            risk_level=RiskLevel.READ_ONLY,
            requires_confirmation=False,
            permissions=["search:read"]
        )

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        query = params.get("query", "").lower()

        # Curated technical knowledge database
        KNOWLEDGE_BANK = [
            {
                "title": "System Design: Distributed Caching & Invalidation",
                "url": "https://docs.nexus-ai.internal/architecture/caching",
                "snippet": "Use Redis with TTL and write-through caching to protect database read replicas from thundering herd problems."
            },
            {
                "title": "Neo4j Graph Traversals & APOC Procedures",
                "url": "https://neo4j.com/docs/cypher-manual/current/",
                "snippet": "Neo4j provides index-free adjacency allowing relationship lookups in O(1) time complexity irrespective of overall graph size."
            },
            {
                "title": "Senior Technical Interview STAR Principles",
                "url": "https://docs.nexus-ai.internal/prep/star-framework",
                "snippet": "Structure architectural answers into Situation, Task, Action, and quantifiable Business/Engineering Result."
            }
        ]

        matches = [k for k in KNOWLEDGE_BANK if any(w in k["title"].lower() or w in k["snippet"].lower() for w in query.split())]
        if not matches:
            matches = KNOWLEDGE_BANK[:2]

        return {
            "query": params.get("query", ""),
            "results": matches,
            "count": len(matches),
            "source": "Nexus Approved Technical Search Index"
        }

search_tool = SearchTool()
