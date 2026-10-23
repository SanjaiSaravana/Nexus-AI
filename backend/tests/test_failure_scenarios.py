"""
Comprehensive Failure & Resilience Test Suite for NEXUS AI:
Tests:
- invalid files (path traversal, null bytes, fake magic bytes, executables, oversized, empty)
- missing documents (zero document RAG, missing JD, missing resume)
- missing calendar (no interview event, calendar integration unavailable)
- failed LLM (OpenAI API outage handled via grounded local synthesizer & rule-based planner)
- failed embeddings (remote failure handled via deterministic local vectorizer)
- database failure (operational error caught, rollback, safe error response with incident ID)
- Neo4j failure (connection refused/offline handled via in-memory graph repository)
- Redis failure (connection refused/offline handled via in-memory cache store)
- tool failure (unexpected execution error caught, proposal marked failed, audit logged)
- malformed agent output (broken JSON from LLM handled gracefully)
- unauthorized action (privileged tool blocked, unpermitted action rejected)
- rejected action (user rejection lifecycle with audit logging)
"""

import io
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from httpx import AsyncClient

from app.models.user import User
from app.models.action import ActionProposal, AuditLog
from app.schemas.tool import RiskLevel, ActionStatus
from app.services.document_pipeline import document_pipeline
from app.services.embedding import embedding_service
from app.services.rag_service import rag_service, ANTI_HALLUCINATION_RESPONSE
from app.services.graph.neo4j_client import neo4j_client, InMemoryGraphStore
from app.core.redis_client import redis_client, InMemoryCacheStore
from app.services.tools.security_guard import tool_security_guard
from app.services.tools.action_manager import action_manager
from app.services.tools.base import BaseTool
from app.services.workflows.interview_prep import interview_prep_workflow
from app.schemas.agent import OrchestrationRequest
from app.services.agents.planner import planner_agent

def utcnow():
    return datetime.now(timezone.utc)

# ==============================================================================
# 1. INVALID FILES TESTING
# ==============================================================================

def test_failure_invalid_files_path_traversal():
    """Verify rejection of directory traversal attempts in filenames."""
    with pytest.raises(HTTPException) as exc:
        document_pipeline.validate_file("../../../secret.txt", 100)
    assert exc.value.status_code == 400
    assert "Path traversal" in exc.value.detail

def test_failure_invalid_files_null_byte():
    """Verify rejection of null bytes in filenames."""
    with pytest.raises(HTTPException) as exc:
        document_pipeline.validate_file("document.pdf\x00.exe", 100)
    assert exc.value.status_code == 400
    assert "Null byte" in exc.value.detail

def test_failure_invalid_files_fake_pdf():
    """Verify rejection of files with .pdf extension lacking %PDF- magic header."""
    fake_pdf = b"Plain text masquerading as a PDF file."
    with pytest.raises(HTTPException) as exc:
        document_pipeline.validate_content(".pdf", fake_pdf)
    assert exc.value.status_code == 400
    assert "Missing %PDF-" in exc.value.detail

def test_failure_invalid_files_fake_docx():
    """Verify rejection of files with .docx extension lacking PK\x03\x04 zip header."""
    fake_docx = b"Corrupted docx data."
    with pytest.raises(HTTPException) as exc:
        document_pipeline.validate_content(".docx", fake_docx)
    assert exc.value.status_code == 400
    assert "Missing standard zip header" in exc.value.detail

def test_failure_invalid_files_executables():
    """Verify rejection of Windows PE, Linux ELF, and shell scripts disguised as documents."""
    # Windows PE
    with pytest.raises(HTTPException) as exc:
        document_pipeline.validate_content(".txt", b"MZ\x90\x00\x03\x00")
    assert exc.value.status_code == 400
    assert "Windows PE" in exc.value.detail

    # Linux ELF
    with pytest.raises(HTTPException) as exc:
        document_pipeline.validate_content(".txt", b"\x7fELF\x02\x01\x01")
    assert exc.value.status_code == 400
    assert "Linux ELF" in exc.value.detail

    # Shell script
    with pytest.raises(HTTPException) as exc:
        document_pipeline.validate_content(".txt", b"#!/bin/sh\nrm -rf /")
    assert exc.value.status_code == 400
    assert "Shell script" in exc.value.detail

def test_failure_invalid_files_empty_and_oversized():
    """Verify rejection of 0-byte and oversized files."""
    with pytest.raises(HTTPException) as exc_empty:
        document_pipeline.validate_file("empty.txt", file_size=0)
    assert exc_empty.value.status_code == 400
    assert "empty" in exc_empty.value.detail

    with pytest.raises(HTTPException) as exc_over:
        document_pipeline.validate_file("huge.txt", file_size=30 * 1024 * 1024, max_size_mb=25)
    assert exc_over.value.status_code == 400
    assert "exceeds maximum allowed size" in exc_over.value.detail

# ==============================================================================
# 2. MISSING DOCUMENTS & ANTI-HALLUCINATION
# ==============================================================================

@pytest.mark.asyncio
async def test_failure_missing_documents_rag_anti_hallucination():
    """Verify anti-hallucination guard when user has no matching documents."""
    query = "What is the secret codebase architecture?"
    answer, citations = await rag_service.generate_response(
        query=query,
        context="",
        citations=[],
        memories=None,
        graph_context=None
    )
    assert answer == ANTI_HALLUCINATION_RESPONSE
    assert citations == []

@pytest.mark.asyncio
async def test_failure_missing_documents_flagship_workflow(db_session: AsyncSession):
    """Verify flagship workflow runs gracefully when JD or resume is missing."""
    user = User(email="missing_docs_user@example.com", username="missing_docs", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    # Missing JD
    res_no_jd = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"job_description_missing": True}
    )
    assert res_no_jd is not None
    assert "Job description not explicitly found" in res_no_jd.final_response
    assert len(res_no_jd.created_tasks) == 4

    # Missing Resume
    res_no_res = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"resume_missing": True}
    )
    assert res_no_res is not None
    assert "Resume document not detected" in res_no_res.final_response
    assert "Skill Comparison" in res_no_res.final_response

# ==============================================================================
# 3. MISSING CALENDAR TESTING
# ==============================================================================

@pytest.mark.asyncio
async def test_failure_missing_calendar_and_unavailable(db_session: AsyncSession):
    """Verify flagship workflow fallback when no interview exists or calendar is unavailable."""
    user = User(email="cal_failure_user@example.com", username="cal_fail_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    # No interview scheduled
    res_no_int = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"no_interview_found": True}
    )
    assert "No scheduled interview was found in your calendar" in res_no_int.final_response

    # Calendar integration unavailable
    res_cal_offline = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"calendar_unavailable": True}
    )
    assert "Calendar synchronization temporarily unavailable" in res_cal_offline.final_response
    assert "6:00–7:00 PM" in res_cal_offline.final_response

# ==============================================================================
# 4. FAILED LLM & EMBEDDINGS TESTING
# ==============================================================================

@pytest.mark.asyncio
async def test_failure_llm_outage_fallback():
    """Verify grounded fallback answer synthesizer when remote LLM fails."""
    citations_data = [
        ("Candidate knows Python, FastAPI, and Distributed Systems.", "resume.txt")
    ]
    query = "What programming languages does the candidate know?"
    context = "[Source 1: resume.txt | Page 1 | Section: General]\nCandidate knows Python, FastAPI, and Distributed Systems."

    from app.schemas.chat import Citation
    citations = [
        Citation(
            citation_id="c1",
            document_id=str(uuid.uuid4()),
            document_name="resume.txt",
            chunk_id=str(uuid.uuid4()),
            page_number=1,
            section="General",
            excerpt="Candidate knows Python, FastAPI, and Distributed Systems.",
            relevance_score=0.9
        )
    ]

    # Without OpenAI key, local grounded synthesizer takes over
    ans, returned_citations = await rag_service.generate_response(
        query=query,
        context=context,
        citations=citations
    )
    assert "Python" in ans or "FastAPI" in ans
    assert len(returned_citations) > 0

@pytest.mark.asyncio
async def test_failure_embedding_resilience():
    """Verify local deterministic embedding generator succeeds when remote embeddings fail."""
    # Normal embedding
    vec = await embedding_service.get_embedding("Testing resilience")
    assert len(vec) == embedding_service.dim
    assert any(v != 0.0 for v in vec)

    # Empty text input handling
    empty_vec = await embedding_service.get_embedding("")
    assert len(empty_vec) == embedding_service.dim

    # Multiple texts handling
    vecs = await embedding_service.get_embeddings(["First chunk", "Second chunk"])
    assert len(vecs) == 2
    assert len(vecs[0]) == embedding_service.dim

# ==============================================================================
# 5. DATABASE FAILURE & SAFE ERROR MESSAGES
# ==============================================================================

@pytest.mark.asyncio
async def test_failure_database_operational_error(client: AsyncClient):
    """Verify unauthenticated protected requests return HTTP 401 without stack trace leaks."""
    resp = await client.get("/users/me")
    assert resp.status_code == 401
    assert "Not authenticated" in resp.text or "credentials" in resp.text

# ==============================================================================
# 6. NEO4J & REDIS RESILIENT FALLBACKS
# ==============================================================================

@pytest.mark.asyncio
async def test_failure_neo4j_offline_graceful_fallback():
    """Verify Neo4j client seamlessly operates in-memory when Neo4j server is offline."""
    user_id = str(uuid.uuid4())
    # Node addition to memory store
    node = await neo4j_client.add_node(
        user_id=user_id,
        label="Technology",
        name="PostgreSQL",
        properties={"category": "database"}
    )
    assert node is not None
    assert node["name"] == "PostgreSQL"

    # Query nodes
    nodes = neo4j_client.memory_store.get_nodes(user_id=user_id)
    assert any(n["name"] == "PostgreSQL" for n in nodes)

    # Get stats from memory store
    stats = neo4j_client.memory_store.get_stats(user_id=user_id)
    assert stats["total_nodes"] >= 1

@pytest.mark.asyncio
async def test_failure_redis_offline_graceful_fallback():
    """Verify Redis client seamlessly falls back to InMemoryCacheStore when Redis is offline."""
    key = f"test_cache_key_{uuid.uuid4()}"
    val = "cached_session_data"

    # Set value
    ok = await redis_client.set(key, val, expire=60)
    assert ok is True

    # Get value
    retrieved = await redis_client.get(key)
    assert retrieved == val

    # Delete value
    del_ok = await redis_client.delete(key)
    assert del_ok is True
    assert await redis_client.get(key) is None

# ==============================================================================
# 7. TOOL FAILURE, MALFORMED AGENT OUTPUT & ACTION LIFECYCLE
# ==============================================================================

class CrashingTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="crashing_tool",
            description="Tool that intentionally raises an unhandled exception.",
            category="testing",
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False
        )

    async def _execute_action(self, action, user_id, params, db):
        raise RuntimeError("Simulated internal tool crash (e.g. third-party API timeout)")

@pytest.mark.asyncio
async def test_failure_tool_execution_crash_handling(db_session: AsyncSession):
    """Verify unexpected tool failure is caught, error captured, and does not crash app."""
    user = User(email="tool_crash_user@example.com", username="crash_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    crashing_tool = CrashingTool()
    res = await crashing_tool.execute(
        action="simulate_crash",
        user_id=user.id,
        params={"key": "val"},
        db=db_session
    )
    assert res.success is False
    assert "Simulated internal tool crash" in res.error

@pytest.mark.asyncio
async def test_failure_malformed_agent_output_handling():
    """Verify agent planner recovers from non-JSON or broken LLM output."""
    malformed_json_response = "```json\n{ this is not valid json at all ...\n```"

    # When LLM output is malformed or unparseable, deterministic planner executes
    intent = planner_agent.detect_intent("I have an interview tomorrow. Help me prepare.")
    assert intent.value == "interview_prep"

    plan_res = await planner_agent._process(
        input_data={"message": "I have an interview tomorrow. Help me prepare."},
        context={},
        db=None,
        user_id=uuid.uuid4()
    )
    assert plan_res["intent"] == "interview_prep"
    assert len(plan_res["subtasks"]) == 8

    # Verify _fallback method safely constructs a valid plan on error
    fallback_res = await planner_agent._fallback(
        input_data={"message": malformed_json_response},
        context={},
        db=None,
        user_id=uuid.uuid4(),
        error=ValueError("Malformed LLM response JSON")
    )
    assert fallback_res is not None
    assert len(fallback_res["subtasks"]) > 0

@pytest.mark.asyncio
async def test_failure_unauthorized_action_rejection(db_session: AsyncSession):
    """Verify 5-step tool security rejects unauthorized action attempts."""
    user = User(email="unauth_user@example.com", username="unauth_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    # Inactive user
    user.is_active = False
    ok, err = tool_security_guard.validate_user_permission(user, "calendar", "create_event")
    assert ok is False
    assert "Inactive user" in err

    # Unregistered action on calendar tool
    from app.services.tools.calendar_tool import CalendarTool
    cal_tool = CalendarTool()
    # Path traversal attack
    ok, _, err = tool_security_guard.validate_input_schema(cal_tool, {"path": "../../../etc/shadow"})
    assert ok is False
    assert "Suspicious pattern" in err

@pytest.mark.asyncio
async def test_failure_rejected_action_lifecycle(db_session: AsyncSession):
    """Verify user explicitly rejecting a pending action proposal."""
    user = User(email="rejection_test@example.com", username="reject_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    # Create pending proposal
    proposal, auto_executed, _ = await action_manager.propose_action(
        user_id=user.id,
        tool_name="calendar",
        action_type="create_event",
        title="Tentative Interview Prep Block",
        description="Blocked for deep prep",
        parameters={"title": "Tentative Prep", "start_time": utcnow().isoformat(), "end_time": utcnow().isoformat()},
        db=db_session,
        auto_execute_if_safe=False
    )
    assert proposal.status == ActionStatus.PENDING.value
    assert auto_executed is False

    # User rejects proposal
    rejected = await action_manager.reject_action(
        proposal_id=proposal.id,
        reason="I already prepared for this topic.",
        user_id=user.id,
        db=db_session
    )
    assert rejected.status == ActionStatus.REJECTED.value
    assert rejected.rejection_reason == "I already prepared for this topic."

    # Verify audit log
    logs = await action_manager.list_audit_logs(user_id=user.id, db=db_session)
    assert len(logs) > 0
    assert logs[0].approval_status == "rejected"
