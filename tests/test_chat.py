"""Test chat endpoint — streaming, validation, auth."""

import json
from tests.conftest import requires_embeddings


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


@requires_embeddings
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


@requires_embeddings
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


@requires_embeddings
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


def test_chat_rejects_empty_message(client, auth_headers):
    res = client.post("/api/chat", json={"message": ""}, headers=auth_headers)
    assert res.status_code == 422


def test_chat_requires_auth(client):
    res = client.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 401
