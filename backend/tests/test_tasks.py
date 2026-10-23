import pytest

@pytest.mark.asyncio
async def test_tasks_crud_and_status(client, user_a_headers):
    # 1. Create a project
    proj_resp = await client.post("/projects", json={"name": "Sprint 1"}, headers=user_a_headers)
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Create task associated with project
    task_payload = {
        "title": "Implement JWT Middleware",
        "description": "Secure all routes",
        "project_id": project_id,
        "priority": "high",
        "status": "todo",
        "due_date": "2026-10-15"
    }
    res_create = await client.post("/tasks", json=task_payload, headers=user_a_headers)
    assert res_create.status_code == 201
    task = res_create.json()
    task_id = task["id"]
    assert task["title"] == "Implement JWT Middleware"
    assert task["priority"] == "high"
    assert task["project_id"] == project_id
    assert task["completed_at"] is None

    # 3. List tasks with filter
    res_list = await client.get(f"/tasks?priority_filter=high", headers=user_a_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 4. Patch task to completed (check completed_at is set)
    res_patch = await client.patch(f"/tasks/{task_id}", json={"status": "completed"}, headers=user_a_headers)
    assert res_patch.status_code == 200
    patched_task = res_patch.json()
    assert patched_task["status"] == "completed"
    assert patched_task["completed_at"] is not None

    # 5. Delete task
    res_del = await client.delete(f"/tasks/{task_id}", headers=user_a_headers)
    assert res_del.status_code == 204

    # 6. Verify deleted
    res_check = await client.get(f"/tasks/{task_id}", headers=user_a_headers)
    assert res_check.status_code == 404
