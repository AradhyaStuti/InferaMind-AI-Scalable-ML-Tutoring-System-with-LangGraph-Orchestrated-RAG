"""FAISS-backed embedding search with a small LRU cache."""

import logging
from collections import OrderedDict
from threading import Lock

import numpy as np
import faiss
import joblib
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document

from backend.config import OLLAMA_URL, EMBED_MODEL, EMBEDDINGS_PATH, TOP_K

logger = logging.getLogger(__name__)

CACHE_MAX_SIZE = 128


class LRUCache:
    def __init__(self, max_size=CACHE_MAX_SIZE):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                return self._cache[key]
            self.misses += 1
            return None

    def put(self, key, value):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
            self._cache[key] = value

    @property
    def stats(self):
        total = self.hits + self.misses
        rate = (self.hits / total * 100) if total > 0 else 0
        return {"size": len(self._cache), "hits": self.hits, "misses": self.misses, "hit_rate": f"{rate:.1f}%"}


class EmbeddingService:
    def __init__(self):
        self.df = None
        self.vectorstore = None
        self._cache = LRUCache()
        self.embeddings = OllamaEmbeddings(
            model=EMBED_MODEL,
            base_url=OLLAMA_URL,
        )

    def load(self):
        self.df = joblib.load(EMBEDDINGS_PATH)
        documents = []
        embeddings_list = []

        for _, row in self.df.iterrows():
            doc = Document(
                page_content=row["text"].strip(),
                metadata={
                    "video": int(row["number"]),
                    "title": row.get("title", ""),
                    "start": round(float(row["start"]), 1),
                    "end": round(float(row["end"]), 1),
                },
            )
            documents.append(doc)
            embeddings_list.append(row["embedding"])

        emb_matrix = np.array(embeddings_list, dtype=np.float32)
        dimension = emb_matrix.shape[1]
        index = faiss.IndexFlatIP(dimension)
        faiss.normalize_L2(emb_matrix)
        index.add(emb_matrix)

        docstore = InMemoryDocstore(
            {str(i): doc for i, doc in enumerate(documents)}
        )

        self.vectorstore = FAISS(
            embedding_function=self.embeddings,
            index=index,
            docstore=docstore,
            index_to_docstore_id={i: str(i) for i in range(len(documents))},
        )
        logger.info("Loaded %d chunks into FAISS", len(self.df))

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        if self.vectorstore is None:
            raise RuntimeError("No vectorstore loaded")

        cache_key = (query.strip().lower(), top_k)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        docs_and_scores = self.vectorstore.similarity_search_with_score(query, k=top_k)

        results = []
        for doc, score in docs_and_scores:
            results.append({
                "video": doc.metadata.get("video", 0),
                "title": doc.metadata.get("title", ""),
                "start": doc.metadata.get("start", 0),
                "end": doc.metadata.get("end", 0),
                "text": doc.page_content,
                "similarity": round(float(score), 3),
            })

        self._cache.put(cache_key, results)
        return results

    @property
    def cache_stats(self):
        return self._cache.stats


embedding_service = EmbeddingService()
