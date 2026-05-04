"""Edge case and security tests."""


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


def test_chat_whitespace_message(client, auth_headers):
    """Whitespace-only messages should be rejected."""
    res = client.post("/api/chat", json={"message": "   "}, headers=auth_headers)
    assert res.status_code in (400, 422)


def test_health_no_auth_required(client):
    """Health endpoint should not require authentication."""
    res = client.get("/api/health")
    assert res.status_code == 200
