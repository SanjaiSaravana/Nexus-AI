import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.goal import Goal
from app.models.memory import Memory, MemoryType
from app.models.document import Document, DocumentChunk
from app.schemas.agent import (
    AgentType,
    AgentStatus,
    UserIntent,
    PlannerOutput,
    ResearchEvidence,
    MemoryRecallOutput,
    ProjectAnalysisOutput,
    TaskPlanOutput,
    CalendarAgentOutput,
    ExecutionAgentOutput,
    OrchestrationRequest,
    OrchestrationResult
)
from app.services.agents.base import BaseAgent
from app.services.agents.planner import planner_agent
from app.services.agents.research import research_agent
from app.services.agents.memory_agent import memory_agent
from app.services.agents.project_agent import project_agent
from app.services.agents.task_agent import task_agent
from app.services.agents.calendar_agent import calendar_agent
from app.services.agents.execution_agent import execution_agent
from app.services.agents.orchestrator import orchestrator

@pytest.mark.asyncio
async def test_planner_agent_interview_prep(db_session: AsyncSession):
    """Test Planner Agent converts high-level interview prep request into 8 structured subtasks."""
    user_id = uuid.uuid4()
    query = "I have an interview tomorrow. Prepare me."

    run_id = uuid.uuid4()
    state = await planner_agent.run(
        run_id=run_id,
        input_data={"message": query},
        context={},
        db=db_session,
        user_id=user_id
    )

    assert state.status == AgentStatus.COMPLETED
    assert state.output is not None

    plan = PlannerOutput(**state.output)
    assert plan.intent == UserIntent.INTERVIEW_PREP
    assert len(plan.subtasks) == 8

    # Verify the 8 structured subtask titles from specifications
    expected_steps = [
        "Find interview details",
        "Find job description",
        "Extract requirements",
        "Analyze user skills",
        "Find relevant projects",
        "Identify gaps",
        "Generate topics",
        "Generate preparation plan"
    ]
    for idx, expected_title in enumerate(expected_steps, start=1):
        step_item = next((st for st in plan.subtasks if st.step == idx), None)
        assert step_item is not None
        assert step_item.title == expected_title
        assert step_item.assigned_agent in [
            AgentType.CALENDAR, AgentType.RESEARCH, AgentType.MEMORY,
            AgentType.PROJECT, AgentType.TASK, AgentType.EXECUTION
        ]

@pytest.mark.asyncio
async def test_routing_and_tool_selection():
    """Test Intent Detection and dynamic Agent tool selection."""
    # 1. Interview Prep
    intent_interview = planner_agent.detect_intent("I have an interview tomorrow with Google")
    assert intent_interview == UserIntent.INTERVIEW_PREP

    # 2. Project Planning
    intent_project = planner_agent.detect_intent("Build a distributed system architecture and project roadmap")
    assert intent_project == UserIntent.PROJECT_PLANNING

    # 3. Task Generation
    intent_task = planner_agent.detect_intent("Create a todo checklist of action items for release")
    assert intent_task == UserIntent.TASK_GENERATION

    # 4. Research Query
    intent_research = planner_agent.detect_intent("Search knowledge documents for API security")
    assert intent_research == UserIntent.RESEARCH_QUERY

@pytest.mark.asyncio
async def test_memory_agent_selective_relevance(db_session: AsyncSession):
    """Verify Memory Agent does NOT retrieve all memories; applies strict semantic and importance filtering."""
    # Register a test user
    user = User(email="memory_agent_test@example.com", username="mem_test", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    # Seed 1 highly relevant memory + 5 irrelevant memories
    relevant_mem = Memory(
        user_id=user.id,
        memory_type=MemoryType.SEMANTIC,
        content="Candidate has 5 years senior backend experience building FastAPI, Python microservices, and Neo4j graph databases.",
        importance=0.9,
        source="conversation"
    )
    db_session.add(relevant_mem)

    irrelevant_contents = [
        "Prefers drinking oat milk lattes in the morning",
        "Bought groceries at the local supermarket on Tuesday",
        "Watched an indie movie on Netflix last weekend",
        "Favorite color is navy blue",
        "Walks the dog every evening in the local park"
    ]
    for c in irrelevant_contents:
        irr_mem = Memory(
            user_id=user.id,
            memory_type=MemoryType.EPISODIC,
            content=c,
            importance=0.2,
            source="conversation"
        )
        db_session.add(irr_mem)

    await db_session.commit()

    run_id = uuid.uuid4()
    state = await memory_agent.run(
        run_id=run_id,
        input_data={"query": "Python FastAPI backend technical interview preparation"},
        context={},
        db=db_session,
        user_id=user.id
    )

    assert state.status == AgentStatus.COMPLETED
    output = MemoryRecallOutput(**state.output)

    # CRITICAL: Must not retrieve all memories!
    assert output.total_evaluated == 6
    assert output.retrieved_count < output.total_evaluated
    assert output.retrieved_count >= 1

    # Relevant memory was retrieved
    contents = [m.content for m in output.memories]
    assert any("FastAPI" in c for c in contents)
    assert not any("oat milk" in c for c in contents)

@pytest.mark.asyncio
async def test_research_agent_structured_evidence(db_session: AsyncSession):
    """Test Research Agent returns structured facts from documents, graph, and external sources."""
    user = User(email="research_agent_test@example.com", username="res_test", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    # Add a document and chunk
    doc = Document(user_id=user.id, filename="resume.pdf", file_size=1024, document_type="pdf")
    db_session.add(doc)
    await db_session.flush()

    chunk = DocumentChunk(
        document_id=doc.id,
        user_id=user.id,
        chunk_index=0,
        content="Lead Architect on Nexus AI platform: engineered distributed indexing and Neo4j Knowledge Graph RAG with sub-100ms latency.",
        embedding=[0.05] * 384
    )
    db_session.add(chunk)
    await db_session.commit()

    run_id = uuid.uuid4()
    state = await research_agent.run(
        run_id=run_id,
        input_data={"query": "What architectural systems and RAG pipelines has the candidate built?"},
        context={},
        db=db_session,
        user_id=user.id
    )

    assert state.status == AgentStatus.COMPLETED
    evidence = ResearchEvidence(**state.output)

    assert len(evidence.facts) > 0
    assert any(f.source_type == "external" for f in evidence.facts)
    assert any("Nexus AI" in f.fact or "STAR" in f.fact for f in evidence.facts)

@pytest.mark.asyncio
async def test_project_and_task_agent_outputs(db_session: AsyncSession):
    """Test Project Agent matches user projects to skills and Task Agent converts plan into actionable tasks."""
    user = User(email="proj_task_test@example.com", username="proj_test", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    proj = Project(
        user_id=user.id,
        name="Nexus AI Assistant",
        description="Production personal intelligence system using Python, FastAPI, Neo4j, React, and RAG.",
        status="active"
    )
    db_session.add(proj)

    goal = Goal(
        user_id=user.id,
        title="Master Distributed Systems and Graph Architectures",
        category="career"
    )
    db_session.add(goal)
    await db_session.commit()

    # 1. Project Agent Run
    run_id = uuid.uuid4()
    proj_state = await project_agent.run(
        run_id=run_id,
        input_data={"message": "Interview tomorrow on backend Python and graph databases"},
        context={},
        db=db_session,
        user_id=user.id
    )
    assert proj_state.status == AgentStatus.COMPLETED
    proj_output = ProjectAnalysisOutput(**proj_state.output)
    assert len(proj_output.matched_projects) >= 1
    assert any("Nexus AI" in p.project_name for p in proj_output.matched_projects)
    assert len(proj_output.recommended_focus) > 0

    # 2. Task Agent Run
    task_state = await task_agent.run(
        run_id=run_id,
        input_data={"message": "I have an interview tomorrow"},
        context={"plan": {"intent": UserIntent.INTERVIEW_PREP}, "project": proj_state.output},
        db=db_session,
        user_id=user.id
    )
    assert task_state.status == AgentStatus.COMPLETED
    task_output = TaskPlanOutput(**task_state.output)
    assert len(task_output.tasks) >= 3
    assert any(t.priority in ["urgent", "high"] for t in task_output.tasks)
    assert any("STAR Story" in t.title for t in task_output.tasks)

@pytest.mark.asyncio
async def test_calendar_and_execution_agent_actions(db_session: AsyncSession):
    """Test Calendar Agent schedule proposals and Execution Agent database task persistence."""
    user = User(email="exec_agent_test@example.com", username="exec_test", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    run_id = uuid.uuid4()
    # Calendar Agent
    cal_state = await calendar_agent.run(
        run_id=run_id,
        input_data={"message": "I have an interview tomorrow at 3pm"},
        context={},
        db=db_session,
        user_id=user.id
    )
    assert cal_state.status == AgentStatus.COMPLETED
    cal_output = CalendarAgentOutput(**cal_state.output)
    assert len(cal_output.events) >= 2
    assert any(e.event_type == "interview" for e in cal_output.events)

    # Execution Agent - auto execute tasks to DB
    staged_tasks = [
        {"title": "Prepare STAR Narratives", "description": "Review Nexus AI architecture", "priority": "urgent", "due_date_offset_days": 0},
        {"title": "System Design Mock Session", "description": "Practice distributed caching", "priority": "high", "due_date_offset_days": 1}
    ]
    exec_state = await execution_agent.run(
        run_id=run_id,
        input_data={"auto_execute_tasks": True},
        context={"task": {"tasks": staged_tasks}},
        db=db_session,
        user_id=user.id
    )
    assert exec_state.status == AgentStatus.COMPLETED
    exec_output = ExecutionAgentOutput(**exec_state.output)
    assert exec_output.success is True
    assert len(exec_output.actions) == 2

    # Verify tasks actually exist in the database
    db_tasks_stmt = select(Task).where(Task.user_id == user.id)
    res = await db_session.execute(db_tasks_stmt)
    created_tasks = res.scalars().all()
    assert len(created_tasks) == 2
    assert any(t.title == "Prepare STAR Narratives" for t in created_tasks)

@pytest.mark.asyncio
async def test_agent_failure_retry_and_graceful_fallback(db_session: AsyncSession):
    """Test failure resilience: Agent retries on exception, falls back gracefully, and does NOT crash orchestrator."""
    class FailingTestAgent(BaseAgent):
        def __init__(self):
            super().__init__(
                agent_type=AgentType.RESEARCH,
                name="Failing Agent",
                description="Simulates upstream network crash",
                activity_message="Simulating...",
                max_retries=2
            )
            self.attempt_counter = 0

        async def _process(self, input_data, context, db, user_id):
            self.attempt_counter += 1
            raise ConnectionResetError("Remote model service disconnected")

        async def _fallback(self, input_data, context, db, user_id, error):
            return {"fallback_used": True, "recovered": "Safe default structured output"}

    failing_agent = FailingTestAgent()
    run_id = uuid.uuid4()
    user_id = uuid.uuid4()

    state = await failing_agent.run(
        run_id=run_id,
        input_data={"query": "test"},
        context={},
        db=db_session,
        user_id=user_id
    )

    # Verified retries executed
    assert failing_agent.attempt_counter == 3  # Initial + 2 retries
    assert state.retries == 3
    # Verified fallback was used and did not crash
    assert state.status == AgentStatus.COMPLETED
    assert state.output == {"fallback_used": True, "recovered": "Safe default structured output"}
    assert "ConnectionResetError" in (state.errors or "")

@pytest.mark.asyncio
async def test_complete_interview_prep_orchestration(db_session: AsyncSession):
    """Complete End-to-End Orchestration Test for the 'I have an interview tomorrow. Prepare me.' request."""
    user = User(email="orch_prep_test@example.com", username="orch_user", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    # Seed Project
    proj = Project(
        user_id=user.id,
        name="Nexus AI Platform",
        description="Advanced Agentic AI platform with Neo4j Knowledge Graph and RAG.",
        status="active"
    )
    db_session.add(proj)
    await db_session.commit()

    activities_logged = []
    async def track_activity(act_msg: str, agent_type: AgentType, status: AgentStatus):
        activities_logged.append((act_msg, agent_type))

    req = OrchestrationRequest(
        message="I have an interview tomorrow. Prepare me.",
        auto_execute_tasks=False
    )

    result = await orchestrator.orchestrate(
        request=req,
        user_id=user.id,
        db=db_session,
        on_activity=track_activity
    )

    assert isinstance(result, OrchestrationResult)
    assert result.intent == UserIntent.INTERVIEW_PREP
    assert len(result.plan.subtasks) == 8

    # Verify agent state tracking
    executed_agent_types = [st.agent for st in result.agent_states]
    assert AgentType.PLANNER in executed_agent_types
    assert AgentType.RESEARCH in executed_agent_types
    assert AgentType.MEMORY in executed_agent_types
    assert AgentType.PROJECT in executed_agent_types
    assert AgentType.CALENDAR in executed_agent_types
    assert AgentType.TASK in executed_agent_types

    for state in result.agent_states:
        assert state.run_id == result.run_id
        assert state.start_time is not None
        assert state.end_time is not None
        assert state.status == AgentStatus.COMPLETED

    # Verify safe high-level UI activity descriptions were dispatched
    assert any("Planning..." in act[0] for act in activities_logged)
    assert any("Retrieving information..." in act[0] for act in activities_logged)
    assert any("Analyzing projects..." in act[0] for act in activities_logged)
    assert any("Checking memory..." in act[0] for act in activities_logged)
    assert any("Creating plan..." in act[0] for act in activities_logged)

    # Verify Final Response Content
    assert "Strategic Interview Readiness Plan" in result.final_response
    assert "STAR Narrative" in result.final_response
    assert "Nexus AI" in result.final_response
    assert len(result.created_tasks) > 0
    assert len(result.suggested_calendar_events) > 0

@pytest.mark.asyncio
async def test_multi_agent_api_endpoints(client, user_a_headers):
    """Test REST API endpoints for agent orchestration, definitions, and run inspection."""
    # 1. Definitions endpoint
    def_resp = await client.get("/agents/definitions", headers=user_a_headers)
    assert def_resp.status_code == 200
    defs = def_resp.json()
    assert defs["count"] == 7
    agent_names = [a["name"] for a in defs["agents"]]
    assert "Planner Agent" in agent_names
    assert "Research Agent" in agent_names
    assert "Memory Agent" in agent_names
    assert "Project Agent" in agent_names
    assert "Task Agent" in agent_names
    assert "Calendar Agent" in agent_names
    assert "Execution Agent" in agent_names

    # 2. Orchestration execution endpoint
    orch_payload = {
        "message": "I have an interview tomorrow. Prepare me.",
        "auto_execute_tasks": False
    }
    orch_resp = await client.post("/agents/orchestrate", json=orch_payload, headers=user_a_headers)
    assert orch_resp.status_code == 200
    res_data = orch_resp.json()
    assert res_data["intent"] == "interview_prep"
    run_id = res_data["run_id"]
    assert len(res_data["agent_states"]) >= 6

    # 3. Run audit endpoint
    run_resp = await client.get(f"/agents/runs/{run_id}", headers=user_a_headers)
    assert run_resp.status_code == 200
    audit_data = run_resp.json()
    assert audit_data["run_id"] == run_id
    assert audit_data["intent"] == "interview_prep"

    # 4. Chat query endpoint auto-routing to orchestrator
    chat_resp = await client.post(
        "/chat/query",
        json={"message": "I have an interview tomorrow. Prepare me."},
        headers=user_a_headers
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "Strategic Interview Readiness Plan" in chat_data["answer"]
