"""Edge case and security tests."""

import os


def test_expired_token(client):
    """Expired/invalid tokens should return 401."""
    headers = {"Authorization": "Bearer invalid-token-here"}
    res = client.get("/api/conversations", headers=headers)
    assert res.status_code == 401


def test_malformed_auth_header(client):
    """Missing Bearer prefix should return 401."""
    headers = {"Authorization": "just-a-token"}
    res = client.get("/api/conversations", headers=headers)
    assert res.status_code in (401, 403)


def test_register_special_characters_username(client):
    """Usernames with special chars should be rejected."""
    res = client.post("/api/auth/register", json={
        "username": "user@name!",
        "password": "password123",
    })
    assert res.status_code == 422


def test_register_max_length_username(client):
    """Username at max length should work."""
    res = client.post("/api/auth/register", json={
        "username": "a" * 30,
        "password": "password123",
    })
    assert res.status_code == 200


def test_register_over_max_username(client):
    """Username over max length should fail."""
    res = client.post("/api/auth/register", json={
        "username": "a" * 31,
        "password": "password123",
    })
    assert res.status_code == 422


def test_rename_empty_title(client, auth_headers):
    """Empty title should be rejected."""
    conv = client.post("/api/conversations", headers=auth_headers).json()
    res = client.patch(
        f"/api/conversations/{conv['id']}",
        json={"title": ""},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_delete_nonexistent_conversation(client, auth_headers):
    res = client.delete("/api/conversations/fake-id-123", headers=auth_headers)
    assert res.status_code == 404


def test_chat_whitespace_message(client, auth_headers):
    """Whitespace-only messages should be rejected."""
    res = client.post("/api/chat", json={"message": "   "}, headers=auth_headers)
    assert res.status_code in (400, 422)


def test_health_no_auth_required(client):
    """Health endpoint should not require authentication."""
    res = client.get("/api/health")
    assert res.status_code == 200


def test_conversations_list_after_delete(client, auth_headers):
    """Deleted conversations should not appear in list."""
    conv = client.post("/api/conversations", headers=auth_headers).json()
    client.delete(f"/api/conversations/{conv['id']}", headers=auth_headers)
    convs = client.get("/api/conversations", headers=auth_headers).json()
    ids = [c["id"] for c in convs]
    assert conv["id"] not in ids


def test_messages_cascade_delete(client, auth_headers):
    """Deleting a conversation should delete its messages."""
    # Create conversation with a message via chat
    import json
    res = client.post(
        "/api/chat",
        json={"message": "Test cascade"},
        headers=auth_headers,
    )
    events = []
    for line in res.text.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass

    conv_id = next(e["conversation_id"] for e in events if "conversation_id" in e)

    # Verify messages exist
    msgs = client.get(f"/api/conversations/{conv_id}/messages", headers=auth_headers).json()
    assert len(msgs) >= 2

    # Delete and verify
    client.delete(f"/api/conversations/{conv_id}", headers=auth_headers)
    res = client.get(f"/api/conversations/{conv_id}/messages", headers=auth_headers)
    assert res.status_code == 404
