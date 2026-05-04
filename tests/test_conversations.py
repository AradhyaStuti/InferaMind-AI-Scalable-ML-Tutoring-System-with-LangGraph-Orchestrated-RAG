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


def test_delete_conversation(client, auth_headers):
    conv = client.post("/api/conversations", headers=auth_headers).json()
    res = client.delete(f"/api/conversations/{conv['id']}", headers=auth_headers)
    assert res.status_code == 200
    res = client.get(f"/api/conversations/{conv['id']}", headers=auth_headers)
    assert res.status_code == 404


def test_unauthorized_access(client):
    res = client.get("/api/conversations")
    assert res.status_code == 401
