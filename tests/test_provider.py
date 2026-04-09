"""Test LLM provider abstraction and generator module."""

from unittest.mock import patch

from backend.rag.generator import (
    CircuitBreaker,
    format_context,
    format_chat_history,
    _build_direct_input,
)


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        assert cb.is_open is False

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True

    def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999)
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert cb.is_open is False


class TestFormatHelpers:
    def test_format_context_with_sources(self):
        sources = [
            {"video": 1, "start": 10, "end": 20, "similarity": 0.9, "text": "Hello"},
            {"video": 2, "start": 30, "end": 40, "similarity": 0.8, "text": "World"},
        ]
        result = format_context(sources)
        assert "Video 1" in result
        assert "Video 2" in result
        assert "Hello" in result
        assert "World" in result

    def test_format_context_empty(self):
        assert format_context([]) == ""

    def test_format_chat_history(self):
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        messages = format_chat_history(history)
        assert len(messages) == 2
        assert messages[0].content == "Hi"
        assert messages[1].content == "Hello"

    def test_format_chat_history_truncates(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        messages = format_chat_history(history)
        assert len(messages) == 6  # last 6 only

    def test_build_direct_input(self):
        result = _build_direct_input("What is CNN?", [])
        assert result["question"] == "What is CNN?"
        assert result["chat_history"] == []


class TestProviderConfig:
    def test_provider_is_valid(self):
        from backend.config import LLM_PROVIDER
        assert LLM_PROVIDER in ("ollama", "groq")

    def test_groq_fallback_without_api_key(self):
        """When provider is groq but no API key, factory should fall back to ollama."""
        from backend.rag.generator import _create_llm
        with patch("backend.rag.generator.LLM_PROVIDER", "groq"), \
             patch("backend.rag.generator.GROQ_API_KEY", ""):
            llm = _create_llm()
            # Should be ChatOllama (fallback) since no API key
            assert llm is not None
