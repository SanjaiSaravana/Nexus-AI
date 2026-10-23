import uuid
import pytest
from app.services.graph.extractor import graph_extractor
from app.services.graph.neo4j_client import neo4j_client
from app.services.graph.graph_service import graph_service
from app.services.rag_service import rag_service

@pytest.mark.asyncio
async def test_entity_extraction():
    """Test extraction and normalization of all 11 required entity types."""
    sample_text = (
        "Project Nexus AI is developed using Python, React, and Neo4j. "
        "User knows Machine Learning and SQL. "
        "Job Software Engineer requires Python and System Design. "
        "Document architecture.pdf describes Project Nexus AI. "
        "Task 'Implement Neo4j Integration' supports Goal 'Master Knowledge Graphs'. "
        "Event 'Sprint Planning Meeting' relates to Project Nexus AI. "
        "User works at Google on Artificial Intelligence."
    )

    entities, relationships = graph_extractor.extract_entities_and_relationships(
        text=sample_text,
        user_name="Alice",
        document_name="architecture.pdf"
    )

    labels = {e.label for e in entities}
    names = {e.name for e in entities}

    # All required entities verified
    assert "User" in labels
    assert "Project" in labels
    assert "Skill" in labels
    assert "Technology" in labels
    assert "Document" in labels
    assert "Task" in labels
    assert "Goal" in labels
    assert "Event" in labels
    assert "Company" in labels
    assert "Job" in labels
    assert "Topic" in labels

    # Specific canonical entities
    assert "Python" in names
    assert "React" in names
    assert "Neo4j" in names
    assert "Nexus AI" in names
    assert "Google" in names
    assert "Software Engineer" in names

@pytest.mark.asyncio
async def test_relationship_extraction():
    """Test extraction of all specified typed relationships."""
    sample_text = (
        "My project Nexus AI uses Python and Neo4j. "
        "User knows Python and Machine Learning. "
        "Job Data Scientist requires Machine Learning. "
        "Document 'Nexus Guide' describes Project Nexus AI. "
        "Task 'Graph Engine' supports Goal 'Launch Phase 4'. "
        "Event 'Demo Review' relates to Project Nexus AI."
    )

    entities, relationships = graph_extractor.extract_entities_and_relationships(
        text=sample_text,
        user_name="Alice",
        document_name="Nexus Guide"
    )

    rel_tuples = {(r.source_label, r.relationship_type, r.target_label) for r in relationships}

    # 1. USER -> OWNS -> PROJECT
    assert ("User", "OWNS", "Project") in rel_tuples

    # 2. PROJECT -> USES -> TECHNOLOGY
    assert ("Project", "USES", "Technology") in rel_tuples

    # 3. USER -> KNOWS -> SKILL
    assert ("User", "KNOWS", "Skill") in rel_tuples

    # 4. JOB -> REQUIRES -> SKILL
    assert ("Job", "REQUIRES", "Skill") in rel_tuples

    # 5. DOCUMENT -> DESCRIBES -> PROJECT
    assert ("Document", "DESCRIBES", "Project") in rel_tuples

    # 6. TASK -> SUPPORTS -> GOAL
    assert ("Task", "SUPPORTS", "Goal") in rel_tuples

    # 7. EVENT -> RELATES_TO -> PROJECT
    assert ("Event", "RELATES_TO", "Project") in rel_tuples

@pytest.mark.asyncio
async def test_graph_insertion():
    """Test inserting nodes and relationships into graph repository."""
    user_id = str(uuid.uuid4())

    # Add Project node
    proj_node = await neo4j_client.add_node(
        user_id=user_id,
        label="Project",
        name="Project Phoenix",
        properties={"status": "active"}
    )
    assert proj_node["name"] == "Project Phoenix"
    assert proj_node["user_id"] == user_id

    # Add Technology node
    tech_node = await neo4j_client.add_node(
        user_id=user_id,
        label="Technology",
        name="Python",
        properties={"category": "language"}
    )
    assert tech_node["name"] == "Python"

    # Add PROJECT -> USES -> TECHNOLOGY edge
    edge = await neo4j_client.add_edge(
        user_id=user_id,
        source_id=proj_node["id"],
        target_id=tech_node["id"],
        rel_type="USES"
    )
    assert edge is not None
    assert edge["source"] == proj_node["id"]
    assert edge["target"] == tech_node["id"]
    assert edge["type"] == "USES"

    # Verify retrieval
    user_nodes = await neo4j_client.get_nodes(user_id=user_id)
    assert len(user_nodes) == 2

    user_edges = await neo4j_client.get_edges(user_id=user_id)
    assert len(user_edges) == 1

@pytest.mark.asyncio
async def test_duplicate_handling():
    """Test that entities and relationships are normalized and deduplicated."""
    user_id = str(uuid.uuid4())

    # Adding "Python", "python", "py" normalized
    n1 = await neo4j_client.add_node(user_id=user_id, label="Technology", name="Python")
    n2 = await neo4j_client.add_node(user_id=user_id, label="Technology", name="python")
    n3 = await neo4j_client.add_node(user_id=user_id, label="Technology", name="Python", properties={"version": "3.11"})

    assert n1["id"] == n2["id"] == n3["id"]
    assert n3["properties"]["version"] == "3.11"

    # Verify only 1 node was stored for Technology Python
    nodes = await neo4j_client.get_nodes(user_id=user_id, label="Technology")
    assert len(nodes) == 1
    assert nodes[0]["name"] == "Python"

    # Adding duplicate edge
    proj = await neo4j_client.add_node(user_id=user_id, label="Project", name="Nexus")
    e1 = await neo4j_client.add_edge(user_id=user_id, source_id=proj["id"], target_id=n1["id"], rel_type="USES")
    e2 = await neo4j_client.add_edge(user_id=user_id, source_id=proj["id"], target_id=n1["id"], rel_type="USES")
    assert e1["id"] == e2["id"]

    edges = await neo4j_client.get_edges(user_id=user_id)
    assert len(edges) == 1

@pytest.mark.asyncio
async def test_graph_retrieval():
    """Test natural language graph queries such as 'What projects do I have that use Python?'."""
    user_id = uuid.uuid4()
    user_id_str = str(user_id)

    # Ingest document text containing relationships
    doc_id = uuid.uuid4()
    doc_text = "Project Nexus AI uses Python, FastAPI, and Neo4j. User knows Python and Data Science."
    await graph_service.ingest_document_entities(
        user_id=user_id,
        document_id=doc_id,
        filename="overview.md",
        text=doc_text,
        user_name="Alice"
    )

    # Query 1: "What projects do I have that use Python?"
    res = await graph_service.query_graph(user_id=user_id, query="What projects do I have that use Python?")
    assert res.intent == "projects_using_technology"
    assert "Nexus AI" in res.answer
    assert any(n.name == "Nexus AI" for n in res.nodes)
    assert any(n.name == "Python" for n in res.nodes)
    assert "USES" in res.cypher

    # Query 2: "What skills do I know?"
    res_skills = await graph_service.query_graph(user_id=user_id, query="What skills do I know?")
    assert res_skills.intent == "user_skills"
    assert "Python" in res_skills.answer or "Data Science" in res_skills.answer

@pytest.mark.asyncio
async def test_user_isolation():
    """Verify strict tenant isolation: User A cannot see or query User B's graph."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # User A creates a secret project using Rust
    await neo4j_client.add_node(user_id=str(user_a), label="Project", name="Secret Project A")
    rust_node = await neo4j_client.add_node(user_id=str(user_a), label="Technology", name="Rust")
    proj_a_node = (await neo4j_client.get_nodes(user_id=str(user_a), label="Project"))[0]
    await neo4j_client.add_edge(user_id=str(user_a), source_id=proj_a_node["id"], target_id=rust_node["id"], rel_type="USES")

    # User B queries their graph
    b_nodes = await neo4j_client.get_nodes(user_id=str(user_b))
    assert len(b_nodes) == 0

    b_edges = await neo4j_client.get_edges(user_id=str(user_b))
    assert len(b_edges) == 0

    # User B asks "What projects do I have that use Rust?"
    res_b = await graph_service.query_graph(user_id=user_b, query="What projects do I have that use Rust?")
    assert "No projects were found" in res_b.answer
    assert len(res_b.nodes) == 0

    # User B attempts to delete User A's node -> False
    deleted = await neo4j_client.delete_node(user_id=str(user_b), node_id=proj_a_node["id"])
    assert deleted is False

    # User A's data remains untouched
    a_nodes = await neo4j_client.get_nodes(user_id=str(user_a))
    assert len(a_nodes) == 2

@pytest.mark.asyncio
async def test_hybrid_rag_graph():
    """Verify that RAG context combines vector knowledge with knowledge graph facts."""
    user_id = uuid.uuid4()
    user_id_str = str(user_id)

    # Ingest graph entities
    p = await neo4j_client.add_node(user_id=user_id_str, label="Project", name="Nexus Core")
    t = await neo4j_client.add_node(user_id=user_id_str, label="Technology", name="Python")
    await neo4j_client.add_edge(user_id=user_id_str, source_id=p["id"], target_id=t["id"], rel_type="USES")

    # Get RAG context
    graph_context = await graph_service.get_rag_context(user_id=user_id, query="Tell me about Python projects")
    assert "Nexus Core" in graph_context
    assert "uses technology 'Python'" in graph_context

    # Generate grounded response with graph context
    ans, citations = await rag_service.generate_response(
        query="What projects use Python?",
        context="",
        citations=[],
        graph_context=graph_context
    )
    assert "Nexus Core" in ans
    assert "Python" in ans

@pytest.mark.asyncio
async def test_knowledge_graph_api(client, user_a_headers, user_b_headers):
    """Test Knowledge Graph REST API endpoints."""
    # 1. User A creates a project in DB
    p_resp = await client.post("/projects", json={"name": "Alpha Platform", "description": "Built using Python and React"}, headers=user_a_headers)
    assert p_resp.status_code == 201

    # 2. Sync database to knowledge graph
    sync_resp = await client.post("/api/v1/knowledge-graph/sync", headers=user_a_headers)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["synced_nodes"] >= 2

    # 3. Get user graph
    g_resp = await client.get("/api/v1/knowledge-graph", headers=user_a_headers)
    assert g_resp.status_code == 200
    graph_data = g_resp.json()
    assert len(graph_data["nodes"]) >= 2
    assert any(n["name"] == "Alpha Platform" for n in graph_data["nodes"])

    # 4. Get stats
    stats_resp = await client.get("/api/v1/knowledge-graph/stats", headers=user_a_headers)
    assert stats_resp.status_code == 200
    assert stats_resp.json()["total_nodes"] >= 2

    # 5. Natural language query endpoint
    q_resp = await client.post(
        "/api/v1/knowledge-graph/query",
        json={"query": "What projects do I have that use Python?"},
        headers=user_a_headers
    )
    assert q_resp.status_code == 200
    q_data = q_resp.json()
    assert "Alpha Platform" in q_data["answer"]

    # 6. User B cannot see User A's graph data
    b_graph_resp = await client.get("/api/v1/knowledge-graph", headers=user_b_headers)
    assert b_graph_resp.status_code == 200
    assert len(b_graph_resp.json()["nodes"]) == 0

    # 7. Extract endpoint
    ext_resp = await client.post(
        "/api/v1/knowledge-graph/extract",
        json={"text": "Task 'Setup DB' supports Goal 'Launch Beta'"},
        headers=user_a_headers
    )
    assert ext_resp.status_code == 200
    assert len(ext_resp.json()["entities"]) >= 2
