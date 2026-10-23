import pytest

@pytest.mark.asyncio
async def test_register_success(client):
    payload = {
        "email": "test@example.com",
        "username": "tester",
        "password": "strongpassword123"
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["username"] == "tester"
    assert data["user"]["profile"] is not None

@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "dupe@example.com",
        "username": "user1",
        "password": "password123"
    }
    resp1 = await client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    payload2 = {
        "email": "dupe@example.com",
        "username": "user2",
        "password": "password456"
    }
    resp2 = await client.post("/auth/register", json=payload2)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(client):
    reg_payload = {
        "email": "loginuser@example.com",
        "username": "loginuser",
        "password": "secretpassword"
    }
    await client.post("/auth/register", json=reg_payload)

    login_payload = {
        "email": "loginuser@example.com",
        "password": "secretpassword"
    }
    response = await client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "loginuser@example.com"

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    reg_payload = {
        "email": "wrongpass@example.com",
        "username": "wrongpass",
        "password": "correctpassword"
    }
    await client.post("/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpass@example.com",
        "password": "wrongpassword"
    }
    response = await client.post("/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_protected_route_without_token(client):
    response = await client.get("/users/me")
    assert response.status_code == 401
