import pytest
import uuid
from app.models.memory import Memory, MemoryType
from app.services.memory_service import memory_service
from app.services.embedding import embedding_service

@pytest.mark.asyncio
async def test_memory_noise_filtering():
    """Verify conversational noise and trivial greetings are rejected."""
    noise_samples = [
        "Hi",
        "Hello there!",
        "Thanks a lot!",
        "ok",
        "cool",
        "What is Docker?",
        "How do I sort a list in Python?"
    ]
    for sample in noise_samples:
        assert memory_service.is_conversational_noise(sample) is True
        extracted = memory_service.extract_memories(sample)
        assert len(extracted) == 0

@pytest.mark.asyncio
async def test_memory_extraction_and_classification():
    """Verify extraction and classification into Semantic, Episodic, Procedural, and Working."""
    # 1. Semantic
    sem_text = "I know Python and TypeScript. I work as a senior backend engineer."
    extracted_sem = memory_service.extract_memories(sem_text)
    assert len(extracted_sem) >= 1
    types = [e["memory_type"] for e in extracted_sem]
    assert MemoryType.SEMANTIC.value in types
    assert any("python" in e["content"].lower() or "engineer" in e["content"].lower() for e in extracted_sem)

    # 2. Episodic
    epi_text = "Yesterday I had an interview at Google for a distributed systems role."
    extracted_epi = memory_service.extract_memories(epi_text)
    assert len(extracted_epi) >= 1
    assert extracted_epi[0]["memory_type"] == MemoryType.EPISODIC.value
    assert "interview" in extracted_epi[0]["content"].lower()

    # 3. Procedural
    proc_text = "I prefer dark mode and concise answers with type annotations."
    extracted_proc = memory_service.extract_memories(proc_text)
    assert len(extracted_proc) >= 1
    assert extracted_proc[0]["memory_type"] == MemoryType.PROCEDURAL.value
    assert "prefers" in extracted_proc[0]["content"].lower()

    # 4. Working
    work_text = "Currently working on database schema migrations for Phase 3."
    extracted_work = memory_service.extract_memories(work_text)
    assert len(extracted_work) >= 1
    assert extracted_work[0]["memory_type"] == MemoryType.WORKING.value

@pytest.mark.asyncio
async def test_memory_deduplication(db_session, user_a_headers):
    """Verify deduplication updates/reinforces existing memory instead of creating duplicates."""
    user_id = uuid.uuid4()
    candidate_1 = {
        "content": "User knows Python and FastAPI.",
        "memory_type": MemoryType.SEMANTIC.value,
        "importance": 0.85,
        "entities": ["python", "fastapi"]
    }
    mem1, is_new1 = await memory_service.deduplicate_and_store(db_session, user_id, candidate_1)
    assert is_new1 is True
    assert mem1.access_count == 1

    # Exact or near-identical duplicate
    candidate_2 = {
        "content": "User knows Python and FastAPI.",
        "memory_type": MemoryType.SEMANTIC.value,
        "importance": 0.90,
        "entities": ["python", "fastapi"]
    }
    mem2, is_new2 = await memory_service.deduplicate_and_store(db_session, user_id, candidate_2)
    assert is_new2 is False
    assert mem2.id == mem1.id
    assert mem2.access_count == 2
    assert mem2.importance == 0.90

@pytest.mark.asyncio
async def test_memory_retrieval(db_session):
    """Verify semantic memory retrieval with composite similarity and importance scoring."""
    user_id = uuid.uuid4()
    candidate_skills = {
        "content": "User knows Python, Kubernetes, and AWS.",
        "memory_type": MemoryType.SEMANTIC.value,
        "importance": 0.9,
        "entities": ["python", "kubernetes", "aws"]
    }
    candidate_pref = {
        "content": "User prefers dark mode and concise code snippets.",
        "memory_type": MemoryType.PROCEDURAL.value,
        "importance": 0.8,
        "entities": ["dark mode"]
    }
    await memory_service.deduplicate_and_store(db_session, user_id, candidate_skills)
    await memory_service.deduplicate_and_store(db_session, user_id, candidate_pref)

    # Query for skills
    results = await memory_service.retrieve_memories(
        db=db_session,
        user_id=user_id,
        query="What cloud and container technologies does user know?",
        top_k=2
    )
    assert len(results) > 0
    top_mem, score = results[0]
    assert "Kubernetes" in top_mem.content or "AWS" in top_mem.content
    assert score > 0.3

@pytest.mark.asyncio
async def test_memory_user_isolation(client, user_a_headers, user_b_headers):
    """Verify strict multi-tenant isolation: User A cannot see, edit, or delete User B's memories."""
    # 1. User A creates a memory
    resp_a = await client.post(
        "/memories",
        json={
            "content": "User A secret project is Operation Starlight.",
            "memory_type": "semantic",
            "importance": 0.95
        },
        headers=user_a_headers
    )
    assert resp_a.status_code == 201
    mem_a_id = resp_a.json()["id"]

    # 2. User B tries to view memories
    resp_b_list = await client.get("/memories", headers=user_b_headers)
    assert resp_b_list.status_code == 200
    b_mem_ids = [m["id"] for m in resp_b_list.json()]
    assert mem_a_id not in b_mem_ids

    # 3. User B tries to access User A's memory directly
    resp_b_get = await client.get(f"/memories/{mem_a_id}", headers=user_b_headers)
    assert resp_b_get.status_code == 404

    # 4. User B tries to edit User A's memory
    resp_b_patch = await client.patch(
        f"/memories/{mem_a_id}",
        json={"content": "Hacked content"},
        headers=user_b_headers
    )
    assert resp_b_patch.status_code == 404

    # 5. User B tries to delete User A's memory
    resp_b_del = await client.delete(f"/memories/{mem_a_id}", headers=user_b_headers)
    assert resp_b_del.status_code == 404

    # Cleanup: User A deletes own memory
    resp_a_del = await client.delete(f"/memories/{mem_a_id}", headers=user_a_headers)
    assert resp_a_del.status_code == 204

@pytest.mark.asyncio
async def test_memory_crud_api(client, user_a_headers):
    """Verify full CRUD lifecycle on /memories endpoints."""
    # Create
    post_resp = await client.post(
        "/memories",
        json={
            "content": "User prefers early morning deep work sessions.",
            "memory_type": "procedural",
            "importance": 0.85
        },
        headers=user_a_headers
    )
    assert post_resp.status_code == 201
    created = post_resp.json()
    mem_id = created["id"]
    assert created["memory_type"] == "procedural"

    # Read Detail
    get_resp = await client.get(f"/memories/{mem_id}", headers=user_a_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == "User prefers early morning deep work sessions."

    # Update
    patch_resp = await client.patch(
        f"/memories/{mem_id}",
        json={
            "content": "User prefers 90-minute morning deep work sessions with coffee.",
            "importance": 0.90
        },
        headers=user_a_headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["importance"] == 0.90
    assert "90-minute" in patch_resp.json()["content"]

    # Stats
    stats_resp = await client.get("/memories/stats", headers=user_a_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total"] >= 1
    assert stats["procedural_count"] >= 1

    # Delete
    del_resp = await client.delete(f"/memories/{mem_id}", headers=user_a_headers)
    assert del_resp.status_code == 204

    # Confirm deleted
    get_again = await client.get(f"/memories/{mem_id}", headers=user_a_headers)
    assert get_again.status_code == 404

@pytest.mark.asyncio
async def test_chat_memory_automatic_extraction_and_recall(client, user_a_headers):
    """Verify that chatting automatically extracts memories and recalls them in subsequent answers."""
    # 1. User shares background during chat
    chat_resp_1 = await client.post(
        "/chat/query",
        json={"message": "I know Python and Go. I work as a Staff Systems Architect."},
        headers=user_a_headers
    )
    assert chat_resp_1.status_code == 200

    # 2. Verify memory was created
    mems_resp = await client.get("/memories?memory_type=semantic", headers=user_a_headers)
    assert mems_resp.status_code == 200
    mems = mems_resp.json()
    assert len(mems) >= 1
    contents = " ".join(m["content"] for m in mems)
    assert "Python" in contents or "Architect" in contents

    # 3. Query recalling user profile
    chat_resp_2 = await client.post(
        "/chat/query",
        json={"message": "What programming languages do I know?"},
        headers=user_a_headers
    )
    assert chat_resp_2.status_code == 200
    ans_2 = chat_resp_2.json()["answer"]
    assert "Python" in ans_2 or "Go" in ans_2
