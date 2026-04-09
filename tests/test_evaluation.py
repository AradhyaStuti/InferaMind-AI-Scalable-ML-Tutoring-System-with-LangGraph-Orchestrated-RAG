"""Tests for RAGAS evaluation metrics.

Unit tests mock embeddings so they run without Ollama.
Integration tests (requires_embeddings) run the full pipeline.
"""

from unittest.mock import patch
import numpy as np

from tests.conftest import requires_embeddings

from backend.rag.evaluation import (
    _cosine_similarity,
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
    evaluate,
)
from backend.rag.embeddings import embedding_service


# ─── Unit tests (always run, no Ollama needed) ───────────────


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = np.array([1.0, 0.0, 0.0])
        assert _cosine_similarity(v, v) == 1.0

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert _cosine_similarity(a, b) == -1.0

    def test_zero_vector_returns_zero(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert _cosine_similarity(a, b) == 0.0


def _fake_embed(text):
    """Deterministic fake embedding: hash text into a 4D unit vector."""
    h = hash(text) % 10000
    vec = np.array([h % 7, h % 11, h % 13, h % 17], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _fake_embed_many(texts):
    return [_fake_embed(t) for t in texts]


class TestContextPrecisionUnit:
    @patch("backend.rag.evaluation._embed_many", side_effect=_fake_embed_many)
    @patch("backend.rag.evaluation._embed", side_effect=_fake_embed)
    def test_returns_float_in_range(self, mock_embed, mock_embed_many):
        sources = [{"text": "gradient descent optimizes"}, {"text": "cost function"}]
        score = context_precision("gradient descent", sources)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_empty_sources_returns_zero(self):
        assert context_precision("anything", []) == 0.0


class TestContextRecallUnit:
    @patch("backend.rag.evaluation._embed_many", side_effect=_fake_embed_many)
    def test_returns_float_in_range(self, mock_embed_many):
        sources = [{"text": "gradient descent updates parameters iteratively"}]
        gt = "Gradient descent updates parameters. It minimizes cost."
        score = context_recall(sources, gt)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_empty_sources_returns_zero(self):
        assert context_recall([], "some ground truth") == 0.0

    def test_empty_ground_truth_returns_zero(self):
        assert context_recall([{"text": "data"}], "") == 0.0


class TestFaithfulnessUnit:
    @patch("backend.rag.evaluation._embed_many", side_effect=_fake_embed_many)
    def test_returns_float_in_range(self, mock_embed_many):
        sources = [{"text": "linear regression predicts continuous values"}]
        answer = "Linear regression predicts values. It fits a line."
        score = faithfulness(answer, sources)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_empty_answer_returns_zero(self):
        assert faithfulness("", [{"text": "data"}]) == 0.0

    def test_empty_sources_returns_zero(self):
        assert faithfulness("some answer", []) == 0.0


class TestAnswerRelevancyUnit:
    @patch("backend.rag.evaluation._embed", side_effect=_fake_embed)
    def test_returns_float_in_range(self, mock_embed):
        score = answer_relevancy("What is ML?", "ML learns from data.")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_empty_question_returns_zero(self):
        assert answer_relevancy("", "some answer") == 0.0

    def test_empty_answer_returns_zero(self):
        assert answer_relevancy("some question", "") == 0.0


class TestEvaluateAggregateUnit:
    @patch("backend.rag.evaluation._embed_many", side_effect=_fake_embed_many)
    @patch("backend.rag.evaluation._embed", side_effect=_fake_embed)
    def test_returns_all_metric_keys(self, mock_embed, mock_embed_many):
        sources = [{"text": "supervised learning uses labeled data"}]
        metrics = evaluate("What is supervised learning?", "It uses labeled data.", sources)
        assert "context_precision" in metrics
        assert "faithfulness" in metrics
        assert "answer_relevancy" in metrics
        assert "ragas_score" in metrics
        for v in metrics.values():
            assert isinstance(v, float)
            assert 0.0 <= v <= 1.0

    @patch("backend.rag.evaluation._embed_many", side_effect=_fake_embed_many)
    @patch("backend.rag.evaluation._embed", side_effect=_fake_embed)
    def test_includes_recall_when_ground_truth_given(self, mock_embed, mock_embed_many):
        sources = [{"text": "gradient descent minimizes cost"}]
        metrics = evaluate(
            "What is gradient descent?",
            "It minimizes cost.",
            sources,
            ground_truth="Gradient descent minimizes the cost function.",
        )
        assert "context_recall" in metrics


# ─── Integration tests (require Ollama + embeddings) ─────────


@requires_embeddings
class TestEvaluationIntegration:
    def test_context_precision_real(self):
        sources = embedding_service.search("supervised learning")
        score = context_precision("What is supervised learning?", sources)
        assert 0.0 <= score <= 1.0
        assert score > 0.3

    def test_faithfulness_real(self):
        sources = embedding_service.search("linear regression")
        answer = "Linear regression fits a straight line to data to predict continuous values."
        score = faithfulness(answer, sources)
        assert 0.0 <= score <= 1.0

    def test_evaluate_aggregate_real(self):
        sources = embedding_service.search("supervised learning")
        answer = "Supervised learning uses labeled data to train models."
        metrics = evaluate("What is supervised learning?", answer, sources)
        assert "ragas_score" in metrics
        for v in metrics.values():
            assert 0.0 <= v <= 1.0
