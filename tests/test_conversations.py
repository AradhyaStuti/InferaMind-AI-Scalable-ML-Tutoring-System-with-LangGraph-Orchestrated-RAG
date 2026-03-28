"""Test conversation CRUD endpoints."""


def test_list_empty(client, auth_headers):
    res = client.get("/api/conversations", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_create_conversation(client, auth_headers):
    res = client.post("/api/conversations", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["title"] == "New Chat"


def test_get_conversation(client, auth_headers):
    conv = client.post("/api/conversations", headers=auth_headers).json()
    res = client.get(f"/api/conversations/{conv['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == conv["id"]


def test_get_nonexistent_conversation(client, auth_headers):
    res = client.get("/api/conversations/fake-id", headers=auth_headers)
    assert res.status_code == 404


def test_rename_conversation(client, auth_headers):
    conv = client.post("/api/conversations", headers=auth_headers).json()
    res = client.patch(
        f"/api/conversations/{conv['id']}",
        json={"title": "Renamed Chat"},
        headers=auth_headers,
    )
    assert res.status_code == 200

    updated = client.get(f"/api/conversations/{conv['id']}", headers=auth_headers).json()
    assert updated["title"] == "Renamed Chat"


def test_delete_conversation(client, auth_headers):
    conv = client.post("/api/conversations", headers=auth_headers).json()
    res = client.delete(f"/api/conversations/{conv['id']}", headers=auth_headers)
    assert res.status_code == 200

    res = client.get(f"/api/conversations/{conv['id']}", headers=auth_headers)
    assert res.status_code == 404


def test_unauthorized_access(client):
    res = client.get("/api/conversations")
    assert res.status_code == 401


def test_cross_user_isolation(client):
    """User A cannot see User B's conversations."""
    # Create user A
    user_a = client.post("/api/auth/register", json={
        "username": "user_a_iso",
        "password": "password123",
    }).json()
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}

    # Create user B
    user_b = client.post("/api/auth/register", json={
        "username": "user_b_iso",
        "password": "password123",
    }).json()
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    # A creates a conversation
    conv = client.post("/api/conversations", headers=headers_a).json()

    # B cannot access it
    res = client.get(f"/api/conversations/{conv['id']}", headers=headers_b)
    assert res.status_code == 404

    # B's list doesn't include it
    convs = client.get("/api/conversations", headers=headers_b).json()
    ids = [c["id"] for c in convs]
    assert conv["id"] not in ids
