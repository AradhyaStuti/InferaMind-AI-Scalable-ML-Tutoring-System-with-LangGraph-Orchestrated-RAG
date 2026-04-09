"""LangChain-based LLM generation with provider abstraction, circuit breaker, and retry logic.

Supports two providers:
  - "groq"   → ChatGroq  (cloud, fast, large models like llama-3.3-70b)
  - "ollama" → ChatOllama (local, no API key needed)

Supports two generation modes:
  - RAG mode      → answers grounded in retrieved video transcripts
  - Direct mode   → answers ML questions from the model's own knowledge (when not in videos)
"""

import logging
import time
import threading

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from backend.config import (
    LLM_PROVIDER, LLM_TIMEOUT,
    OLLAMA_URL, OLLAMA_LLM_MODEL,
    GROQ_API_KEY, GROQ_LLM_MODEL,
)

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


llm_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

# Keep backward-compatible alias for health endpoint
ollama_breaker = llm_breaker


# ─── Provider-Agnostic LLM Factory ───────────────────────────

def _create_llm() -> BaseChatModel:
    """Create LLM instance based on configured provider."""
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            logger.warning(
                "LLM_PROVIDER=groq but GROQ_API_KEY is empty — falling back to Ollama"
            )
            return _create_ollama_llm()
        return _create_groq_llm()
    return _create_ollama_llm()


def _create_groq_llm() -> BaseChatModel:
    from langchain_groq import ChatGroq
    logger.info("LLM provider: Groq (%s)", GROQ_LLM_MODEL)
    return ChatGroq(
        model=GROQ_LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.3,
        max_tokens=1024,
    )


def _create_ollama_llm() -> BaseChatModel:
    from langchain_ollama import ChatOllama
    logger.info("LLM provider: Ollama (%s)", OLLAMA_LLM_MODEL)
    return ChatOllama(
        model=OLLAMA_LLM_MODEL,
        base_url=OLLAMA_URL,
        timeout=LLM_TIMEOUT,
    )


llm = _create_llm()


# ─── Prompts ─────────────────────────────────────────────────

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

DIRECT_KNOWLEDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an AI teaching assistant for Andrew Ng's Machine Learning Specialization.
The student asked a machine learning question that isn't directly covered in the course videos you have access to.

Answer from your own knowledge as a knowledgeable ML tutor. Be accurate and educational.

Instructions:
- Start with: "This topic isn't covered in the course videos I have, but here's what I can tell you:"
- Give a clear, correct, and thorough explanation
- Use examples and analogies where helpful
- Use markdown formatting for readability (bold, lists, code blocks, etc.)
- If the topic connects to something in the course (supervised/unsupervised learning, regression, gradient descent, neural networks, etc.), mention how it relates
- Be honest about the limits of your explanation — don't fabricate citations or sources""",
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
direct_chain = DIRECT_KNOWLEDGE_PROMPT | llm | StrOutputParser()
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


def _build_direct_input(question, history):
    return {
        "chat_history": format_chat_history(history or []),
        "question": question,
    }


def stream_tokens(question: str, sources: list[dict], history: list[dict] = None):
    """Stream RAG response tokens with circuit breaker and retry."""
    if llm_breaker.is_open:
        yield (
            "I'm having trouble connecting to the AI model right now. "
            "Please try again in a few seconds."
        )
        return

    inputs = _build_rag_input(question, sources, history)

    for attempt in range(MAX_RETRIES):
        try:
            for token in rag_chain.stream(inputs):
                yield token
            llm_breaker.record_success()
            return
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                llm_breaker.record_failure()
                logger.error(f"Stream failed after {MAX_RETRIES} retries: {e}")
                yield (
                    "\n\nI couldn't generate a response. "
                    "Please check your LLM configuration and try again."
                )
                return
            wait = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Stream attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)


def stream_direct_tokens(question: str, history: list[dict] = None):
    """Stream direct-knowledge response tokens (no RAG context)."""
    if llm_breaker.is_open:
        yield (
            "I'm having trouble connecting to the AI model right now. "
            "Please try again in a few seconds."
        )
        return

    inputs = _build_direct_input(question, history)

    for attempt in range(MAX_RETRIES):
        try:
            for token in direct_chain.stream(inputs):
                yield token
            llm_breaker.record_success()
            return
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                llm_breaker.record_failure()
                logger.error(f"Direct stream failed after {MAX_RETRIES} retries: {e}")
                yield (
                    "\n\nI couldn't generate a response. "
                    "Please check your LLM configuration and try again."
                )
                return
            wait = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Direct stream attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)


def generate_title(question: str) -> str:
    if llm_breaker.is_open:
        return question[:50]

    try:
        result = title_chain.invoke({"question": question})
        llm_breaker.record_success()
        return result.strip().strip('"')[:200]
    except Exception as e:
        llm_breaker.record_failure()
        logger.warning(f"Title generation failed: {e}")
        return question[:50]
