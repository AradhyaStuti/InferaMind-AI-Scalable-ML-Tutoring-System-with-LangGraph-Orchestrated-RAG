"""Embeddings, FAISS search, and the 3-way classifier."""

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
        assert 0 < len(results) <= 5


@requires_embeddings
class TestGraphClassifier:
    def _classify(self, question: str) -> str:
        return classify_node({
            "question": question,
            "chat_history": [],
            "sources": [],
            "query_type": "",
        })["query_type"]

    def test_classify_course_related(self):
        assert self._classify("What is supervised learning?") == "course_related"

    def test_classify_off_topic(self):
        assert self._classify("Who won the 2022 FIFA World Cup final?") == "off_topic"
