"""
Production Integration & End-to-End Test Suite for NEXUS AI:
Tests the complete multi-tier execution chain:
Frontend/Client
  → REST API
  → Database (SQLAlchemy & Neo4j)
  → AI (Intent, Grounding & Anti-Hallucination)
  → Retrieval (Vector Dense + BM25 Sparse Hybrid RAG)
  → Multi-Agent Orchestrator (Planner, Research, Memory, Project, Task, Execution)
  → Secure Tools (5-Step Guard, Calendar, Task, Action Confirmation, Audit Log)
"""

import io
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

def utcnow():
    return datetime.now(timezone.utc)

@pytest.mark.asyncio
async def test_full_production_chain_integration(client: AsyncClient):
    """
    Test the complete production chain from User Registration to Tool Execution:
    Frontend/Client -> API -> Database -> AI -> Retrieval -> Agents -> Tools -> Audit Log
    """
    # --------------------------------------------------------------------------
    # Tier 1: User Registration & Authentication (API -> DB -> JWT)
    # --------------------------------------------------------------------------
    reg_payload = {
        "email": "integration_candidate@example.com",
        "username": "candidate_pro",
        "password": "ProductionPassword123!"
    }
    reg_resp = await client.post("/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    reg_data = reg_resp.json()
    user_id = reg_data["user"]["id"]
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify session via protected endpoint
    me_resp = await client.get("/users/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == reg_payload["email"]

    # --------------------------------------------------------------------------
    # Tier 2: Database Project Creation
    # --------------------------------------------------------------------------
    proj_payload = {
        "name": "NEXUS AI Production Deployment",
        "description": "High-availability distributed agentic intelligence platform",
        "status": "active"
    }
    proj_resp = await client.post("/projects", json=proj_payload, headers=headers)
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    # --------------------------------------------------------------------------
    # Tier 3: Document Ingestion Pipeline (API -> Ingestion -> Embeddings -> DB)
    # --------------------------------------------------------------------------
    resume_text = (
        "Candidate Profile: Senior AI Infrastructure Architect\n"
        "Technical Stack: Python 3.11, FastAPI, PostgreSQL, Neo4j, Docker, PyTorch, Hybrid RAG pipelines.\n"
        "Experience: 8 years building distributed backend architectures and agentic workflows.\n"
        "Achievements: Decreased query latency by 45% using hybrid reciprocal rank fusion reranking."
    )
    files = {
        "file": ("architect_resume.txt", io.BytesIO(resume_text.encode("utf-8")), "text/plain")
    }
    upload_resp = await client.post("/documents/upload", files=files, headers=headers)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]
    assert upload_resp.json()["document"]["filename"] == "architect_resume.txt"

    # --------------------------------------------------------------------------
    # Tier 4: AI Grounded Retrieval & Chat (API -> Hybrid RAG -> Anti-Hallucination)
    # --------------------------------------------------------------------------
    chat_resp = await client.post(
        "/chat/query",
        json={"message": "What is the candidate's technical stack and experience?"},
        headers=headers
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "FastAPI" in chat_data["answer"] or "Python" in chat_data["answer"]
    assert len(chat_data["citations"]) > 0

    # --------------------------------------------------------------------------
    # Tier 5: Seed Calendar Interview Event
    # --------------------------------------------------------------------------
    tomorrow_dt = utcnow() + timedelta(days=1)
    interview_start = tomorrow_dt.replace(hour=14, minute=0, second=0, microsecond=0)
    interview_end = interview_start + timedelta(hours=1)

    event_payload = {
        "title": "Anthropic - Lead Systems Architect Interview",
        "description": "Deep-dive technical assessment into distributed RAG, multi-agent orchestration, and Neo4j graph storage.",
        "start_time": interview_start.isoformat(),
        "end_time": interview_end.isoformat(),
        "event_type": "interview"
    }
    cal_resp = await client.post("/calendar/events", json=event_payload, headers=headers)
    assert cal_resp.status_code == 201
    event_id = cal_resp.json()["id"]

    # --------------------------------------------------------------------------
    # Tier 6: Multi-Agent Workflow: "I have an interview tomorrow. Help me prepare."
    # (API -> Orchestrator -> Planner -> Research -> Memory -> Task -> Tool Proposal)
    # --------------------------------------------------------------------------
    wf_resp = await client.post(
        "/workflows/interview-prep",
        json={"message": "I have an interview tomorrow. Help me prepare."},
        headers=headers
    )
    assert wf_resp.status_code == 200
    wf_data = wf_resp.json()
    assert wf_data["intent"] == "interview_prep"
    assert "Strategic Interview Readiness Plan" in wf_data["final_response"]
    assert len(wf_data["created_tasks"]) == 4

    # --------------------------------------------------------------------------
    # Tier 7: Action Security & User Approval Lifecycle
    # (API -> Action Manager -> 5-Step Guard -> User Approval -> Tool Execution -> Audit)
    # --------------------------------------------------------------------------
    prop_id = wf_data["execution_summary"].get("action_proposal_id")
    assert prop_id is not None

    # User approves staged calendar action proposal via API
    approve_resp = await client.post(
        f"/workflows/interview-prep/approve-calendar/{prop_id}",
        headers=headers
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "executed"

    # 2. Check immutable audit logs
    audit_resp = await client.get("/actions/audit-logs", headers=headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert len(audit_logs) > 0
    # Verify no unmasked credentials in audit logs
    for log in audit_logs:
        for k, v in (log.get("parameters") or {}).items():
            if any(s in k.lower() for s in ["password", "secret", "token"]):
                assert v == "******"

    # --------------------------------------------------------------------------
    # Tier 8: Proactive Recommendations & Dashboard Metrics
    # --------------------------------------------------------------------------
    recs_resp = await client.get("/recommendations", headers=headers)
    assert recs_resp.status_code == 200

    dash_resp = await client.get("/dashboard/overview", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    stats = dash_data["stats"]
    assert stats["active_projects_count"] >= 1
    assert stats["total_tasks"] >= len(wf_data["created_tasks"])
