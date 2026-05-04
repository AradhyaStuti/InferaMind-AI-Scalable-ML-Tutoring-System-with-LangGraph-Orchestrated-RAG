from backend.config import LLM_MODEL, LLM_PROVIDER


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["embedding_model"] == "bge-m3"
    assert data["llm_model"] == LLM_MODEL
    assert data["llm_provider"] == LLM_PROVIDER
