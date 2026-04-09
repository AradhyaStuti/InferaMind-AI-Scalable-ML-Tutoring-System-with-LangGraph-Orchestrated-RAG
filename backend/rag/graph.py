"""
LangGraph RAG agent — 3-way classify + retrieve.

Graph: START -> classify -> retrieve -> END          (in-video)
                  |
                  +-> direct_knowledge -> END        (ML topic, not in videos)
                  |
                  +-> off_topic -> END               (not ML at all)

Generation is handled separately via streaming in chat.py.
"""

import time
import logging
from typing import TypedDict, Literal

import numpy as np
from langgraph.graph import StateGraph, END

from backend.rag.embeddings import embedding_service
from backend.config import COURSE_THRESHOLD, GENERAL_THRESHOLD

logger = logging.getLogger("backend.rag.pipeline")

# ─── Embeddings-based classifier ────────────────────────────────
# Anchor phrases representing course-related topics.
# At startup, these are embedded and the mean vector becomes the
# "course centroid".  A query is course-related when its cosine
# similarity to this centroid exceeds COURSE_THRESHOLD.

COURSE_ANCHORS = [
    "supervised learning", "unsupervised learning", "regression",
    "classification", "gradient descent", "cost function",
    "neural network", "machine learning algorithm", "training set",
    "linear regression", "logistic regression", "feature scaling",
    "Andrew Ng", "model training", "overfitting", "underfitting",
    "learning rate", "decision boundary", "regularization",
]

_course_centroid: np.ndarray | None = None


def _ensure_centroid() -> np.ndarray:
    """Lazily compute and cache the course centroid vector."""
    global _course_centroid
    if _course_centroid is None:
        vecs = embedding_service.embeddings.embed_documents(COURSE_ANCHORS)
        mat = np.array(vecs, dtype=np.float32)
        centroid = mat.mean(axis=0)
        centroid /= np.linalg.norm(centroid)
        _course_centroid = centroid
    return _course_centroid


class GraphState(TypedDict):
    question: str
    chat_history: list[dict]
    sources: list[dict]
    query_type: str


def classify_node(state: GraphState) -> GraphState:
    """3-way embeddings-based classification.

    >= COURSE_THRESHOLD  → 'course_related'         (RAG from videos)
    >= GENERAL_THRESHOLD → 'course_related_general'  (LLM answers from own knowledge)
    < GENERAL_THRESHOLD  → 'off_topic'               (rejected)
    """
    t0 = time.time()

    centroid = _ensure_centroid()
    q_vec = np.array(
        embedding_service.embeddings.embed_query(state["question"]),
        dtype=np.float32,
    )
    q_vec /= np.linalg.norm(q_vec)

    similarity = float(np.dot(q_vec, centroid))

    if similarity >= COURSE_THRESHOLD:
        query_type = "course_related"
    elif similarity >= GENERAL_THRESHOLD:
        query_type = "course_related_general"
    else:
        query_type = "off_topic"

    ms = round((time.time() - t0) * 1000, 1)
    logger.info(
        "classify query=%r sim=%.3f course_thresh=%.2f general_thresh=%.2f result=%s time=%sms",
        state["question"][:80], similarity,
        COURSE_THRESHOLD, GENERAL_THRESHOLD, query_type, ms,
    )
    return {**state, "query_type": query_type}


def retrieve_node(state: GraphState) -> GraphState:
    t0 = time.time()
    sources = embedding_service.search(state["question"])
    ms = round((time.time() - t0) * 1000, 1)
    top_sim = round(sources[0]["similarity"], 3) if sources else 0
    logger.info(
        "retrieve query=%r chunks=%d top_similarity=%.3f time=%sms cache=%s",
        state["question"][:80], len(sources), top_sim, ms, embedding_service.cache_stats,
    )
    return {**state, "sources": sources}


def direct_knowledge_node(state: GraphState) -> GraphState:
    """ML-related but not in videos — pass through with empty sources."""
    return {**state, "sources": []}


def off_topic_node(state: GraphState) -> GraphState:
    return {**state, "sources": []}


def route_after_classify(
    state: GraphState,
) -> Literal["retrieve", "direct_knowledge", "off_topic"]:
    if state["query_type"] == "course_related":
        return "retrieve"
    if state["query_type"] == "course_related_general":
        return "direct_knowledge"
    return "off_topic"


def build_graph() -> StateGraph:
    workflow = StateGraph(GraphState)
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("direct_knowledge", direct_knowledge_node)
    workflow.add_node("off_topic", off_topic_node)
    workflow.set_entry_point("classify")
    workflow.add_conditional_edges("classify", route_after_classify, {
        "retrieve": "retrieve",
        "direct_knowledge": "direct_knowledge",
        "off_topic": "off_topic",
    })
    workflow.add_edge("retrieve", END)
    workflow.add_edge("direct_knowledge", END)
    workflow.add_edge("off_topic", END)
    return workflow.compile()


rag_graph = build_graph()


def run_graph(question: str, chat_history: list[dict] = None) -> GraphState:
    return rag_graph.invoke({
        "question": question,
        "chat_history": chat_history or [],
        "sources": [],
        "query_type": "",
    })
