"""Application configuration with validation."""

import os
import secrets
import logging

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env file from project root (won't override existing env vars)
load_dotenv(os.path.join(BASE_DIR, ".env"))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─── LLM Provider ────────────────────────────────────────────
# "groq" = Groq cloud (fast, needs GROQ_API_KEY)
# "ollama" = local Ollama (no API key, needs Ollama running)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# Ollama settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

# Groq settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

# Resolved LLM model name based on provider
LLM_MODEL = GROQ_LLM_MODEL if LLM_PROVIDER == "groq" else OLLAMA_LLM_MODEL

EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.joblib")
DB_PATH = os.path.join(DATA_DIR, "conversations.db")

TOP_K = 5
EMBED_TIMEOUT = 120
LLM_TIMEOUT = 300
MAX_MESSAGE_LENGTH = 2000
MAX_TITLE_LENGTH = 200

# ─── 3-way classification thresholds ─────────────────────────
# >= COURSE_THRESHOLD  → course_related (RAG from videos)
# >= GENERAL_THRESHOLD → course_related_general (LLM answers from own knowledge)
# < GENERAL_THRESHOLD  → off_topic (rejected)
COURSE_THRESHOLD = float(os.getenv("COURSE_THRESHOLD", "0.35"))
GENERAL_THRESHOLD = float(os.getenv("GENERAL_THRESHOLD", "0.20"))

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
