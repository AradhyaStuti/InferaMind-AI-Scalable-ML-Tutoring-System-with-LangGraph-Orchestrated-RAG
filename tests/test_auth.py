"""Test authentication endpoints."""


def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "username": "newuser_test1",
        "password": "password123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["username"] == "newuser_test1"
    assert data["token_type"] == "bearer"


def test_register_duplicate(client):
    client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "password123",
    })
    res = client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "password456",
    })
    assert res.status_code == 409


def test_register_invalid_username(client):
    res = client.post("/api/auth/register", json={
        "username": "ab",  # too short
        "password": "password123",
    })
    assert res.status_code == 422


def test_register_short_password(client):
    res = client.post("/api/auth/register", json={
        "username": "validuser",
        "password": "short",  # too short
    })
    assert res.status_code == 422


def test_login_success(client):
    client.post("/api/auth/register", json={
        "username": "loginuser",
        "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "username": "loginuser",
        "password": "password123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "username": "wrongpwuser",
        "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "username": "wrongpwuser",
        "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = client.post("/api/auth/login", json={
        "username": "nosuchuser",
        "password": "password123",
    })
    assert res.status_code == 401
