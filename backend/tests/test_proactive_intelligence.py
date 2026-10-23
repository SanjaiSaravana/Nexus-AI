import uuid
import pytest
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import select

from app.models.task import Task
from app.models.calendar import CalendarEvent
from app.models.document import Document
from app.models.goal import Goal
from app.models.recommendation import AIRecommendation, ProactivePreferences
from app.services.proactive.priority_engine import priority_engine, PriorityEngine
from app.services.proactive.detector import proactive_detector
from app.services.proactive.service import proactive_service


# =============================================================================
# 1. PRIORITY ENGINE UNIT TESTS
# =============================================================================

def test_priority_engine_weight_sum():
    engine = PriorityEngine()
    total_weights = (
        engine.WEIGHT_URGENCY +
        engine.WEIGHT_DEADLINE +
        engine.WEIGHT_GOAL_RELEVANCE +
        engine.WEIGHT_IMPORTANCE +
        engine.WEIGHT_DEPENDENCIES +
        engine.WEIGHT_ESTIMATED_EFFORT
    )
    assert abs(total_weights - 1.0) < 1e-6


def test_priority_engine_custom_factors_normalization():
    engine = PriorityEngine()
    # Test maximum bound
    max_breakdown = engine.calculate_breakdown(
        task={"title": "Max task"},
        custom_factors={
            "urgency": 1.0,
            "deadline": 1.0,
            "goal_relevance": 1.0,
            "importance": 1.0,
            "dependencies": 1.0,
            "estimated_effort": 1.0
        }
    )
    assert max_breakdown["normalized_score"] == 1.0
    assert max_breakdown["priority_level"] == "urgent"

    # Test minimum bound
    min_breakdown = engine.calculate_breakdown(
        task={"title": "Min task"},
        custom_factors={
            "urgency": 0.0,
            "deadline": 0.0,
            "goal_relevance": 0.0,
            "importance": 0.0,
            "dependencies": 0.0,
            "estimated_effort": 0.0
        }
    )
    assert min_breakdown["normalized_score"] == 0.0
    assert min_breakdown["priority_level"] == "low"

    # Test arbitrary factors stay within [0.0, 1.0]
    mid_breakdown = engine.calculate_breakdown(
        task={"title": "Mid task"},
        custom_factors={
            "urgency": 0.5,
            "deadline": 0.8,
            "goal_relevance": 0.6,
            "importance": 0.7,
            "dependencies": 0.4,
            "estimated_effort": 0.9
        }
    )
    assert 0.0 <= mid_breakdown["normalized_score"] <= 1.0
    assert "urgency" in mid_breakdown["factors"]
    assert "deadline" in mid_breakdown["factors"]
    assert "goal_relevance" in mid_breakdown["factors"]
    assert "importance" in mid_breakdown["factors"]
    assert "dependencies" in mid_breakdown["factors"]
    assert "estimated_effort" in mid_breakdown["factors"]


def test_priority_engine_automatic_inference():
    today = date(2026, 10, 15)
    task_urgent = {
        "title": "Interview preparation blocker",
        "description": "Urgent review for tomorrow's technical interview",
        "priority": "urgent",
        "due_date": date(2026, 10, 16)
    }
    score = priority_engine.calculate_priority(task=task_urgent, reference_date=today)
    assert score >= 0.75

    task_low = {
        "title": "Read random blog post",
        "priority": "low",
        "due_date": date(2026, 11, 15)
    }
    low_score = priority_engine.calculate_priority(task=task_low, reference_date=today)
    assert low_score < score


# =============================================================================
# 2. PROACTIVE DETECTION SCENARIOS
# =============================================================================

@pytest.mark.asyncio
async def test_flagship_interview_prep_gap_detection(db_session, user_a_headers, client):
    # Retrieve user ID
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()
    tomorrow_start = (now_utc + timedelta(days=1)).replace(hour=14, minute=0, second=0)

    # 1. Calendar event: Interview tomorrow
    event = CalendarEvent(
        user_id=user_id,
        title="Google Staff Software Engineer Interview",
        description="Onsite virtual interview round",
        event_type="interview",
        start_time=tomorrow_start,
        end_time=tomorrow_start + timedelta(hours=1)
    )
    db_session.add(event)

    # 2. Document: Job description exists in vault
    doc = Document(
        user_id=user_id,
        filename="Google_Staff_Engineer_JD.pdf",
        document_type="pdf",
        file_size=1024,
        status="processed"
    )
    db_session.add(doc)

    # 3. Active Goal
    goal = Goal(
        user_id=user_id,
        title="Land Senior AI Engineering Role",
        category="career",
        status="active"
    )
    db_session.add(goal)
    await db_session.commit()

    # Run proactive detection without any prep task
    recs = await proactive_detector.detect_all(
        user_id=user_id,
        db=db_session,
        reference_date=today
    )

    # Verify Flagship Situation Detected
    prep_recs = [r for r in recs if r["category"] == "preparation_gap"]
    assert len(prep_recs) == 1
    flagship_rec = prep_recs[0]

    # Verify exact user-facing recommendation requirement
    expected_recommendation = (
        "Your interview is tomorrow and you don't currently have an interview preparation task. "
        "I found the job description and relevant projects. Would you like me to create a preparation plan?"
    )
    assert flagship_rec["recommendation"] == expected_recommendation
    assert flagship_rec["action_type"] == "create_preparation_plan"
    assert flagship_rec["priority_score"] >= 0.90
    assert flagship_rec["priority_level"] == "urgent"
    assert flagship_rec["related_deadline"] is not None

    # Now simulate user already has a preparation task
    prep_task = Task(
        user_id=user_id,
        title="Interview Preparation for Google",
        status="todo",
        priority="urgent"
    )
    db_session.add(prep_task)
    await db_session.commit()

    # Re-detect: prep gap should now be resolved!
    recs_after = await proactive_detector.detect_all(
        user_id=user_id,
        db=db_session,
        reference_date=today
    )
    assert not any(r["category"] == "preparation_gap" for r in recs_after)


@pytest.mark.asyncio
async def test_detect_conflicting_events(db_session, user_a_headers, client):
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])
    now_utc = datetime.now(timezone.utc)
    t1 = now_utc + timedelta(hours=3)
    t2 = t1 + timedelta(minutes=45)

    # Event 1: 3:00 to 4:00
    e1 = CalendarEvent(
        user_id=user_id,
        title="Team Sprint Sync",
        start_time=t1,
        end_time=t1 + timedelta(hours=1),
        event_type="meeting"
    )
    # Event 2: 3:45 to 4:45 (15 min overlap)
    e2 = CalendarEvent(
        user_id=user_id,
        title="Client Architecture Review",
        start_time=t2,
        end_time=t2 + timedelta(hours=1),
        event_type="meeting"
    )
    db_session.add_all([e1, e2])
    await db_session.commit()

    recs = await proactive_detector.detect_all(user_id=user_id, db=db_session)
    conflict_recs = [r for r in recs if r["category"] == "conflicting_events"]
    assert len(conflict_recs) >= 1
    assert "overlap" in conflict_recs[0]["recommendation"].lower() or "conflict" in conflict_recs[0]["recommendation"].lower()
    assert conflict_recs[0]["action_type"] == "resolve_calendar_conflict"


@pytest.mark.asyncio
async def test_detect_overdue_and_upcoming_deadlines(db_session, user_a_headers, client):
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])
    today = date(2026, 10, 15)

    # Overdue task
    overdue_task = Task(
        user_id=user_id,
        title="Submit Quarterly Security Audit",
        status="todo",
        priority="high",
        due_date=date(2026, 10, 10) # 5 days overdue
    )
    # Upcoming deadline task
    imminent_task = Task(
        user_id=user_id,
        title="Deploy Phase 8 Proactive Engine",
        status="in_progress",
        priority="urgent",
        due_date=date(2026, 10, 16) # due tomorrow
    )
    db_session.add_all([overdue_task, imminent_task])
    await db_session.commit()

    recs = await proactive_detector.detect_all(user_id=user_id, db=db_session, reference_date=today)
    
    overdue = [r for r in recs if r["category"] == "overdue_task"]
    assert len(overdue) >= 1
    assert "5 day(s) overdue" in overdue[0]["recommendation"]

    imminent = [r for r in recs if r["category"] == "upcoming_deadline"]
    assert len(imminent) >= 1
    assert "due tomorrow" in imminent[0]["recommendation"]


@pytest.mark.asyncio
async def test_detect_inactive_goals_and_unfinished_high_priority(db_session, user_a_headers, client):
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])
    today = date(2026, 10, 15)

    # Inactive goal with 0% progress
    inactive_goal = Goal(
        user_id=user_id,
        title="Learn Rust System Programming",
        category="learning",
        progress_pct=0,
        status="active"
    )
    # Blocked high priority task
    blocked_task = Task(
        user_id=user_id,
        title="Provision Production Redis Cluster",
        status="blocked",
        priority="urgent"
    )
    db_session.add_all([inactive_goal, blocked_task])
    await db_session.commit()

    recs = await proactive_detector.detect_all(user_id=user_id, db=db_session, reference_date=today)

    goal_recs = [r for r in recs if r["category"] == "inactive_goal"]
    assert len(goal_recs) >= 1
    assert "0% progress" in goal_recs[0]["recommendation"]
    assert goal_recs[0]["action_type"] == "generate_goal_milestones"

    high_pri = [r for r in recs if r["category"] == "unfinished_high_priority"]
    assert len(high_pri) >= 1
    assert "URGENT" in high_pri[0]["recommendation"]
    assert high_pri[0]["action_type"] == "decompose_task"


# =============================================================================
# 3. SAFETY, PREFERENCES & ANTI-SPAM CONTROLS
# =============================================================================

@pytest.mark.asyncio
async def test_proactive_service_disable_suggestions(db_session, user_a_headers, client):
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])

    # Disable proactive suggestions
    await proactive_service.update_preferences(
        user_id=user_id,
        updates={"enabled": False},
        db=db_session
    )

    # Create an overdue task that would normally trigger
    task = Task(
        user_id=user_id,
        title="Overdue Report",
        status="todo",
        due_date=date(2026, 1, 1)
    )
    db_session.add(task)
    await db_session.commit()

    # Attempt generation - should return empty list because disabled
    recs = await proactive_service.generate_recommendations(user_id=user_id, db=db_session)
    assert len(recs) == 0


@pytest.mark.asyncio
async def test_proactive_service_max_daily_limit_and_dismissal(db_session, user_a_headers, client):
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])

    # Set cap to 1 recommendation
    await proactive_service.update_preferences(
        user_id=user_id,
        updates={"enabled": True, "max_daily_recommendations": 1},
        db=db_session
    )

    # Create two overdue tasks
    t1 = Task(user_id=user_id, title="Task Alpha", status="todo", due_date=date(2026, 1, 1))
    t2 = Task(user_id=user_id, title="Task Beta", status="todo", due_date=date(2026, 1, 2))
    db_session.add_all([t1, t2])
    await db_session.commit()

    recs = await proactive_service.generate_recommendations(user_id=user_id, db=db_session)
    # Strictly limited to 1 recommendation
    assert len(recs) == 1
    rec_to_dismiss = recs[0]

    # Dismiss the recommendation
    dismissed = await proactive_service.dismiss_recommendation(
        recommendation_id=rec_to_dismiss.id,
        user_id=user_id,
        db=db_session
    )
    assert dismissed.status == "dismissed"
    assert dismissed.dismissed_at is not None

    # Check active recommendations: dismissed item should not be present
    active = await proactive_service.get_active_recommendations(user_id=user_id, db=db_session)
    assert len(active) == 0

    # Regenerating within 24h should NOT bring back the dismissed title
    recs_second = await proactive_service.generate_recommendations(user_id=user_id, db=db_session)
    for r in recs_second:
        assert r.title != rec_to_dismiss.title


@pytest.mark.asyncio
async def test_proactive_service_muted_categories(db_session, user_a_headers, client):
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])

    # Mute overdue_task category
    await proactive_service.update_preferences(
        user_id=user_id,
        updates={"muted_categories": ["overdue_task"]},
        db=db_session
    )

    task = Task(user_id=user_id, title="Overdue Bug Fix", status="todo", due_date=date(2026, 1, 1))
    db_session.add(task)
    await db_session.commit()

    recs = await proactive_service.generate_recommendations(user_id=user_id, db=db_session)
    assert not any(r.category == "overdue_task" for r in recs)


# =============================================================================
# 4. REST API ENDPOINTS & DASHBOARD INTEGRATION
# =============================================================================

@pytest.mark.asyncio
async def test_recommendations_api_lifecycle(client, user_a_headers, db_session):
    # 1. GET preferences default
    pref_res = await client.get("/recommendations/preferences", headers=user_a_headers)
    assert pref_res.status_code == 200
    pref_data = pref_res.json()
    assert pref_data["enabled"] is True
    assert pref_data["frequency"] in ["daily", "hourly", "immediate"]

    # 2. PUT preferences
    update_res = await client.put(
        "/recommendations/preferences",
        json={"frequency": "hourly", "max_daily_recommendations": 7},
        headers=user_a_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["frequency"] == "hourly"
    assert update_res.json()["max_daily_recommendations"] == 7

    # 3. Create overdue task directly via DB to trigger a recommendation
    user_resp = await client.get("/users/me", headers=user_a_headers)
    user_id = uuid.UUID(user_resp.json()["id"])
    t = Task(user_id=user_id, title="Refactor Auth Module", status="todo", due_date=date(2026, 1, 1), priority="high")
    db_session.add(t)
    await db_session.commit()

    # 4. POST /recommendations/generate
    gen_res = await client.post("/recommendations/generate", headers=user_a_headers)
    assert gen_res.status_code == 200
    recs = gen_res.json()
    assert len(recs) >= 1
    target_rec = recs[0]
    rec_id = target_rec["id"]
    assert "priority_score" in target_rec
    assert "reason" in target_rec

    # 5. GET /recommendations returns active
    list_res = await client.get("/recommendations", headers=user_a_headers)
    assert list_res.status_code == 200
    assert any(r["id"] == rec_id for r in list_res.json())

    # 6. GET /dashboard/overview includes ai_recommendations
    dash_res = await client.get("/dashboard/overview", headers=user_a_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "ai_recommendations" in dash_data
    assert len(dash_data["ai_recommendations"]) >= 1

    # 7. POST /recommendations/{id}/act
    act_res = await client.post(f"/recommendations/{rec_id}/act", headers=user_a_headers)
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "success"

    # 8. Check that executed recommendation status transitioned and is no longer active
    active_after = await client.get("/recommendations", headers=user_a_headers)
    # The acted upon recommendation should not be in active recommendations
    assert not any(r["id"] == rec_id for r in active_after.json())
