import uuid
import re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.knowledge_graph import (
    GraphData,
    GraphQueryRequest,
    GraphQueryResponse,
    CypherQueryRequest,
    CypherQueryResponse,
    EntityExtractionRequest,
    EntityExtractionResponse,
    GraphStatsResponse,
    GraphSyncResponse,
    ExtractedEntity,
    ExtractedRelationship
)
from app.services.graph.graph_service import graph_service
from app.services.graph.neo4j_client import neo4j_client
from app.services.graph.extractor import graph_extractor

router = APIRouter()

@router.get("", response_model=GraphData)
async def get_knowledge_graph(
    label: Optional[str] = Query(None, description="Filter by node label (e.g. Project, Skill, Technology, Task, Goal, Document)"),
    search: Optional[str] = Query(None, description="Search term for node names"),
    limit: int = Query(300, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """Get user's knowledge graph nodes and edges for visualization."""
    return await graph_service.get_user_graph_data(
        user_id=current_user.id,
        label=label,
        search=search,
        limit=limit
    )

@router.get("/neighborhood", response_model=GraphData)
async def get_graph_neighborhood(
    node_id: Optional[str] = Query(None, description="Starting node ID for neighborhood exploration"),
    depth: int = Query(2, ge=1, le=5),
    limit: int = Query(150, ge=1, le=500),
    current_user: User = Depends(get_current_user)
):
    """Traverse graph neighborhood from a specific node up to specified depth hops."""
    data = await neo4j_client.get_neighborhood(
        user_id=str(current_user.id),
        node_id=node_id,
        depth=depth,
        limit=limit
    )
    return GraphData(nodes=data["nodes"], edges=data["edges"])

@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    current_user: User = Depends(get_current_user)
):
    """Get metrics and breakdown of user's knowledge graph."""
    stats = await neo4j_client.get_stats(str(current_user.id))
    return GraphStatsResponse(**stats)

@router.post("/query", response_model=GraphQueryResponse)
async def query_knowledge_graph(
    request: GraphQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute natural language relational query over user's Knowledge Graph."""
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )
    return await graph_service.query_graph(
        user_id=current_user.id,
        query=request.query
    )

@router.post("/cypher", response_model=CypherQueryResponse)
async def execute_safe_cypher(
    request: CypherQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute read-only safe Cypher query restricted to user's partition."""
    cypher_clean = request.cypher.strip()
    forbidden_tokens = ["delete", "drop", "create", "merge", "set", "remove", "alter", "call"]
    if any(re.search(rf'\b{token}\b', cypher_clean, re.IGNORECASE) for token in forbidden_tokens):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only read-only MATCH/RETURN Cypher queries are permitted on this endpoint."
        )

    params = dict(request.params or {})
    params["user_id"] = str(current_user.id)

    records = await neo4j_client.execute_cypher(cypher_clean, params)
    return CypherQueryResponse(cypher=cypher_clean, records=records)

@router.post("/extract", response_model=EntityExtractionResponse)
async def extract_entities_from_text(
    request: EntityExtractionRequest,
    persist: bool = Query(False, description="Whether to immediately ingest extracted entities into graph"),
    current_user: User = Depends(get_current_user)
):
    """Extract entities and typed relationships from text with normalization and deduplication."""
    user_name = current_user.profile.full_name if (current_user.profile and current_user.profile.full_name) else current_user.username
    entities, relationships = graph_extractor.extract_entities_and_relationships(
        text=request.text,
        user_name=user_name,
        document_name=request.document_name
    )

    if persist:
        # Save to graph
        for ent in entities:
            await neo4j_client.add_node(
                user_id=str(current_user.id),
                label=ent.label,
                name=ent.name,
                properties=ent.properties
            )

    return EntityExtractionResponse(entities=entities, relationships=relationships)

@router.post("/sync", response_model=GraphSyncResponse)
async def sync_database_to_graph(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Synchronize relational database entities (Projects, Tasks, Goals, Documents) to Neo4j graph."""
    res = await graph_service.sync_user_database(user_id=current_user.id, db=db)
    return GraphSyncResponse(
        message="Knowledge Graph synchronized successfully with relational records.",
        synced_nodes=res["synced_nodes"],
        synced_edges=res["synced_edges"]
    )

@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_graph_node(
    node_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a node and all connected relationships."""
    success = await neo4j_client.delete_node(str(current_user.id), node_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found or not owned by user."
        )
    return None

@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_graph(
    current_user: User = Depends(get_current_user)
):
    """Clear all knowledge graph nodes and edges for the current user."""
    await neo4j_client.clear_user_graph(str(current_user.id))
    return None
