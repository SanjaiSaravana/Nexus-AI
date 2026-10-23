import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import RiskLevel
from app.services.tools.base import BaseTool
from app.services.graph.neo4j_client import neo4j_client
from app.services.graph.graph_service import graph_service

class KnowledgeGraphTool(BaseTool):
    """Knowledge Graph Tool for querying relational subgraphs and executing Cypher lookups."""

    def __init__(self):
        super().__init__(
            name="knowledge_graph",
            description="Query entity nodes, relationships, and graph neighborhoods in Neo4j.",
            category="knowledge",
            risk_level=RiskLevel.READ_ONLY,
            requires_confirmation=False,
            permissions=["graph:read"]
        )

    async def _execute_action(
        self,
        action: str,
        user_id: uuid.UUID,
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        if action == "query_graph":
            query = params.get("query", "")
            ans = await graph_service.answer_graph_query(user_id=user_id, query=query)
            return ans.model_dump()
        elif action == "get_neighborhood":
            node_id = params.get("node_id", "")
            hops = params.get("hops", 1)
            nodes, edges = await neo4j_client.get_neighborhood(user_id=user_id, node_id=node_id, hops=hops)
            return {
                "nodes": [n.model_dump() for n in nodes],
                "edges": [e.model_dump() for e in edges],
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        elif action == "sync_database":
            res = await graph_service.sync_database_to_graph(user_id=user_id, db=db)
            return res.model_dump()
        else:
            raise ValueError(f"Unknown knowledge graph action '{action}'. Supported: query_graph, get_neighborhood, sync_database")

knowledge_graph_tool = KnowledgeGraphTool()
