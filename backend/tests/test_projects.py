import pytest

@pytest.mark.asyncio
async def test_projects_crud(client, user_a_headers):
    # 1. Create project
    create_payload = {
        "name": "NEXUS Core Engine",
        "description": "Building the core AI orchestrator",
        "status": "active"
    }
    res_create = await client.post("/projects", json=create_payload, headers=user_a_headers)
    assert res_create.status_code == 201
    project = res_create.json()
    project_id = project["id"]
    assert project["name"] == "NEXUS Core Engine"
    assert project["status"] == "active"

    # 2. List projects
    res_list = await client.get("/projects", headers=user_a_headers)
    assert res_list.status_code == 200
    projects = res_list.json()
    assert len(projects) == 1
    assert projects[0]["id"] == project_id

    # 3. Get single project
    res_get = await client.get(f"/projects/{project_id}", headers=user_a_headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == project_id

    # 4. Patch project
    patch_payload = {
        "description": "Updated project description",
        "status": "completed"
    }
    res_patch = await client.patch(f"/projects/{project_id}", json=patch_payload, headers=user_a_headers)
    assert res_patch.status_code == 200
    updated_project = res_patch.json()
    assert updated_project["description"] == "Updated project description"
    assert updated_project["status"] == "completed"

    # 5. Delete project
    res_del = await client.delete(f"/projects/{project_id}", headers=user_a_headers)
    assert res_del.status_code == 204

    # 6. Verify deleted
    res_verify = await client.get(f"/projects/{project_id}", headers=user_a_headers)
    assert res_verify.status_code == 404
