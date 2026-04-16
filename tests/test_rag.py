"""Test RAG pipeline — embeddings, graph, and 3-way classifier."""

from tests.conftest import requires_embeddings

from backend.rag.embeddings import embedding_service
from backend.rag.graph import classify_node


@requires_embeddings
class TestEmbeddingService:
    def test_embeddings_loaded(self):
        assert embedding_service.df is not None
        assert len(embedding_service.df) > 0

    def test_search_returns_results(self):
        results = embedding_service.search("supervised learning")
        assert len(results) > 0
        assert len(results) <= 5

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


@requires_embeddings
class TestGraphClassifier:
    def _classify(self, question: str) -> str:
        state = {
            "question": question,
            "chat_history": [],
            "sources": [],
            "query_type": "",
        }
        return classify_node(state)["query_type"]

    def test_classify_course_related(self):
        """Direct course topic → course_related (RAG from videos)."""
        assert self._classify("What is supervised learning?") == "course_related"

    def test_classify_off_topic(self):
        """Completely unrelated → off_topic (rejected)."""
        assert self._classify("Who won the 2022 FIFA World Cup final?") == "off_topic"

    def test_classify_course_related_general(self):
        """ML topic not directly in video anchors → course_related_general."""
        result = self._classify("Explain transformers and attention mechanisms in deep learning")
        assert result in ("course_related_general", "course_related")

    def test_classify_returns_valid_type(self):
        """All classifications must be one of the three valid types."""
        for q in [
            "What is gradient descent?",
            "How do convolutional neural networks work?",
            "Tell me a joke about cats",
        ]:
            result = self._classify(q)
            assert result in ("course_related", "course_related_general", "off_topic")
