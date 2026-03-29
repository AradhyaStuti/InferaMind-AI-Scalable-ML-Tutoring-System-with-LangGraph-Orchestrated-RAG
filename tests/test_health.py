"""Test health and general endpoints."""

from tests.conftest import requires_embeddings


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["embedding_model"] == "bge-m3"
    assert data["llm_model"] == "llama3.2"


@requires_embeddings
def test_health_chunks_loaded(client):
    res = client.get("/api/health")
    data = res.json()
    assert data["chunks_loaded"] > 0


@requires_embeddings
def test_frontend_served(client):
    res = client.get("/")
    assert res.status_code == 200


def test_chat_requires_auth(client):
    res = client.post("/api/chat", json={"message": "hello"})
    assert res.status_code == 401


def test_chat_rejects_empty(client, auth_headers):
    res = client.post("/api/chat", json={"message": " "}, headers=auth_headers)
    # min_length=1 after strip check or pydantic validation
    assert res.status_code in (400, 422)
