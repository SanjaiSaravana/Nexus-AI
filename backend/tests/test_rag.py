import io
import pytest
from app.services.document_pipeline import document_pipeline, ParsedSection
from app.services.embedding import embedding_service
from app.services.rag_service import rag_service, ANTI_HALLUCINATION_RESPONSE

@pytest.mark.asyncio
async def test_document_pipeline_parsing_and_chunking():
    # 1. Text Parsing
    txt_content = b"Alex Mercer is a Senior AI Engineer specializing in Python, FastAPI, and Distributed Systems.\n\nHe has built scalable RAG pipelines and vector search architectures."
    txt_sections = document_pipeline.parse_document("skills.txt", txt_content)
    assert len(txt_sections) == 2
    assert "Alex Mercer" in txt_sections[0].content

    # 2. Markdown Parsing
    md_content = b"# Technical Skills\n- Python\n- PyTorch\n- pgvector\n\n# Work Experience\nStaff Engineer at DeepMind."
    md_sections = document_pipeline.parse_document("profile.md", md_content)
    assert len(md_sections) >= 2

    # 3. CSV Parsing
    csv_content = b"skill,years_experience,proficiency\nPython,8,Expert\nPostgreSQL,6,Advanced\nFastAPI,5,Expert"
    csv_sections = document_pipeline.parse_document("skills.csv", csv_content)
    assert len(csv_sections) >= 1
    assert "Python" in csv_sections[0].content

    # 4. Semantic Chunking
    chunks = document_pipeline.semantic_chunk(txt_sections, max_chunk_chars=100)
    assert len(chunks) >= 2
    assert chunks[0]["chunk_index"] == 0
    assert "page_number" in chunks[0]

@pytest.mark.asyncio
async def test_embeddings_and_vector_similarity():
    text_a = "Python backend development with FastAPI and PostgreSQL"
    text_b = "Python web APIs using FastAPI and async database queries"
    text_c = "Organic gardening techniques and tomato planting schedule"

    emb_a = await embedding_service.get_embedding(text_a)
    emb_b = await embedding_service.get_embedding(text_b)
    emb_c = await embedding_service.get_embedding(text_c)

    assert len(emb_a) == embedding_service.dim

    sim_ab = embedding_service.cosine_similarity(emb_a, emb_b)
    sim_ac = embedding_service.cosine_similarity(emb_a, emb_c)

    # Related texts must score significantly higher than unrelated texts
    assert sim_ab > sim_ac

@pytest.mark.asyncio
async def test_document_upload_and_retrieval(client, user_a_headers):
    # Upload TXT Document
    doc_content = (
        "Candidate: Alex Mercer\n"
        "Technical Skills: Python, FastAPI, SQLAlchemy, PostgreSQL, Docker, PyTorch, RAG Pipelines.\n"
        "Current Project: NEXUS AI Agentic Intelligence Platform.\n"
        "Education: Master of Computer Science."
    )
    files = {
        "file": ("resume.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")
    }

    upload_resp = await client.post("/documents/upload", files=files, headers=user_a_headers)
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()
    assert upload_data["document"]["filename"] == "resume.txt"
    doc_id = upload_data["document"]["id"]

    # List documents
    list_resp = await client.get("/documents", headers=user_a_headers)
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert any(d["id"] == doc_id for d in docs)

    # Chat query - Strongest Technical Skills
    chat_resp = await client.post(
        "/chat/query",
        json={"message": "What are my technical skills?"},
        headers=user_a_headers
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "Python" in chat_data["answer"]
    assert len(chat_data["citations"]) > 0
    assert chat_data["citations"][0]["document_name"] == "resume.txt"

@pytest.mark.asyncio
async def test_anti_hallucination_guard(client, user_a_headers):
    # Ask something completely absent from documents
    chat_resp = await client.post(
        "/chat/query",
        json={"message": "What is the secret recipe for Martian sourdough bread and warp drive fuel?"},
        headers=user_a_headers
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["answer"] == ANTI_HALLUCINATION_RESPONSE
    assert len(data["citations"]) == 0

@pytest.mark.asyncio
async def test_rag_user_isolation(client, user_a_headers, user_b_headers):
    # User A uploads a private confidential project plan
    private_doc = (
        "CONFIDENTIAL PROJECT ZEUS\n"
        "Budget: $10,000,000 USD\n"
        "Codename: Project Zeus Quantum Engine\n"
        "Authorized Personnel: User A Only."
    )
    files = {
        "file": ("project_zeus_confidential.txt", io.BytesIO(private_doc.encode("utf-8")), "text/plain")
    }
    upload_resp = await client.post("/documents/upload", files=files, headers=user_a_headers)
    assert upload_resp.status_code == 201
    doc_a_id = upload_resp.json()["document"]["id"]

    # 1. User B lists documents -> Must NOT see User A's document
    b_docs = (await client.get("/documents", headers=user_b_headers)).json()
    assert not any(d["id"] == doc_a_id for d in b_docs)

    # 2. User B tries direct GET /documents/{id} -> 404
    assert (await client.get(f"/documents/{doc_a_id}", headers=user_b_headers)).status_code == 404

    # 3. User B tries direct DELETE /documents/{id} -> 404
    assert (await client.delete(f"/documents/{doc_a_id}", headers=user_b_headers)).status_code == 404

    # 4. User B asks RAG about Project Zeus -> Must trigger anti-hallucination, zero leak!
    b_chat_resp = await client.post(
        "/chat/query",
        json={"message": "What is the budget and codename for Project Zeus?"},
        headers=user_b_headers
    )
    assert b_chat_resp.status_code == 200
    b_data = b_chat_resp.json()
    assert b_data["answer"] == ANTI_HALLUCINATION_RESPONSE
    assert len(b_data["citations"]) == 0
