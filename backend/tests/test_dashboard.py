from datetime import date, timedelta
import pytest

@pytest.mark.asyncio
async def test_dashboard_overview_metrics(client, user_a_headers):
    today = date.today()

    # Create project
    await client.post("/projects", json={"name": "Alpha Project", "status": "active"}, headers=user_a_headers)
    
    # Create tasks
    await client.post("/tasks", json={"title": "Task 1", "status": "completed", "due_date": str(today)}, headers=user_a_headers)
    await client.post("/tasks", json={"title": "Task 2", "status": "in_progress", "due_date": str(today)}, headers=user_a_headers)
    await client.post("/tasks", json={"title": "Task 3", "status": "todo", "due_date": str(today + timedelta(days=2))}, headers=user_a_headers)

    # Create goal
    await client.post("/goals", json={"title": "Goal 1", "progress_pct": 50, "status": "active"}, headers=user_a_headers)

    response = await client.get("/dashboard/overview", headers=user_a_headers)
    assert response.status_code == 200
    data = response.json()

    stats = data["stats"]
    assert stats["total_tasks"] == 3
    assert stats["completed_tasks"] == 1
    assert stats["pending_tasks"] == 2
    assert stats["in_progress_tasks"] == 1
    assert stats["active_projects_count"] == 1
    assert stats["active_goals_count"] == 1
    assert stats["average_goal_progress"] == 50.0

    assert len(data["todays_tasks"]) >= 1
    assert len(data["upcoming_tasks"]) >= 1
    assert len(data["active_projects"]) == 1
    assert len(data["active_goals"]) == 1
