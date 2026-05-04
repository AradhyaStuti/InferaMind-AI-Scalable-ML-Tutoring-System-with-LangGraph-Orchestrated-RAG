"""Configuration loaded from .env / environment."""

import os
import secrets
import logging

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DATA_DIR = os.path.join(BASE_DIR, "data")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "groq" or "ollama"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

LLM_MODEL = GROQ_LLM_MODEL if LLM_PROVIDER == "groq" else OLLAMA_LLM_MODEL

EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.joblib")
DB_PATH = os.path.join(DATA_DIR, "conversations.db")

TOP_K = 5
LLM_TIMEOUT = 300
MAX_MESSAGE_LENGTH = 2000
MAX_TITLE_LENGTH = 200

# Cosine-similarity gates between query and the course centroid.
COURSE_THRESHOLD = float(os.getenv("COURSE_THRESHOLD", "0.58"))
GENERAL_THRESHOLD = float(os.getenv("GENERAL_THRESHOLD", "0.55"))

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET not set — using random secret. "
        "Sessions will not survive a restart. Set JWT_SECRET in production."
    )

if not os.path.isdir(DATA_DIR):
    raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")
