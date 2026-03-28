"""Application configuration with validation."""

import os
import secrets
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")

EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.joblib")
DB_PATH = os.path.join(DATA_DIR, "conversations.db")

TOP_K = 5
EMBED_TIMEOUT = 120
LLM_TIMEOUT = 300
MAX_MESSAGE_LENGTH = 2000
MAX_TITLE_LENGTH = 200

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# JWT secret — generate a stable one and warn if not set explicitly
_jwt_from_env = os.getenv("JWT_SECRET")
if _jwt_from_env:
    JWT_SECRET = _jwt_from_env
else:
    JWT_SECRET = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET not set — using random secret. "
        "Sessions will not persist across server restarts. "
        "Set JWT_SECRET env var in production."
    )

# Validate critical paths at import time
if not os.path.isdir(DATA_DIR):
    raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")
