import pytest

@pytest.mark.asyncio
async def test_user_data_isolation(client, user_a_headers, user_b_headers):
    # User A creates a project, task, and goal
    proj_a = (await client.post("/projects", json={"name": "Project A Private"}, headers=user_a_headers)).json()
    task_a = (await client.post("/tasks", json={"title": "Task A Secret", "project_id": proj_a["id"]}, headers=user_a_headers)).json()
    goal_a = (await client.post("/goals", json={"title": "Goal A Personal"}, headers=user_a_headers)).json()

    # 1. User B lists projects - must NOT see User A's project
    b_projects = (await client.get("/projects", headers=user_b_headers)).json()
    assert len(b_projects) == 0
    assert not any(p["id"] == proj_a["id"] for p in b_projects)

    # 2. User B lists tasks - must NOT see User A's task
    b_tasks = (await client.get("/tasks", headers=user_b_headers)).json()
    assert len(b_tasks) == 0
    assert not any(t["id"] == task_a["id"] for t in b_tasks)

    # 3. User B lists goals - must NOT see User A's goal
    b_goals = (await client.get("/goals", headers=user_b_headers)).json()
    assert len(b_goals) == 0
    assert not any(g["id"] == goal_a["id"] for g in b_goals)

    # 4. User B attempts direct GET on User A's resources -> 404
    assert (await client.get(f"/projects/{proj_a['id']}", headers=user_b_headers)).status_code == 404
    assert (await client.get(f"/tasks/{task_a['id']}", headers=user_b_headers)).status_code == 404
    assert (await client.get(f"/goals/{goal_a['id']}", headers=user_b_headers)).status_code == 404

    # 5. User B attempts PATCH on User A's resources -> 404
    assert (await client.patch(f"/projects/{proj_a['id']}", json={"name": "Hacked"}, headers=user_b_headers)).status_code == 404
    assert (await client.patch(f"/tasks/{task_a['id']}", json={"title": "Hacked"}, headers=user_b_headers)).status_code == 404
    assert (await client.patch(f"/goals/{goal_a['id']}", json={"title": "Hacked"}, headers=user_b_headers)).status_code == 404

    # 6. User B attempts DELETE on User A's resources -> 404
    assert (await client.delete(f"/projects/{proj_a['id']}", headers=user_b_headers)).status_code == 404
    assert (await client.delete(f"/tasks/{task_a['id']}", headers=user_b_headers)).status_code == 404
    assert (await client.delete(f"/goals/{goal_a['id']}", headers=user_b_headers)).status_code == 404

    # 7. User B tries to link their task to User A's project -> 400 Bad Request
    malicious_task_resp = await client.post(
        "/tasks",
        json={"title": "Unauthorized Task Attachment", "project_id": proj_a["id"]},
        headers=user_b_headers
    )
    assert malicious_task_resp.status_code == 400
    assert "Invalid project_id" in malicious_task_resp.json()["detail"]

    # 8. User A's resources remain untouched and intact
    res_proj_a = await client.get(f"/projects/{proj_a['id']}", headers=user_a_headers)
    assert res_proj_a.status_code == 200
    assert res_proj_a.json()["name"] == "Project A Private"
