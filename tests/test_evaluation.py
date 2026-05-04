"""Unit tests mock the embedder; integration tests need Ollama + embeddings.joblib."""

from unittest.mock import patch
import numpy as np

from tests.conftest import requires_embeddings

from backend.rag.evaluation import (
    _cosine_similarity,
    context_precision,
    evaluate,
)
from backend.rag.embeddings import embedding_service


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
    h = hash(text) % 10000
    vec = np.array([h % 7, h % 11, h % 13, h % 17], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _fake_embed_many(texts):
    return [_fake_embed(t) for t in texts]


@patch("backend.rag.evaluation._embed_many", side_effect=_fake_embed_many)
@patch("backend.rag.evaluation._embed", side_effect=_fake_embed)
def test_context_precision_returns_float_in_range(mock_embed, mock_embed_many):
    sources = [{"text": "gradient descent optimizes"}, {"text": "cost function"}]
    score = context_precision("gradient descent", sources)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@patch("backend.rag.evaluation._embed_many", side_effect=_fake_embed_many)
@patch("backend.rag.evaluation._embed", side_effect=_fake_embed)
def test_evaluate_returns_all_metric_keys(mock_embed, mock_embed_many):
    sources = [{"text": "supervised learning uses labeled data"}]
    metrics = evaluate("What is supervised learning?", "It uses labeled data.", sources)
    assert {"context_precision", "faithfulness", "answer_relevancy", "ragas_score"} <= metrics.keys()
    for v in metrics.values():
        assert 0.0 <= v <= 1.0


@requires_embeddings
class TestEvaluationIntegration:
    def test_context_precision_real(self):
        sources = embedding_service.search("supervised learning")
        score = context_precision("What is supervised learning?", sources)
        assert score > 0.3

    def test_evaluate_aggregate_real(self):
        sources = embedding_service.search("supervised learning")
        metrics = evaluate(
            "What is supervised learning?",
            "Supervised learning uses labeled data to train models.",
            sources,
        )
        assert "ragas_score" in metrics
        for v in metrics.values():
            assert 0.0 <= v <= 1.0
