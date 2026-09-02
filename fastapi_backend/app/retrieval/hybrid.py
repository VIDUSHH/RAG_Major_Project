"""
Hybrid retrieval module combining dense vector search, sparse BM25 search,
Reciprocal Rank Fusion (RRF), and cross-encoder reranking.
"""

import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.logging import logger
from app.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.services.vector_service import QdrantService, get_qdrant_service


@dataclass
class RetrievalCandidate:
    """A candidate document from retrieval."""

    id: str
    text: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    retrieval_method: str = "unknown"
    rank: int = 0


@dataclass
class RetrievalResult:
    """Final retrieval result after fusion and reranking."""

    candidates: list[RetrievalCandidate]
    query: str
    total_candidates: int
    retrieval_time_ms: float
    fusion_method: str
    reranked: bool = False


class BaseRetriever(ABC):
    """Abstract base class for retrievers."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        query_vector: list[float],
        filter_: dict[str, Any] | None = None,
        top_k: int = 50,
    ) -> list[RetrievalCandidate]:
        """Retrieve candidates for a query."""
        pass

    @abstractmethod
    def add_documents(self, documents: list[dict[str, Any]], embeddings: list[list[float]]):
        """Add documents to the retriever index."""
        pass


class DenseVectorRetriever(BaseRetriever):
    """Dense vector retrieval using Qdrant."""

    def __init__(
        self,
        qdrant_service: QdrantService | None = None,
        collection_name: str | None = None,
    ):
        self.qdrant = qdrant_service or get_qdrant_service()
        self.collection_name = collection_name or "postmortems_v1"

    def retrieve(
        self,
        query: str,
        query_vector: list[float],
        filter_: dict[str, Any] | None = None,
        top_k: int = 50,
    ) -> list[RetrievalCandidate]:
        qdrant_filter = None
        if filter_:
            qdrant_filter = self.qdrant.create_tenant_filter(
                organization_id=filter_.get("organization_id", ""),
                project_id=filter_.get("project_id"),
                service=filter_.get("service"),
                level=filter_.get("level"),
                start_time=filter_.get("start_time"),
                end_time=filter_.get("end_time"),
            )

        results = self.qdrant.search(
            query_vector=query_vector,
            collection_name=self.collection_name,
            limit=top_k,
            filter_=qdrant_filter,
            with_vectors=False,
        )

        candidates = []
        for rank, result in enumerate(results):
            candidates.append(
                RetrievalCandidate(
                    id=result.id,
                    text=result.payload.get("text", ""),
                    score=result.score,
                    source=result.payload.get("source", "unknown"),
                    metadata=result.payload,
                    retrieval_method="dense",
                    rank=rank,
                )
            )
        return candidates

    def add_documents(self, documents: list[dict[str, Any]], embeddings: list[list[float]]):
        """Not implemented for dense retriever - use QdrantService directly."""
        pass


class SparseBM25Retriever(BaseRetriever):
    """Sparse retrieval using BM25.

    The corpus is built lazily from Qdrant on first use (the vector store is
    the source of truth; ingest writes points directly, so no incremental
    index is maintained). It is refreshed periodically when new points arrive.
    """

    def __init__(
        self,
        collection_name: str | None = None,
        max_corpus_docs: int = 50000,
    ):
        self.collection_name = collection_name or "postmortems_v1"
        self.max_corpus_docs = max_corpus_docs
        self.bm25: BM25Okapi | None = None
        self.documents: list[dict[str, Any]] = []
        self.tokenized_corpus: list[list[str]] = []
        self._corpus_count: int = 0
        self._count_checks: int = 0

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        import re

        return re.findall(r"\b\w+\b", text.lower())

    def _reset_corpus(self):
        self.bm25 = None
        self.documents = []
        self.tokenized_corpus = []

    def _build_corpus(self, qdrant_service, collection_name: str) -> None:
        """Build the BM25 index by scrolling the Qdrant collection."""
        documents = []
        offset = None
        while True:
            points, offset = qdrant_service.scroll(
                collection_name=collection_name,
                limit=1000,
                offset=offset,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                text = payload.get("text", "")
                if text:
                    documents.append(
                        {
                            "id": point.id,
                            "text": text,
                            "source": payload.get("source", "unknown"),
                            "metadata": payload,
                        }
                    )
                if len(documents) >= self.max_corpus_docs:
                    break
            if offset is None or len(documents) >= self.max_corpus_docs:
                break

        if documents:
            self.documents = documents
            self.tokenized_corpus = [self._tokenize(doc["text"]) for doc in documents]
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self._corpus_count = len(documents)
            logger.info(f"Built BM25 index from Qdrant: {len(documents)} documents")
        else:
            self._corpus_count = 0
            logger.debug("No documents in Qdrant for BM25 index")

    def _ensure_corpus(self, qdrant_service, collection_name: str) -> None:
        """Build the corpus lazily, refreshing it when new points arrive."""
        if self.bm25 is not None:
            self._count_checks += 1
            if self._count_checks < 25:
                return
            self._count_checks = 0
            try:
                stats = qdrant_service.get_collection_stats(collection_name)
                if stats.points_count == self._corpus_count:
                    return
            except Exception as e:
                logger.debug(f"Could not check collection stats for BM25 refresh: {e}")
                return
            self._reset_corpus()

        try:
            self._build_corpus(qdrant_service, collection_name)
        except Exception as e:
            logger.warning(f"Failed to build BM25 index from Qdrant: {e}")

    def retrieve(
        self,
        query: str,
        query_vector: list[float],
        filter_: dict[str, Any] | None = None,
        top_k: int = 50,
    ) -> list[RetrievalCandidate]:
        if self.bm25 is None:
            try:
                self._ensure_corpus(get_qdrant_service(), self.collection_name)
            except Exception as e:
                logger.debug(f"BM25 corpus unavailable, sparse channel disabled: {e}")

        if self.bm25 is None or not self.documents:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        if filter_:
            org_id = filter_.get("organization_id")
            if org_id:
                mask = [
                    doc.get("metadata", {}).get("organization_id") == org_id
                    for doc in self.documents
                ]
                scores = np.where(mask, scores, -1e9)

        top_indices = np.argsort(scores)[::-1][:top_k]

        candidates = []
        for rank, idx in enumerate(top_indices):
            if scores[idx] > 0:
                doc = self.documents[idx]
                candidates.append(
                    RetrievalCandidate(
                        id=doc["id"],
                        text=doc["text"],
                        score=float(scores[idx]),
                        source=doc.get("source", "unknown"),
                        metadata=doc.get("metadata", {}),
                        retrieval_method="sparse",
                        rank=rank,
                    )
                )
        return candidates

    def add_documents(self, documents: list[dict[str, Any]], embeddings: list[list[float]]):
        """Add documents to BM25 index."""
        self.documents = documents
        self.tokenized_corpus = [self._tokenize(doc["text"]) for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"Built BM25 index with {len(documents)} documents")


class HybridRetriever:
    """
    Hybrid retriever combining dense and sparse retrieval with RRF fusion
    and optional cross-encoder reranking.
    """

    def __init__(
        self,
        dense_retriever: DenseVectorRetriever | None = None,
        sparse_retriever: SparseBM25Retriever | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        collection_name: str | None = None,
        rrf_k: int = 60,
        enable_reranking: bool = True,
        rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        rerank_top_k: int = 20,
    ):
        self.collection_name = collection_name or "postmortems_v1"
        self.dense = dense_retriever or DenseVectorRetriever(collection_name=self.collection_name)
        self.sparse = sparse_retriever or SparseBM25Retriever(collection_name=self.collection_name)
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.rrf_k = rrf_k
        self.enable_reranking = enable_reranking
        self.rerank_model_name = rerank_model
        self.rerank_top_k = rerank_top_k
        self._reranker = None

    def _get_reranker(self):
        """Lazy load cross-encoder reranker."""
        if self._reranker is None and self.enable_reranking:
            try:
                from sentence_transformers import CrossEncoder

                self._reranker = CrossEncoder(self.rerank_model_name)
                logger.info(f"Loaded reranker: {self.rerank_model_name}")
            except Exception as e:
                logger.warning(f"Failed to load reranker: {e}")
                self.enable_reranking = False
        return self._reranker

    def retrieve(
        self,
        query: str,
        filter_: dict[str, Any] | None = None,
        top_k: int = 10,
        dense_top_k: int = 50,
        sparse_top_k: int = 50,
    ) -> RetrievalResult:
        """Perform hybrid retrieval with RRF fusion and optional reranking."""
        start_time = time.time()

        query_vector = self.embedding_provider.embed_query(query)

        dense_candidates = self.dense.retrieve(
            query=query,
            query_vector=query_vector,
            filter_=filter_,
            top_k=dense_top_k,
        )

        sparse_candidates = self.sparse.retrieve(
            query=query,
            query_vector=query_vector,
            filter_=filter_,
            top_k=sparse_top_k,
        )

        fused_candidates = self._reciprocal_rank_fusion(
            dense_candidates, sparse_candidates, top_k=max(dense_top_k, sparse_top_k)
        )

        reranked = False
        if self.enable_reranking and fused_candidates:
            reranker = self._get_reranker()
            if reranker:
                fused_candidates = self._rerank_candidates(
                    query, fused_candidates, self.rerank_top_k
                )
                reranked = True

        final_candidates = fused_candidates[:top_k]

        retrieval_time_ms = (time.time() - start_time) * 1000

        return RetrievalResult(
            candidates=final_candidates,
            query=query,
            total_candidates=len(dense_candidates) + len(sparse_candidates),
            retrieval_time_ms=retrieval_time_ms,
            fusion_method="rrf",
            reranked=reranked,
        )

    def _reciprocal_rank_fusion(
        self,
        dense_results: list[RetrievalCandidate],
        sparse_results: list[RetrievalCandidate],
        top_k: int = 50,
    ) -> list[RetrievalCandidate]:
        """Combine results using Reciprocal Rank Fusion."""
        scores = defaultdict(float)
        candidate_map = {}

        for rank, candidate in enumerate(dense_results):
            scores[candidate.id] += 1.0 / (self.rrf_k + rank + 1)
            candidate_map[candidate.id] = candidate

        for rank, candidate in enumerate(sparse_results):
            scores[candidate.id] += 1.0 / (self.rrf_k + rank + 1)
            if candidate.id not in candidate_map:
                candidate_map[candidate.id] = candidate

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

        fused = []
        for rank, candidate_id in enumerate(sorted_ids):
            candidate = candidate_map[candidate_id]
            candidate.score = scores[candidate_id]
            candidate.retrieval_method = "hybrid_rrf"
            candidate.rank = rank
            fused.append(candidate)

        return fused

    def _rerank_candidates(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalCandidate]:
        """Rerank candidates using cross-encoder."""
        reranker = self._get_reranker()
        if not reranker:
            return candidates

        pairs = [(query, c.text) for c in candidates[:top_k]]
        scores = reranker.predict(pairs)

        for candidate, score in zip(candidates[:top_k], scores, strict=True):
            candidate.score = float(score)
            candidate.retrieval_method = "hybrid_reranked"

        candidates[:top_k] = sorted(candidates[:top_k], key=lambda c: c.score, reverse=True)
        for rank, candidate in enumerate(candidates):
            candidate.rank = rank

        return candidates

    def add_documents(self, documents: list[dict[str, Any]], embeddings: list[list[float]]):
        """Add documents to both retrievers."""
        self.sparse.add_documents(documents, embeddings)
        logger.info(f"Added {len(documents)} documents to hybrid retriever")


_hybrid_retriever: HybridRetriever | None = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create singleton hybrid retriever."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever(enable_reranking=settings.RERANKING_ENABLED)
    return _hybrid_retriever
