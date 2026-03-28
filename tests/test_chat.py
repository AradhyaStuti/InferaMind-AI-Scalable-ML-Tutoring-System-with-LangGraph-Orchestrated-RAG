"""Test chat endpoint — streaming, message persistence, edge cases."""

import json


def parse_sse(response_text: str) -> list[dict]:
    """Parse SSE response into list of data objects."""
    events = []
    for line in response_text.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def test_chat_creates_conversation(client, auth_headers):
    """First message should create a new conversation."""
    res = client.post(
        "/api/chat",
        json={"message": "What is supervised learning?"},
        headers=auth_headers,
    )
    assert res.status_code == 200

    events = parse_sse(res.text)
    conv_ids = [e["conversation_id"] for e in events if "conversation_id" in e]
    assert len(conv_ids) >= 1
    assert conv_ids[0]  # non-empty


def test_chat_returns_sse_pipeline(client, auth_headers):
    """Response should include classify, retrieve, generate nodes."""
    res = client.post(
        "/api/chat",
        json={"message": "What is machine learning?"},
        headers=auth_headers,
    )
    events = parse_sse(res.text)

    nodes = [e.get("node") for e in events if "node" in e]
    assert "classify" in nodes
    assert "retrieve" in nodes
    assert "generate" in nodes


def test_chat_returns_sources(client, auth_headers):
    """Course-related queries should return source chunks."""
    res = client.post(
        "/api/chat",
        json={"message": "What is supervised learning?"},
        headers=auth_headers,
    )
    events = parse_sse(res.text)

    source_events = [e for e in events if "sources" in e]
    assert len(source_events) >= 1
    sources = source_events[0]["sources"]
    assert len(sources) > 0
    assert "video" in sources[0]
    assert "text" in sources[0]
    assert "similarity" in sources[0]


def test_chat_returns_tokens(client, auth_headers):
    """Response should stream tokens."""
    res = client.post(
        "/api/chat",
        json={"message": "What is regression?"},
        headers=auth_headers,
    )
    events = parse_sse(res.text)

    tokens = [e["token"] for e in events if "token" in e]
    assert len(tokens) > 0
    full_response = "".join(tokens)
    assert len(full_response) > 10


def test_chat_done_event(client, auth_headers):
    """Stream should end with a done event."""
    res = client.post(
        "/api/chat",
        json={"message": "What is a loss function?"},
        headers=auth_headers,
    )
    events = parse_sse(res.text)
    done_events = [e for e in events if e.get("done")]
    assert len(done_events) == 1


def test_chat_persists_messages(client, auth_headers):
    """Messages should be saved to the conversation."""
    res = client.post(
        "/api/chat",
        json={"message": "What is gradient descent?"},
        headers=auth_headers,
    )
    events = parse_sse(res.text)
    conv_id = next(e["conversation_id"] for e in events if "conversation_id" in e)

    msgs = client.get(f"/api/conversations/{conv_id}/messages", headers=auth_headers).json()
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "What is gradient descent?"
    assert msgs[1]["role"] == "assistant"
    assert len(msgs[1]["content"]) > 0


def test_chat_continues_conversation(client, auth_headers):
    """Sending a second message to same conversation should work."""
    # First message
    res1 = client.post(
        "/api/chat",
        json={"message": "What is ML?"},
        headers=auth_headers,
    )
    events1 = parse_sse(res1.text)
    conv_id = next(e["conversation_id"] for e in events1 if "conversation_id" in e)

    # Second message to same conversation
    res2 = client.post(
        "/api/chat",
        json={"message": "Tell me more", "conversation_id": conv_id},
        headers=auth_headers,
    )
    assert res2.status_code == 200
    events2 = parse_sse(res2.text)
    assert any(e.get("done") for e in events2)

    # Should have 4 messages total (2 user + 2 assistant)
    msgs = client.get(f"/api/conversations/{conv_id}/messages", headers=auth_headers).json()
    assert len(msgs) == 4


def test_chat_rejects_empty_message(client, auth_headers):
    res = client.post("/api/chat", json={"message": ""}, headers=auth_headers)
    assert res.status_code == 422


def test_chat_rejects_long_message(client, auth_headers):
    res = client.post(
        "/api/chat",
        json={"message": "x" * 2001},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_chat_requires_auth(client):
    res = client.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 401


def test_chat_rejects_invalid_conversation(client, auth_headers):
    res = client.post(
        "/api/chat",
        json={"message": "hello", "conversation_id": "nonexistent-id"},
        headers=auth_headers,
    )
    assert res.status_code == 404


def test_chat_cross_user_isolation(client):
    """User A cannot send messages to User B's conversation."""
    # Create user A
    user_a = client.post("/api/auth/register", json={
        "username": f"chat_iso_a_{__import__('os').urandom(4).hex()}",
        "password": "password123",
    }).json()
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}

    # Create user B
    user_b = client.post("/api/auth/register", json={
        "username": f"chat_iso_b_{__import__('os').urandom(4).hex()}",
        "password": "password123",
    }).json()
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    # A creates a conversation
    res = client.post(
        "/api/chat",
        json={"message": "What is ML?"},
        headers=headers_a,
    )
    events = parse_sse(res.text)
    conv_id = next(e["conversation_id"] for e in events if "conversation_id" in e)

    # B tries to access A's conversation
    res = client.post(
        "/api/chat",
        json={"message": "Hack!", "conversation_id": conv_id},
        headers=headers_b,
    )
    assert res.status_code == 404
