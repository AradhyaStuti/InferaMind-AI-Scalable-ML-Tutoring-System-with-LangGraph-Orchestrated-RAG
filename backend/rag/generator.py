"""LangChain-based LLM generation with circuit breaker and retry logic."""

import logging
import time
import threading

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from backend.config import OLLAMA_URL, LLM_MODEL, LLM_TIMEOUT

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 1  # seconds


# ─── Circuit Breaker ───────────────────────────────────────────

class CircuitBreaker:
    """Prevents repeated calls to a failing service."""

    def __init__(self, failure_threshold=3, recovery_timeout=30):
        self._failure_count = 0
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time = 0
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._failure_count >= self._threshold:
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    # Half-open: allow one attempt
                    self._failure_count = self._threshold - 1
                    return False
                return True
            return False

    def record_success(self):
        with self._lock:
            self._failure_count = 0

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()


ollama_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)


# ─── LLM Setup ────────────────────────────────────────────────

llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_URL,
    timeout=LLM_TIMEOUT,
)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an AI teaching assistant for Andrew Ng's Machine Learning Specialization (Course 1).
You help students navigate the course by answering questions and pointing them to specific videos and timestamps.

Use the following retrieved transcript excerpts to answer the student's question:

{context}

Instructions:
- Answer in a clear, helpful, and conversational way
- Reference specific videos and timestamps (e.g., "In Video 2 around 1:30...")
- If the question is unrelated to the course, politely say you can only help with these 4 videos
- Use markdown formatting for readability (bold, lists, etc.)
- Keep responses focused and informative, like a real tutor would""",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ]
)

TITLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Generate a short, concise title (max 6 words) for a conversation that starts with this question. Return only the title, nothing else.",
        ),
        ("human", "{question}"),
    ]
)

# Pre-build chains as singletons
rag_chain = RAG_PROMPT | llm | StrOutputParser()
title_chain = TITLE_PROMPT | llm | StrOutputParser()


def format_context(sources: list[dict]) -> str:
    lines = []
    for s in sources:
        video = s.get('video', '?')
        start = s.get('start', 0)
        end = s.get('end', 0)
        sim = s.get('similarity', 0)
        text = s.get('text', '')
        lines.append(f"[Video {video} | {start}s - {end}s | Relevance: {sim}]\n{text}")
    return "\n\n".join(lines)


def format_chat_history(history: list[dict]) -> list:
    messages = []
    for msg in history[-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    return messages


def _build_rag_input(question, sources, history):
    return {
        "context": format_context(sources),
        "chat_history": format_chat_history(history or []),
        "question": question,
    }


def stream_tokens(question: str, sources: list[dict], history: list[dict] = None):
    """Stream response tokens with circuit breaker and retry."""
    if ollama_breaker.is_open:
        yield (
            "I'm having trouble connecting to the AI model right now. "
            "Please try again in a few seconds. Make sure Ollama is running."
        )
        return

    inputs = _build_rag_input(question, sources, history)

    for attempt in range(MAX_RETRIES):
        try:
            for token in rag_chain.stream(inputs):
                yield token
            ollama_breaker.record_success()
            return
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                ollama_breaker.record_failure()
                logger.error(f"Stream failed after {MAX_RETRIES} retries: {e}")
                yield (
                    "\n\nI couldn't generate a response. "
                    "Please check that Ollama is running and try again."
                )
                return
            wait = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Stream attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)


def generate_title(question: str) -> str:
    if ollama_breaker.is_open:
        return question[:50]

    try:
        result = title_chain.invoke({"question": question})
        ollama_breaker.record_success()
        return result.strip().strip('"')[:200]
    except Exception as e:
        ollama_breaker.record_failure()
        logger.warning(f"Title generation failed: {e}")
        return question[:50]
