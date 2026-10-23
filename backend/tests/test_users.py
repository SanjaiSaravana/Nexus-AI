import pytest

@pytest.mark.asyncio
async def test_get_current_user(client, user_a_headers):
    response = await client.get("/users/me", headers=user_a_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user_a@example.com"
    assert data["username"] == "user_a"
    assert data["profile"] is not None

@pytest.mark.asyncio
async def test_update_profile(client, user_a_headers):
    payload = {
        "full_name": "Alice User",
        "bio": "AI Systems Engineer",
        "preferences": {"theme": "dark", "timezone": "UTC"}
    }
    response = await client.patch("/users/me/profile", json=payload, headers=user_a_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Alice User"
    assert data["bio"] == "AI Systems Engineer"
    assert data["preferences"]["theme"] == "dark"
