import uuid
import pytest
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.calendar import CalendarEvent
from app.models.document import Document, DocumentChunk
from app.models.project import Project
from app.models.task import Task
from app.models.memory import Memory, MemoryType
from app.models.action import ActionProposal, AuditLog
from app.schemas.tool import ActionStatus
from app.schemas.agent import (
    OrchestrationRequest,
    OrchestrationResult,
    AgentType,
    AgentStatus
)
from app.services.workflows.interview_prep import interview_prep_workflow, InterviewPrepWorkflow

def utcnow():
    return datetime.now(timezone.utc)

@pytest.mark.asyncio
async def test_flagship_workflow_16_steps_end_to_end(db_session: AsyncSession):
    """
    Test the complete 16-step flagship interview preparation workflow end-to-end.
    User says: "I have an interview tomorrow. Help me prepare."
    """
    # 1. Setup User
    user = User(
        email="flagship_test_user@example.com",
        username="flagship_candidate",
        hashed_password="pw"
    )
    db_session.add(user)
    await db_session.flush()

    tomorrow_dt = utcnow() + timedelta(days=1)
    interview_start = tomorrow_dt.replace(hour=10, minute=0, second=0, microsecond=0)
    interview_end = interview_start + timedelta(hours=1)

    # 2. Seed Calendar Event (Step 2 & 3)
    interview_event = CalendarEvent(
        user_id=user.id,
        title="Stripe - Senior AI Systems Engineer Interview",
        description="Technical screening with engineering lead covering architecture, hybrid RAG, and query optimization.",
        start_time=interview_start,
        end_time=interview_end,
        event_type="interview"
    )
    db_session.add(interview_event)

    # 3. Seed Job Description in Knowledge Vault (Step 4 & 5)
    jd_doc = Document(
        user_id=user.id,
        filename="Stripe_Senior_AI_Systems_Engineer_JD.pdf",
        document_type="pdf",
        status="processed"
    )
    db_session.add(jd_doc)
    await db_session.flush()

    jd_chunk = DocumentChunk(
        document_id=jd_doc.id,
        user_id=user.id,
        chunk_index=0,
        content=(
            "Role: Senior AI Systems Engineer at Stripe. "
            "Requirements: Python 3.11, FastAPI, SQL query optimization, distributed system design, "
            "Graph databases (Neo4j), and hybrid RAG retrieval pipelines. "
            "Responsibilities: Architect low-latency backend services, optimize database schemas, "
            "lead architectural reviews, and maintain 99.99% system availability."
        )
    )
    db_session.add(jd_chunk)

    # 4. Seed Resume & Projects (Step 6)
    resume_doc = Document(
        user_id=user.id,
        filename="Candidate_Resume_Senior_Engineer.pdf",
        document_type="pdf",
        status="processed"
    )
    db_session.add(resume_doc)
    await db_session.flush()

    resume_chunk = DocumentChunk(
        document_id=resume_doc.id,
        user_id=user.id,
        chunk_index=0,
        content=(
            "Experienced Backend & AI Engineer specializing in Python, FastAPI, Neo4j knowledge graphs, "
            "asynchronous concurrency, and PostgreSQL. Built high-scale hybrid RAG platforms."
        )
    )
    db_session.add(resume_chunk)

    user_proj = Project(
        user_id=user.id,
        name="Nexus AI Agentic Platform",
        description="Multi-agent asynchronous system with Neo4j graph retrieval and FastAPI services.",
        status="active"
    )
    db_session.add(user_proj)
    await db_session.commit()

    # 5. Track UI activity messages emitted during workflow
    activities_emitted = []
    async def track_ui_activity(msg: str, agent_type: AgentType, status: AgentStatus):
        activities_emitted.append(msg)

    # 6. Execute Flagship Workflow
    req = OrchestrationRequest(
        message="I have an interview tomorrow. Help me prepare."
    )

    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        on_activity=track_ui_activity
    )

    # --- VERIFY STEP 1: Detect ---
    assert isinstance(result, OrchestrationResult)
    # Check that detection data is present
    assert "Tomorrow" in result.final_response
    assert "High" in result.final_response
    assert "Interview Preparation" in result.final_response

    # --- VERIFY STEP 2 & 3: Find interview, company, role ---
    assert "Stripe" in result.final_response
    assert "Senior AI Systems Engineer" in result.final_response or "Senior" in result.final_response

    # --- VERIFY STEP 4 & 5: Extracted requirements ---
    assert "Required Competencies" in result.final_response or "Job Requirements" in result.final_response
    assert "Python" in result.final_response
    assert "FastAPI" in result.final_response

    # --- VERIFY STEP 6 & 7: Skill comparison ---
    assert "Skill Comparison" in result.final_response
    assert "Nexus AI" in result.final_response

    # --- VERIFY STEP 8: Strong, weak, missing areas ---
    assert "Strong Areas" in result.final_response
    assert "Weak Areas" in result.final_response or "Target Weak Areas" in result.final_response
    assert "Missing" in result.final_response

    # --- VERIFY STEP 9: Likely interview topics ---
    assert "Anticipated Interview Topics" in result.final_response
    assert "System Design" in result.final_response
    assert "SQL" in result.final_response

    # --- VERIFY STEP 10: Personalized plan with exact time blocks ---
    assert "6:00–7:00 PM" in result.final_response
    assert "7:15–8:15 PM" in result.final_response
    assert "8:30–9:00 PM" in result.final_response
    assert "9:00–9:30 PM" in result.final_response

    # --- VERIFY STEP 11: Persistent database tasks created ---
    assert len(result.created_tasks) == 4
    tasks_query = select(Task).where(Task.user_id == user.id)
    t_res = await db_session.execute(tasks_query)
    stored_tasks = t_res.scalars().all()
    assert len(stored_tasks) == 4
    task_titles = [t.title for t in stored_tasks]
    assert any("SQL" in t for t in task_titles)
    assert any("System Design" in t for t in task_titles)
    assert any("STAR" in t for t in task_titles)
    assert any("Mock Interview" in t for t in task_titles)

    # --- VERIFY STEP 12 & 13: Free slots & Action proposal awaiting approval ---
    prop_query = select(ActionProposal).where(ActionProposal.user_id == user.id)
    p_res = await db_session.execute(prop_query)
    proposals = p_res.scalars().all()
    assert len(proposals) >= 1
    calendar_proposal = proposals[0]
    assert calendar_proposal.tool_name == "calendar"
    assert calendar_proposal.action_type == "create_event"
    assert calendar_proposal.requires_confirmation is True
    assert calendar_proposal.status == ActionStatus.PENDING.value
    assert "Interview Preparation" in calendar_proposal.title

    # --- VERIFY STEP 14: User approval executes event creation ---
    approved_prop, exec_result = await interview_prep_workflow.create_approved_event(
        proposal_id=calendar_proposal.id,
        user_id=user.id,
        db=db_session
    )
    assert approved_prop.status == ActionStatus.EXECUTED.value
    # Verify event was written to CalendarEvent table
    evt_query = select(CalendarEvent).where(
        CalendarEvent.user_id == user.id,
        CalendarEvent.event_type == "prep"
    )
    e_res = await db_session.execute(evt_query)
    created_events = e_res.scalars().all()
    assert len(created_events) >= 1
    assert "Interview Preparation" in created_events[0].title

    # Verify audit log was recorded
    audit_query = select(AuditLog).where(AuditLog.proposal_id == calendar_proposal.id)
    a_res = await db_session.execute(audit_query)
    audit = a_res.scalar_one_or_none()
    assert audit is not None
    assert audit.status == "success"

    # --- VERIFY STEP 15: Meaningful memory stored ---
    mem_query = select(Memory).where(
        Memory.user_id == user.id,
        Memory.memory_type == MemoryType.EPISODIC.value
    )
    m_res = await db_session.execute(mem_query)
    stored_mems = m_res.scalars().all()
    assert len(stored_mems) >= 1
    prep_mem = stored_mems[0]
    assert "Stripe" in prep_mem.content
    assert "interview" in prep_mem.content.lower()
    assert prep_mem.importance >= 0.8

    # --- VERIFY STEP 16: Summary output ---
    assert len(result.final_response) > 500

    # --- VERIFY UI ACTIVITY MESSAGES SEQUENCE ---
    expected_ui_sequence = [
        "Understanding request...",
        "Finding interview...",
        "Reading job description...",
        "Analyzing your skills...",
        "Checking relevant projects...",
        "Identifying skill gaps...",
        "Creating preparation plan...",
        "Waiting for calendar approval...",
        "Completed."
    ]
    assert activities_emitted == expected_ui_sequence

@pytest.mark.asyncio
async def test_failure_case_no_interview_found(db_session: AsyncSession):
    """Failure Case 1: No interview event found in calendar."""
    user = User(email="no_interview@example.com", username="no_int_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"no_interview_found": True}
    )

    assert result is not None
    assert "No scheduled interview was found in your calendar" in result.final_response
    assert len(result.created_tasks) == 4

@pytest.mark.asyncio
async def test_failure_case_job_description_missing(db_session: AsyncSession):
    """Failure Case 2: Job description document is missing in Knowledge Vault."""
    user = User(email="no_jd@example.com", username="no_jd_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"job_description_missing": True}
    )

    assert result is not None
    assert "Job description not explicitly found" in result.final_response
    assert "Required Competencies" in result.final_response
    assert len(result.created_tasks) == 4

@pytest.mark.asyncio
async def test_failure_case_resume_missing(db_session: AsyncSession):
    """Failure Case 3: Resume document is missing in Knowledge Vault."""
    user = User(email="no_resume@example.com", username="no_res_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"resume_missing": True}
    )

    assert result is not None
    assert "Resume document not detected" in result.final_response
    assert "Skill Comparison" in result.final_response

@pytest.mark.asyncio
async def test_failure_case_calendar_unavailable(db_session: AsyncSession):
    """Failure Case 4: Calendar tool or integration is unavailable/offline."""
    user = User(email="cal_unavail@example.com", username="cal_unavail_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"calendar_unavailable": True}
    )

    assert result is not None
    assert "Calendar synchronization temporarily unavailable" in result.final_response
    assert "6:00–7:00 PM" in result.final_response

@pytest.mark.asyncio
async def test_failure_case_llm_failure(db_session: AsyncSession):
    """Failure Case 5: LLM generation error or outage handled via deterministic fallback."""
    user = User(email="llm_fail@example.com", username="llm_fail_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"llm_failure": True}
    )

    assert result is not None
    assert "Strategic Interview Readiness Plan" in result.final_response
    assert "6:00–7:00 PM" in result.final_response

@pytest.mark.asyncio
async def test_failure_case_retrieval_failure(db_session: AsyncSession):
    """Failure Case 6: Vector search / RAG retrieval failure gracefully caught."""
    user = User(email="retrieval_fail@example.com", username="retrieval_fail_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"retrieval_failure": True}
    )

    assert result is not None
    assert "Required Competencies" in result.final_response
    assert len(result.created_tasks) == 4

@pytest.mark.asyncio
async def test_failure_case_tool_failure(db_session: AsyncSession):
    """Failure Case 7: Tool action failure (e.g. database constraint or tool timeout) gracefully handled."""
    user = User(email="tool_fail@example.com", username="tool_fail_user", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()

    req = OrchestrationRequest(message="I have an interview tomorrow. Help me prepare.")
    result = await interview_prep_workflow.execute(
        request=req,
        user_id=user.id,
        db=db_session,
        simulate_failures={"tool_failure": True}
    )

    # Workflow must not crash; returns full plan with graceful indication
    assert result is not None
    assert "Strategic Interview Readiness Plan" in result.final_response
    assert "6:00–7:00 PM" in result.final_response

@pytest.mark.asyncio
async def test_api_workflows_interview_prep_and_calendar_approval(client, user_a_headers):
    """
    Test REST API endpoints:
    1. POST /workflows/interview-prep executes the 16 steps and returns OrchestrationResult
    2. POST /workflows/interview-prep/approve-calendar/{id} executes Step 14 approval
    """
    # 1. Trigger workflow via API
    resp = await client.post(
        "/workflows/interview-prep",
        json={"message": "I have an interview tomorrow. Help me prepare."},
        headers=user_a_headers
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "interview_prep"
    assert "Strategic Interview Readiness Plan" in data["final_response"]
    assert len(data["created_tasks"]) == 4

    prop_id = data["execution_summary"]["action_proposal_id"]
    assert prop_id is not None

    # 2. Approve the staged calendar action via Step 14 API
    approve_resp = await client.post(
        f"/workflows/interview-prep/approve-calendar/{prop_id}",
        headers=user_a_headers
    )
    assert approve_resp.status_code == 200
    appr_data = approve_resp.json()
    assert appr_data["status"] == "executed"

@pytest.mark.asyncio
async def test_chat_query_interview_prep_workflow(client, user_a_headers):
    """Test Chat endpoint /chat/query seamlessly executes the flagship workflow."""
    resp = await client.post(
        "/chat/query",
        json={"message": "I have an interview tomorrow. Help me prepare."},
        headers=user_a_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Strategic Interview Readiness Plan" in data["answer"]
    assert "6:00–7:00 PM" in data["answer"]
    assert "conversation_id" in data

@pytest.mark.asyncio
async def test_chat_stream_interview_prep_workflow_ui_activities(client, user_a_headers):
    """Test Chat SSE endpoint /chat/stream streams the exact 9 UI activity status sequence."""
    resp = await client.post(
        "/chat/stream",
        json={"message": "I have an interview tomorrow. Help me prepare."},
        headers=user_a_headers
    )
    assert resp.status_code == 200
    body = resp.text
    
    # Verify the exact 9 UI activity status messages were streamed over SSE
    assert "Understanding request..." in body
    assert "Finding interview..." in body
    assert "Reading job description..." in body
    assert "Analyzing your skills..." in body
    assert "Checking relevant projects..." in body
    assert "Identifying skill gaps..." in body
    assert "Creating preparation plan..." in body
    assert "Waiting for calendar approval..." in body
    assert "Completed." in body
    
    # Reconstruct token content from SSE stream
    import json
    tokens = [
        json.loads(line.replace("data: ", ""))["content"]
        for line in body.split("\n\n")
        if line.startswith("data: ") and '"type": "token"' in line
    ]
    reconstructed_text = "".join(tokens)
    assert "Strategic Interview Readiness Plan" in reconstructed_text
    assert "6:00–7:00 PM" in reconstructed_text
