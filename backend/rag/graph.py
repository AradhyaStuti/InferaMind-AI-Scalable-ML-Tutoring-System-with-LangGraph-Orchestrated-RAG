"""LangGraph routing: classify (per-course anchor scores) → retrieve / direct / off-topic."""

import time
import logging
from typing import TypedDict, Literal

import numpy as np
from langgraph.graph import StateGraph, END

from backend.rag.embeddings import embedding_service
from backend.rag.courses import COURSES, DEFAULT_COURSE_ID, get_course
from backend.config import COURSE_THRESHOLD, GENERAL_THRESHOLD

logger = logging.getLogger("backend.rag.pipeline")

# course_id → matrix of unit-norm anchor embeddings; populated lazily.
_anchor_matrices: dict[str, np.ndarray] = {}


def _ensure_anchor_matrices() -> dict[str, np.ndarray]:
    if _anchor_matrices:
        return _anchor_matrices
    for course_id, meta in COURSES.items():
        anchors = meta.get("anchors", [])
        if not anchors:
            continue
        vecs = embedding_service.embeddings.embed_documents(anchors)
        mat = np.array(vecs, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        _anchor_matrices[course_id] = mat / norms
    return _anchor_matrices


def _score_course(q_vec: np.ndarray, anchor_mat: np.ndarray) -> float:
    """Course score = max cosine similarity to any single anchor.

    Sharper than a single centroid when the anchor set spans multiple sub-topics —
    a query about one specific topic gets the credit it deserves instead of being
    averaged down by unrelated anchors.
    """
    sims = anchor_mat @ q_vec
    return float(sims.max())


class GraphState(TypedDict):
    question: str
    chat_history: list[dict]
    sources: list[dict]
    query_type: str
    course_id: str


def classify_node(state: GraphState) -> GraphState:
    t0 = time.time()
    anchor_matrices = _ensure_anchor_matrices()

    q_vec = np.array(
        embedding_service.embeddings.embed_query(state["question"]),
        dtype=np.float32,
    )
    norm = np.linalg.norm(q_vec)
    if norm > 0:
        q_vec /= norm

    best_course = DEFAULT_COURSE_ID
    best_score = -1.0
    for course_id, mat in anchor_matrices.items():
        score = _score_course(q_vec, mat)
        if score > best_score:
            best_score = score
            best_course = course_id

    course_meta = get_course(best_course) or {}
    course_thresh = float(course_meta.get("course_threshold", COURSE_THRESHOLD))
    general_thresh = float(course_meta.get("general_threshold", GENERAL_THRESHOLD))

    if best_score >= course_thresh:
        query_type = "course_related"
    elif best_score >= general_thresh:
        query_type = "course_related_general"
    else:
        query_type = "off_topic"

    ms = round((time.time() - t0) * 1000, 1)
    logger.info(
        "classify query=%r best_course=%s sim=%.3f course_thresh=%.2f general_thresh=%.2f result=%s time=%sms",
        state["question"][:80], best_course, best_score,
        course_thresh, general_thresh, query_type, ms,
    )
    return {**state, "query_type": query_type, "course_id": best_course}


def retrieve_node(state: GraphState) -> GraphState:
    t0 = time.time()
    sources = embedding_service.search(
        state["question"],
        course_id=state.get("course_id") or None,
    )
    ms = round((time.time() - t0) * 1000, 1)
    top_sim = round(sources[0]["similarity"], 3) if sources else 0
    logger.info(
        "retrieve query=%r course=%s chunks=%d top_similarity=%.3f time=%sms cache=%s",
        state["question"][:80], state.get("course_id"), len(sources), top_sim, ms, embedding_service.cache_stats,
    )
    return {**state, "sources": sources}


def direct_knowledge_node(state: GraphState) -> GraphState:
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
        "course_id": "",
    })
