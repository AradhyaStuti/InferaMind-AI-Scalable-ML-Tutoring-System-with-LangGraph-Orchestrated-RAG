"""Tests for RAGAS evaluation metrics."""

from backend.rag.evaluation import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
    evaluate,
)
from backend.rag.embeddings import embedding_service
from backend.rag.graph import run_graph


class TestContextPrecision:
    def test_relevant_chunks_score_high(self):
        sources = embedding_service.search("supervised learning")
        score = context_precision("What is supervised learning?", sources)
        assert 0.0 <= score <= 1.0
        assert score > 0.3

    def test_empty_sources_returns_zero(self):
        assert context_precision("anything", []) == 0.0


class TestContextRecall:
    def test_recall_with_ground_truth(self):
        sources = embedding_service.search("gradient descent")
        gt = "Gradient descent is an optimization algorithm. It minimizes the cost function by iteratively updating parameters."
        score = context_recall(sources, gt)
        assert 0.0 <= score <= 1.0

    def test_empty_sources_returns_zero(self):
        assert context_recall([], "some ground truth") == 0.0


class TestFaithfulness:
    def test_grounded_answer_scores_high(self):
        sources = embedding_service.search("linear regression")
        answer = "Linear regression fits a straight line to data to predict continuous values."
        score = faithfulness(answer, sources)
        assert 0.0 <= score <= 1.0

    def test_empty_answer_returns_zero(self):
        sources = embedding_service.search("anything")
        assert faithfulness("", sources) == 0.0


class TestAnswerRelevancy:
    def test_relevant_answer_scores_high(self):
        score = answer_relevancy(
            "What is machine learning?",
            "Machine learning is a subset of AI that learns patterns from data.",
        )
        assert score > 0.5

    def test_irrelevant_answer_scores_low(self):
        score = answer_relevancy(
            "What is machine learning?",
            "The recipe for chocolate cake requires flour and sugar.",
        )
        assert score < 0.5

    def test_empty_returns_zero(self):
        assert answer_relevancy("", "answer") == 0.0
        assert answer_relevancy("question", "") == 0.0


class TestEvaluateAggregate:
    def test_returns_all_metrics(self):
        result = run_graph("What is supervised learning?")
        sources = result["sources"]
        answer = "Supervised learning uses labeled data to train models."
        metrics = evaluate("What is supervised learning?", answer, sources)
        assert "context_precision" in metrics
        assert "faithfulness" in metrics
        assert "answer_relevancy" in metrics
        assert "ragas_score" in metrics
        for v in metrics.values():
            assert 0.0 <= v <= 1.0

    def test_with_ground_truth_includes_recall(self):
        sources = embedding_service.search("regression")
        metrics = evaluate(
            "What is regression?",
            "Regression predicts continuous values.",
            sources,
            ground_truth="Regression is a supervised learning technique for predicting continuous output.",
        )
        assert "context_recall" in metrics
