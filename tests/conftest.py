"""Shared test fixtures."""

import os
import pytest
from fastapi.testclient import TestClient

os.environ["OLLAMA_URL"] = "http://localhost:11434"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "test-secret-key-for-ci"

from backend.main import app, startup
from backend.config import EMBEDDINGS_PATH
from backend.db.store import init_db, get_conn
from backend.auth.security import init_auth_db


def _has_embeddings() -> bool:
    return os.path.isfile(EMBEDDINGS_PATH)


def _ollama_reachable() -> bool:
    try:
        import requests
        r = requests.get(os.environ["OLLAMA_URL"], timeout=2)
        return r.status_code == 200
    except Exception:
        return False


_embeddings_available = _has_embeddings()
_ollama_available = _ollama_reachable() if _embeddings_available else False


@pytest.fixture(scope="session", autouse=True)
def setup_app():
    if _embeddings_available and _ollama_available:
        startup()
    else:
        # CI / no-Ollama path: skip embedding load.
        init_db()
        init_auth_db()
    yield
    with get_conn() as conn:
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM conversations")
        conn.execute("DELETE FROM users")


requires_embeddings = pytest.mark.skipif(
    not (_embeddings_available and _ollama_available),
    reason="Requires embeddings.joblib + running Ollama",
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    username = f"testuser_{os.urandom(4).hex()}"
    res = client.post("/api/auth/register", json={
        "username": username,
        "password": "testpass123",
    })
    assert res.status_code == 200, f"Registration failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
