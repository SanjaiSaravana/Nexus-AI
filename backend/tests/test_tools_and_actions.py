import pytest
from datetime import datetime, timedelta, timezone
from app.services.tools import tool_registry, ActionManager
from app.services.tools.calendar_tool import CalendarTool
from app.services.tools.task_tool import TaskTool
from app.services.tools.email_tool import EmailTool
from app.services.tools.github_tool import GitHubTool
from app.models.action import sanitize_parameters, ActionProposal, AuditLog
from app.models.calendar import CalendarEvent
from sqlalchemy import select


@pytest.mark.asyncio
async def test_tool_registry_contains_all_required_domains():
    """Verify that all 9 domains requested in Phase 6 are properly registered with complete schemas."""
    expected_tools = [
        "task",
        "calendar",
        "documents",
        "memory",
        "projects",
        "knowledge_graph",
        "search",
        "email",
        "github",
    ]
    all_tools = tool_registry.list_tools()
    registered_names = {t.name for t in all_tools}

    for name in expected_tools:
        assert name in registered_names, f"Tool '{name}' is not registered in ToolRegistry"

    # Verify schema definition completeness
    for tool_def in all_tools:
        assert tool_def.name
        assert tool_def.description
        assert tool_def.category
        assert tool_def.risk_level in ["read_only", "low", "medium", "high", "critical"]
        assert isinstance(tool_def.requires_confirmation, bool)
        assert isinstance(tool_def.permissions, list)
        assert isinstance(tool_def.input_schema, dict)
        assert isinstance(tool_def.output_schema, dict)


@pytest.mark.asyncio
async def test_action_proposal_and_permission_checks(client, user_a_headers):
    """Test proposing an action, verifying that high-risk actions require user confirmation."""
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    tomorrow_end = tomorrow + timedelta(hours=1)

    # Propose calendar event creation (requires confirmation)
    proposal_data = {
        "tool_name": "calendar",
        "action_type": "create_event",
        "title": "Interview Preparation",
        "description": "Tomorrow 6:00 PM – 7:00 PM",
        "parameters": {
            "title": "Interview Preparation",
            "start_time": tomorrow.isoformat(),
            "end_time": tomorrow_end.isoformat(),
            "event_type": "prep",
            "location": "Virtual Office"
        }
    }

    resp = await client.post("/actions/propose", json=proposal_data, headers=user_a_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["tool_name"] == "calendar"
    assert data["title"] == "Interview Preparation"
    assert data["requires_confirmation"] is True
    assert data["status"] == "pending"
    proposal_id = data["id"]

    # Verify listed in pending proposals
    list_resp = await client.get("/actions/proposals?status=pending", headers=user_a_headers)
    assert list_resp.status_code == 200
    proposals = list_resp.json()
    assert any(p["id"] == proposal_id for p in proposals)


@pytest.mark.asyncio
async def test_action_approval_and_execution_lifecycle(client, user_a_headers, db_session):
    """Test full cycle: propose action -> approve -> tool execution -> audit log created."""
    now = datetime.now(timezone.utc)
    t_start = now + timedelta(days=2)
    t_end = t_start + timedelta(hours=1)

    proposal_data = {
        "tool_name": "calendar",
        "action_type": "create_event",
        "title": "Mock Technical Interview",
        "description": "Technical Screening Round",
        "parameters": {
            "title": "Mock Technical Interview",
            "start_time": t_start.isoformat(),
            "end_time": t_end.isoformat(),
            "event_type": "interview",
            "location": "Google Meet"
        }
    }

    create_resp = await client.post("/actions/propose", json=proposal_data, headers=user_a_headers)
    assert create_resp.status_code == 201
    proposal_id = create_resp.json()["id"]

    # Approve proposal
    approve_resp = await client.post(f"/actions/proposals/{proposal_id}/approve", json={"note": "Approved by user"}, headers=user_a_headers)
    assert approve_resp.status_code == 200, approve_resp.text
    result_data = approve_resp.json()
    assert result_data["status"] == "executed"
    assert result_data["result"] is not None
    assert result_data["result"]["success"] is True

    # Verify event exists in calendar
    events_resp = await client.get("/calendar/events", headers=user_a_headers)
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert any(e["title"] == "Mock Technical Interview" for e in events)

    # Verify audit log recorded execution
    audit_resp = await client.get("/actions/audit-logs", headers=user_a_headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    matching_log = next((l for l in audit_logs if l.get("proposal_id") == proposal_id), None)
    assert matching_log is not None
    assert matching_log["approval_status"] == "approved"
    assert matching_log["status"] == "success"
    assert matching_log["action"] == "create_event"


@pytest.mark.asyncio
async def test_action_rejection_flow(client, user_a_headers):
    """Test proposing an action and rejecting it without execution."""
    proposal_data = {
        "tool_name": "email",
        "action_type": "send_email",
        "title": "Send Cold Email to Recruiter",
        "description": "Sending outreach email",
        "parameters": {
            "to_address": "recruiter@bigtech.com",
            "subject": "Inquiry regarding Senior AI Engineer role",
            "body": "Hello, I am interested in joining your team..."
        }
    }

    resp = await client.post("/actions/propose", json=proposal_data, headers=user_a_headers)
    assert resp.status_code == 201
    proposal_id = resp.json()["id"]

    # Reject proposal
    reject_resp = await client.post(
        f"/actions/proposals/{proposal_id}/reject",
        json={"reason": "Need to polish resume first"},
        headers=user_a_headers
    )
    assert reject_resp.status_code == 200
    rejected = reject_resp.json()
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "Need to polish resume first"

    # Verify audit log records rejection
    audit_resp = await client.get("/actions/audit-logs", headers=user_a_headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    matching_log = next((l for l in audit_logs if l.get("proposal_id") == proposal_id), None)
    assert matching_log is not None
    assert matching_log["approval_status"] == "rejected"
    assert matching_log["status"] == "rejected"


@pytest.mark.asyncio
async def test_tool_validation_and_failed_execution(client, user_a_headers):
    """Test tool parameter validation and error handling on malformed tool calls."""
    # Propose calendar event with invalid end_time before start_time
    now = datetime.now(timezone.utc)
    bad_proposal = {
        "tool_name": "calendar",
        "action_type": "create_event",
        "title": "Invalid Event Dates",
        "parameters": {
            "title": "Invalid Event",
            "start_time": (now + timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat()  # end before start
        }
    }

    resp = await client.post("/actions/propose", json=bad_proposal, headers=user_a_headers)
    assert resp.status_code == 201
    prop_id = resp.json()["id"]

    # Attempt to approve and execute -> should catch validation error gracefully
    approve_resp = await client.post(f"/actions/proposals/{prop_id}/approve", headers=user_a_headers)
    # The proposal status should reflect failed execution
    assert approve_resp.status_code == 200
    prop = approve_resp.json()
    assert prop["status"] == "failed"
    assert "start_time must be before end_time" in prop["error_message"].lower()

    # Check audit log recorded the failure
    audit_resp = await client.get("/actions/audit-logs", headers=user_a_headers)
    matching_log = next((l for l in audit_resp.json() if l.get("proposal_id") == prop_id), None)
    assert matching_log is not None
    assert matching_log["status"] == "failed"
    assert "start_time" in matching_log["error_message"].lower()


@pytest.mark.asyncio
async def test_audit_log_secret_sanitization():
    """Verify that credentials, tokens, passwords, and API keys are redacted before storing in audit logs."""
    raw_params = {
        "username": "candidate_alex",
        "password": "SuperSecretPassword123!",
        "api_key": "sk-proj-xyz12398459438593485",
        "access_token": "bearer_jwt_token_here",
        "nested_config": {
            "db_secret": "my-database-password",
            "auth_header": "Bearer secret_header_value",
            "normal_value": 42
        }
    }

    sanitized = sanitize_parameters(raw_params)
    assert sanitized["username"] == "candidate_alex"
    assert sanitized["password"] == "******"
    assert sanitized["api_key"] == "******"
    assert sanitized["access_token"] == "******"
    assert sanitized["nested_config"]["db_secret"] == "******"
    assert sanitized["nested_config"]["auth_header"] == "******"
    assert sanitized["nested_config"]["normal_value"] == 42


@pytest.mark.asyncio
async def test_calendar_tool_crud_and_free_slots(db_session):
    """Test all calendar abstraction methods: get_events, get_free_slots, create_event, update_event, delete_event."""
    user_id = "test-user-calendar"
    cal_tool = CalendarTool(db_session=db_session, user_id=user_id)

    base_time = datetime(2026, 10, 15, 9, 0, 0, tzinfo=timezone.utc)

    # 1. create_event
    res1 = await cal_tool.execute({
        "action": "create_event",
        "title": "Morning Standup",
        "start_time": base_time.isoformat(),
        "end_time": (base_time + timedelta(minutes=30)).isoformat(),
        "event_type": "meeting"
    })
    assert res1.success is True
    event1_id = res1.data["event"]["id"]

    # Create second event in afternoon
    afternoon_start = base_time + timedelta(hours=4)
    res2 = await cal_tool.execute({
        "action": "create_event",
        "title": "Interview Prep",
        "start_time": afternoon_start.isoformat(),
        "end_time": (afternoon_start + timedelta(hours=1)).isoformat(),
        "event_type": "prep"
    })
    assert res2.success is True
    event2_id = res2.data["event"]["id"]

    # 2. get_events
    events_res = await cal_tool.execute({
        "action": "get_events",
        "start_time": (base_time - timedelta(days=1)).isoformat(),
        "end_time": (base_time + timedelta(days=2)).isoformat()
    })
    assert events_res.success is True
    assert len(events_res.data["events"]) == 2

    # 3. get_free_slots
    slots_res = await cal_tool.execute({
        "action": "get_free_slots",
        "start_time": base_time.isoformat(),
        "end_time": (base_time + timedelta(hours=8)).isoformat(),
        "duration_minutes": 60
    })
    assert slots_res.success is True
    free_slots = slots_res.data["free_slots"]
    assert len(free_slots) > 0

    # 4. update_event
    update_res = await cal_tool.execute({
        "action": "update_event",
        "event_id": event1_id,
        "title": "Morning Sync & Strategy",
        "location": "Boardroom A"
    })
    assert update_res.success is True
    assert update_res.data["event"]["title"] == "Morning Sync & Strategy"
    assert update_res.data["event"]["location"] == "Boardroom A"

    # 5. delete_event
    del_res = await cal_tool.execute({
        "action": "delete_event",
        "event_id": event2_id
    })
    assert del_res.success is True
    assert del_res.data["deleted"] is True

    # Verify only 1 event remains
    events_after = await cal_tool.execute({
        "action": "get_events",
        "start_time": (base_time - timedelta(days=1)).isoformat(),
        "end_time": (base_time + timedelta(days=2)).isoformat()
    })
    assert len(events_after.data["events"]) == 1


@pytest.mark.asyncio
async def test_task_tool_crud(db_session):
    """Test task tool abstraction: create_task, update_task, complete_task, delete_task."""
    user_id = "test-user-task"
    task_tool = TaskTool(db_session=db_session, user_id=user_id)

    # 1. create_task
    create_res = await task_tool.execute({
        "action": "create_task",
        "title": "Review Distributed Systems Architecture",
        "description": "Study consensus algorithms and CAP theorem",
        "priority": "high"
    })
    assert create_res.success is True
    task_id = create_res.data["task"]["id"]
    assert create_res.data["task"]["priority"] == "high"

    # 2. update_task
    update_res = await task_tool.execute({
        "action": "update_task",
        "task_id": task_id,
        "title": "Review Raft and Paxos Consensus",
        "priority": "critical"
    })
    assert update_res.success is True
    assert update_res.data["task"]["title"] == "Review Raft and Paxos Consensus"
    assert update_res.data["task"]["priority"] == "critical"

    # 3. complete_task
    comp_res = await task_tool.execute({
        "action": "complete_task",
        "task_id": task_id
    })
    assert comp_res.success is True
    assert comp_res.data["task"]["status"] == "completed"

    # 4. delete_task
    del_res = await task_tool.execute({
        "action": "delete_task",
        "task_id": task_id
    })
    assert del_res.success is True
    assert del_res.data["deleted"] is True


@pytest.mark.asyncio
async def test_email_and_github_mock_tools(db_session):
    """Test EmailTool and GitHubTool local/mock implementations without requiring external OAuth credentials."""
    user_id = "test-mock-user"

    # Email tool
    email_tool = EmailTool(db_session=db_session, user_id=user_id)
    send_res = await email_tool.execute({
        "action": "send_email",
        "to_address": "hiring@innovate.ai",
        "subject": "Follow up on Interview Prep",
        "body": "Thank you for the informative discussion."
    })
    assert send_res.success is True
    assert send_res.data["status"] == "sent"
    assert send_res.data["provider"] == "mock_local_smtp"

    # Check inbox/outbox listing
    inbox_res = await email_tool.execute({"action": "list_inbox"})
    assert inbox_res.success is True
    assert len(inbox_res.data["messages"]) >= 1

    # GitHub tool
    gh_tool = GitHubTool(db_session=db_session, user_id=user_id)
    issue_res = await gh_tool.execute({
        "action": "create_issue",
        "repo": "owner/nexus-ai",
        "title": "Implement automated evaluation suite for multi-agent reasoning",
        "body": "Track end-to-end benchmark scores and latency.",
        "labels": ["enhancement", "phase-6"]
    })
    assert issue_res.success is True
    assert issue_res.data["issue_number"] is not None
    assert issue_res.data["provider"] == "mock_local_github"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_for_actions_and_calendar(client, user_a_headers, user_b_headers):
    """Verify that User B cannot view or approve User A's action proposals or calendar events."""
    now = datetime.now(timezone.utc)
    t_start = now + timedelta(days=3)
    t_end = t_start + timedelta(hours=1)

    # User A creates proposal
    prop_data = {
        "tool_name": "calendar",
        "action_type": "create_event",
        "title": "Confidential Strategy Session",
        "parameters": {
            "title": "Confidential Strategy Session",
            "start_time": t_start.isoformat(),
            "end_time": t_end.isoformat()
        }
    }
    resp = await client.post("/actions/propose", json=prop_data, headers=user_a_headers)
    assert resp.status_code == 201
    prop_a_id = resp.json()["id"]

    # User B lists proposals -> should NOT see User A's proposal
    b_list = await client.get("/actions/proposals", headers=user_b_headers)
    assert b_list.status_code == 200
    b_proposals = b_list.json()
    assert not any(p["id"] == prop_a_id for p in b_proposals)

    # User B attempts to approve User A's proposal -> should return 404
    b_approve = await client.post(f"/actions/proposals/{prop_a_id}/approve", headers=user_b_headers)
    assert b_approve.status_code == 404
