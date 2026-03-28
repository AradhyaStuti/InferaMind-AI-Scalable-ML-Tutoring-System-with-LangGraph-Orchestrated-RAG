"""Test RAG pipeline — embeddings, graph, and retrieval quality."""

from backend.rag.embeddings import embedding_service
from backend.rag.graph import run_graph, classify_node, retrieve_node


class TestEmbeddingService:
    """Test the FAISS embedding service."""

    def test_embeddings_loaded(self):
        assert embedding_service.df is not None
        assert len(embedding_service.df) > 0

    def test_vectorstore_initialized(self):
        assert embedding_service.vectorstore is not None

    def test_search_returns_results(self):
        results = embedding_service.search("supervised learning")
        assert len(results) > 0
        assert len(results) <= 5  # TOP_K default

    def test_search_result_structure(self):
        results = embedding_service.search("gradient descent")
        for r in results:
            assert "video" in r
            assert "text" in r
            assert "start" in r
            assert "end" in r
            assert "similarity" in r
            assert isinstance(r["similarity"], float)
            assert 0 <= r["similarity"] <= 1

    def test_search_relevance(self):
        """Results for 'machine learning' should contain relevant text."""
        results = embedding_service.search("machine learning")
        texts = " ".join(r["text"].lower() for r in results)
        assert "machine" in texts or "learning" in texts

    def test_search_custom_top_k(self):
        results = embedding_service.search("regression", top_k=3)
        assert len(results) <= 3

    def test_search_similarity_ordering(self):
        """Results should be ordered by similarity (descending)."""
        results = embedding_service.search("neural network")
        similarities = [r["similarity"] for r in results]
        assert similarities == sorted(similarities, reverse=True)


class TestGraphPipeline:
    """Test the LangGraph classify + retrieve pipeline (embeddings-based classifier)."""

    def test_classify_course_related(self):
        state = {
            "question": "What is supervised learning?",
            "chat_history": [],
            "sources": [],
            "query_type": "",
        }
        result = classify_node(state)
        assert result["query_type"] == "course_related"

    def test_classify_off_topic(self):
        state = {
            "question": "What is the best recipe for chocolate cake?",
            "chat_history": [],
            "sources": [],
            "query_type": "",
        }
        result = classify_node(state)
        assert result["query_type"] == "off_topic"

    def test_classify_course_question_about_regression(self):
        state = {
            "question": "How does logistic regression work in classification?",
            "chat_history": [],
            "sources": [],
            "query_type": "",
        }
        result = classify_node(state)
        assert result["query_type"] == "course_related"

    def test_classify_off_topic_sports(self):
        state = {
            "question": "Who won the FIFA World Cup last year?",
            "chat_history": [],
            "sources": [],
            "query_type": "",
        }
        result = classify_node(state)
        assert result["query_type"] == "off_topic"

    def test_retrieve_returns_sources(self):
        state = {
            "question": "What is linear regression?",
            "chat_history": [],
            "sources": [],
            "query_type": "course_related",
        }
        result = retrieve_node(state)
        assert len(result["sources"]) > 0

    def test_run_graph_course_related(self):
        result = run_graph("What is supervised learning?")
        assert result["query_type"] == "course_related"
        assert len(result["sources"]) > 0

    def test_run_graph_off_topic(self):
        result = run_graph("What is the best football team in the world?")
        assert result["query_type"] == "off_topic"
        assert result["sources"] == []

    def test_run_graph_with_history(self):
        history = [
            {"role": "user", "content": "What is ML?"},
            {"role": "assistant", "content": "Machine learning is..."},
        ]
        result = run_graph("Explain gradient descent", history)
        assert result["query_type"] == "course_related"

    def test_run_graph_preserves_question(self):
        result = run_graph("What is gradient descent?")
        assert result["question"] == "What is gradient descent?"
