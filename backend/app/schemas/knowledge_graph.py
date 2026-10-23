from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class GraphNode(BaseModel):
    id: str
    label: str
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphData(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)

class GraphQueryRequest(BaseModel):
    query: str

class GraphQueryResponse(BaseModel):
    query: str
    intent: str
    cypher: str
    answer: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)

class CypherQueryRequest(BaseModel):
    cypher: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CypherQueryResponse(BaseModel):
    cypher: str
    records: List[Dict[str, Any]] = Field(default_factory=list)

class ExtractedEntity(BaseModel):
    label: str
    name: str
    normalized_name: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class ExtractedRelationship(BaseModel):
    source_label: str
    source_name: str
    relationship_type: str
    target_label: str
    target_name: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class EntityExtractionRequest(BaseModel):
    text: str
    document_name: Optional[str] = None

class EntityExtractionResponse(BaseModel):
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]

class GraphStatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    node_counts: Dict[str, int] = Field(default_factory=dict)
    edge_counts: Dict[str, int] = Field(default_factory=dict)

class GraphSyncResponse(BaseModel):
    message: str
    synced_nodes: int
    synced_edges: int
