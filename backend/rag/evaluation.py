"""RAGAS-style evaluation metrics for the RAG pipeline.

Implements four core metrics without external API dependencies:

1. Context Precision  — Are the top-ranked retrieved chunks actually relevant?
2. Context Recall     — Does the retrieved context cover the ground-truth answer?
3. Faithfulness       — Is the generated answer grounded in the retrieved context?
4. Answer Relevancy   — Does the generated answer address the original question?

All metrics return a float in [0, 1].  Higher is better.
"""

import numpy as np
from backend.rag.embeddings import embedding_service


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _embed(text: str) -> np.ndarray:
    return np.array(
        embedding_service.embeddings.embed_query(text), dtype=np.float32
    )


def _embed_many(texts: list[str]) -> np.ndarray:
    return np.array(
        embedding_service.embeddings.embed_documents(texts), dtype=np.float32
    )


# ─── Metric 1: Context Precision ──────────────────────────────────

def context_precision(question: str, sources: list[dict], k: int = 5) -> float:
    """Precision@K — fraction of retrieved chunks semantically relevant to the question.

    A chunk is "relevant" if its cosine similarity to the question exceeds 0.40.
    """
    if not sources:
        return 0.0

    top_sources = sources[:k]
    q_vec = _embed(question)
    chunk_vecs = _embed_many([s["text"] for s in top_sources])

    relevant = sum(
        1 for cv in chunk_vecs if _cosine_similarity(q_vec, cv) >= 0.40
    )
    return relevant / len(top_sources)


# ─── Metric 2: Context Recall ─────────────────────────────────────

def context_recall(
    sources: list[dict], ground_truth: str, threshold: float = 0.45
) -> float:
    """Measures how well retrieved context covers the ground-truth answer.

    Splits ground truth into sentences and checks what fraction is
    semantically supported by at least one retrieved chunk.
    """
    if not sources or not ground_truth.strip():
        return 0.0

    gt_sentences = [s.strip() for s in ground_truth.split(".") if s.strip()]
    if not gt_sentences:
        return 0.0

    gt_vecs = _embed_many(gt_sentences)
    chunk_vecs = _embed_many([s["text"] for s in sources])

    covered = 0
    for gv in gt_vecs:
        if any(_cosine_similarity(gv, cv) >= threshold for cv in chunk_vecs):
            covered += 1

    return covered / len(gt_sentences)


# ─── Metric 3: Faithfulness ───────────────────────────────────────

def faithfulness(answer: str, sources: list[dict], threshold: float = 0.45) -> float:
    """Measures how well the generated answer is grounded in retrieved context.

    Splits the answer into sentences and checks what fraction is
    semantically supported by at least one retrieved chunk.
    """
    if not sources or not answer.strip():
        return 0.0

    answer_sentences = [s.strip() for s in answer.split(".") if s.strip()]
    if not answer_sentences:
        return 0.0

    ans_vecs = _embed_many(answer_sentences)
    chunk_vecs = _embed_many([s["text"] for s in sources])

    grounded = 0
    for av in ans_vecs:
        if any(_cosine_similarity(av, cv) >= threshold for cv in chunk_vecs):
            grounded += 1

    return grounded / len(answer_sentences)


# ─── Metric 4: Answer Relevancy ───────────────────────────────────

def answer_relevancy(question: str, answer: str) -> float:
    """Cosine similarity between the question and answer embeddings."""
    if not question.strip() or not answer.strip():
        return 0.0
    return max(0.0, _cosine_similarity(_embed(question), _embed(answer)))


# ─── Aggregate ────────────────────────────────────────────────────

def evaluate(
    question: str,
    answer: str,
    sources: list[dict],
    ground_truth: str | None = None,
) -> dict[str, float]:
    """Run all available RAGAS metrics and return a summary dict."""
    metrics = {
        "context_precision": context_precision(question, sources),
        "faithfulness": faithfulness(answer, sources),
        "answer_relevancy": answer_relevancy(question, answer),
    }

    if ground_truth:
        metrics["context_recall"] = context_recall(sources, ground_truth)

    metrics["ragas_score"] = float(np.mean(list(metrics.values())))
    return metrics
