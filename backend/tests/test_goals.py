import pytest

@pytest.mark.asyncio
async def test_goals_crud(client, user_a_headers):
    # 1. Create Goal
    create_payload = {
        "title": "Master Agentic AI Architecture",
        "description": "Design and build production multi-agent systems",
        "category": "career",
        "status": "active",
        "progress_pct": 25,
        "target_date": "2026-12-31"
    }
    res_create = await client.post("/goals", json=create_payload, headers=user_a_headers)
    assert res_create.status_code == 201
    goal = res_create.json()
    goal_id = goal["id"]
    assert goal["title"] == "Master Agentic AI Architecture"
    assert goal["progress_pct"] == 25

    # 2. List Goals
    res_list = await client.get("/goals", headers=user_a_headers)
    assert res_list.status_code == 200
    goals = res_list.json()
    assert len(goals) == 1
    assert goals[0]["id"] == goal_id

    # 3. Patch Goal progress
    res_patch = await client.patch(f"/goals/{goal_id}", json={"progress_pct": 80}, headers=user_a_headers)
    assert res_patch.status_code == 200
    assert res_patch.json()["progress_pct"] == 80

    # 4. Delete Goal
    res_del = await client.delete(f"/goals/{goal_id}", headers=user_a_headers)
    assert res_del.status_code == 204

    # 5. Verify deleted
    res_check = await client.get(f"/goals/{goal_id}", headers=user_a_headers)
    assert res_check.status_code == 404
