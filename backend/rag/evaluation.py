"""RAGAS-style metrics, computed locally with the embedding service."""

import numpy as np
from backend.rag.embeddings import embedding_service


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _embed(text: str) -> np.ndarray:
    return np.array(embedding_service.embeddings.embed_query(text), dtype=np.float32)


def _embed_many(texts: list[str]) -> np.ndarray:
    return np.array(embedding_service.embeddings.embed_documents(texts), dtype=np.float32)


def _coverage(target_sentences: list[str], chunk_vecs: np.ndarray, threshold: float) -> float:
    if not target_sentences:
        return 0.0
    target_vecs = _embed_many(target_sentences)
    covered = sum(
        1 for tv in target_vecs
        if any(_cosine_similarity(tv, cv) >= threshold for cv in chunk_vecs)
    )
    return covered / len(target_sentences)


def context_precision(question: str, sources: list[dict], k: int = 5) -> float:
    if not sources:
        return 0.0
    top_sources = sources[:k]
    q_vec = _embed(question)
    chunk_vecs = _embed_many([s["text"] for s in top_sources])
    relevant = sum(1 for cv in chunk_vecs if _cosine_similarity(q_vec, cv) >= 0.40)
    return relevant / len(top_sources)


def context_recall(sources: list[dict], ground_truth: str, threshold: float = 0.45) -> float:
    if not sources or not ground_truth.strip():
        return 0.0
    sentences = [s.strip() for s in ground_truth.split(".") if s.strip()]
    chunk_vecs = _embed_many([s["text"] for s in sources])
    return _coverage(sentences, chunk_vecs, threshold)


def faithfulness(answer: str, sources: list[dict], threshold: float = 0.45) -> float:
    if not sources or not answer.strip():
        return 0.0
    sentences = [s.strip() for s in answer.split(".") if s.strip()]
    chunk_vecs = _embed_many([s["text"] for s in sources])
    return _coverage(sentences, chunk_vecs, threshold)


def answer_relevancy(question: str, answer: str) -> float:
    if not question.strip() or not answer.strip():
        return 0.0
    return max(0.0, _cosine_similarity(_embed(question), _embed(answer)))


def evaluate(
    question: str,
    answer: str,
    sources: list[dict],
    ground_truth: str | None = None,
) -> dict[str, float]:
    metrics = {
        "context_precision": context_precision(question, sources),
        "faithfulness": faithfulness(answer, sources),
        "answer_relevancy": answer_relevancy(question, answer),
    }
    if ground_truth:
        metrics["context_recall"] = context_recall(sources, ground_truth)
    metrics["ragas_score"] = float(np.mean(list(metrics.values())))
    return metrics
