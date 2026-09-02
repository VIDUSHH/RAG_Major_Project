"""
Qdrant vector database service for the RAG pipeline.

Provides high-level operations for collection management, point insertion,
search, filtering, and health checks.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HnswConfigDiff,
    MatchValue,
    OptimizersConfigDiff,
    PointStruct,
    QueryRequest,
    Range,
    SearchParams,
    VectorParams,
)

from app.core.config import settings
from app.core.logging import logger


@dataclass
class VectorSearchResult:
    """Result from vector search."""

    id: str
    score: float
    payload: dict[str, Any]
    vector: list[float] | None = None


@dataclass
class CollectionStats:
    """Collection statistics."""

    name: str
    vectors_count: int
    points_count: int
    segments_count: int
    status: str
    optimizer_status: str
    dimension: int
    distance: str


class QdrantService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self):
        self._client: QdrantClient | None = None
        self._default_collection = "postmortems_v1"
        self._ensured_collections: set[str] = set()

    def _get_client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            if settings.QDRANT_URL:
                logger.info(f"Connecting to Qdrant Cloud: {settings.QDRANT_URL}")
                self._client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY or None,
                )
            else:
                logger.info(
                    f"Connecting to local Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
                )
                self._client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    grpc_port=settings.QDRANT_GRPC_PORT,
                    api_key=settings.QDRANT_API_KEY or None,
                )
        return self._client

    def close(self):
        """Close the client connection."""
        if self._client:
            self._client.close()
            self._client = None

    def health_check(self) -> bool:
        """Check if Qdrant is accessible."""
        try:
            client = self._get_client()
            client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def get_collection_stats(self, collection_name: str | None = None) -> CollectionStats:
        """Get collection statistics."""
        client = self._get_client()
        name = collection_name or self._default_collection
        try:
            info = client.get_collection(collection_name=name)
            segments = getattr(info, "segments", None) or []
            return CollectionStats(
                name=name,
                vectors_count=info.points_count or 0,
                points_count=info.points_count or 0,
                segments_count=len(segments),
                status=info.status.value if info.status else "unknown",
                optimizer_status=info.optimizer_status.value
                if info.optimizer_status
                else "unknown",
                dimension=info.config.params.vectors.size if info.config.params.vectors else 0,
                distance=info.config.params.vectors.distance.value
                if info.config.params.vectors
                else "unknown",
            )
        except UnexpectedResponse as e:
            if e.status_code == 404:
                return CollectionStats(
                    name=name,
                    vectors_count=0,
                    points_count=0,
                    segments_count=0,
                    status="not_found",
                    optimizer_status="unknown",
                    dimension=0,
                    distance="unknown",
                )
            raise

    def list_collections(self) -> list[str]:
        """List all collection names."""
        client = self._get_client()
        collections = client.get_collections().collections
        return [c.name for c in collections]

    def _collection_dimension(self, collection_name: str) -> int | None:
        """Return the configured vector dimension of an existing collection, or None."""
        try:
            info = self._get_client().get_collection(collection_name=collection_name)
            vectors = info.config.params.vectors
            return vectors.size if vectors else None
        except Exception:
            return None

    def create_collection(
        self,
        collection_name: str,
        dimension: int = 768,
        distance: Distance = Distance.COSINE,
        recreate: bool = False,
    ) -> bool:
        """Create a collection if it doesn't exist.

        If the collection already exists with a different vector dimension
        (e.g. after switching embedding models), it is recreated at the new
        dimension so writes don't fail — existing points are dropped and a
        warning is logged.
        """
        client = self._get_client()
        try:
            existing = client.get_collections().collections
            if any(c.name == collection_name for c in existing):
                current_dim = self._collection_dimension(collection_name)
                if recreate or (current_dim is not None and current_dim != dimension):
                    if not recreate:
                        logger.warning(
                            f"Collection {collection_name} has dimension {current_dim} "
                            f"but the embedding provider uses {dimension}; recreating at "
                            f"{dimension} (existing points will be dropped)"
                        )
                    client.delete_collection(collection_name=collection_name)
                else:
                    logger.info(f"Collection {collection_name} already exists")
                    self.ensure_payload_indexes(collection_name)
                    return True

            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=distance,
                ),
                optimizers_config=OptimizersConfigDiff(
                    default_segment_number=2,
                    max_segment_size=20000,
                ),
                hnsw_config=HnswConfigDiff(
                    m=16,
                    ef_construct=100,
                ),
            )
            self.ensure_payload_indexes(collection_name)
            logger.info(f"Created collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    def _collection_missing(self, e: Exception) -> bool:
        """True if the error is a collection-not-found (404)."""
        return isinstance(e, UnexpectedResponse) and e.status_code == 404

    def _ensure_collection(self, collection_name: str, dimension: int = 768) -> None:
        """Ensure a collection exists, creating it on first use (idempotent)."""
        if collection_name in self._ensured_collections:
            return
        try:
            self.create_collection(collection_name, dimension=dimension)
        except Exception as e:
            logger.warning(f"Could not ensure collection {collection_name}: {e}")
        self._ensured_collections.add(collection_name)

    def ensure_payload_indexes(self, collection_name: str | None = None) -> None:
        """Create payload indexes for tenant-filtered fields (idempotent)."""
        client = self._get_client()
        name = collection_name or self._default_collection
        indexes = {
            "organization_id": "keyword",
            "project_id": "keyword",
            "service": "keyword",
            "level": "keyword",
            "source": "keyword",
            "timestamp": "datetime",
        }
        for field, schema in indexes.items():
            try:
                client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_schema=schema,
                )
                logger.info(f"Created payload index on {name}.{field}")
            except Exception as e:
                logger.debug(f"Payload index {name}.{field} already exists or failed: {e}")

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        client = self._get_client()
        try:
            client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False

    def upsert_points(
        self,
        points: list[PointStruct],
        collection_name: str | None = None,
        batch_size: int = 100,
        dimension: int | None = None,
    ) -> int:
        """Upsert points in batches.

        ``dimension`` is the embedding dimension used to create the collection
        if it does not exist yet (or if it must be recreated after a change of
        embedding model).
        """
        client = self._get_client()
        name = collection_name or self._default_collection
        self._ensure_collection(name, dimension=dimension or 768)
        total_upserted = 0

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                client.upsert(collection_name=name, points=batch, wait=True)
                total_upserted += len(batch)
                logger.debug(f"Upserted batch {i // batch_size + 1}: {len(batch)} points")
            except Exception as e:
                logger.error(f"Failed to upsert batch {i // batch_size + 1}: {e}")
                raise

        return total_upserted

    def search(
        self,
        query_vector: list[float],
        collection_name: str | None = None,
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_: Filter | None = None,
        with_vectors: bool = False,
        search_params: SearchParams | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors."""
        client = self._get_client()
        name = collection_name or self._default_collection

        try:
            results = client.query_points(
                collection_name=name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_,
                with_vectors=with_vectors,
                search_params=search_params,
            )
            return [
                VectorSearchResult(
                    id=str(r.id),
                    score=r.score,
                    payload=r.payload or {},
                    vector=r.vector if with_vectors else None,
                )
                for r in results.points
            ]
        except Exception as e:
            if self._collection_missing(e):
                logger.debug(f"Collection {name} not found, returning empty results")
                return []
            logger.error(f"Vector search failed: {e}")
            raise

    def search_batch(
        self,
        query_vectors: list[list[float]],
        collection_name: str | None = None,
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_: Filter | None = None,
    ) -> list[list[VectorSearchResult]]:
        """Batch search for multiple query vectors."""
        client = self._get_client()
        name = collection_name or self._default_collection

        try:
            requests = [
                QueryRequest(
                    vector=qv,
                    limit=limit,
                    score_threshold=score_threshold,
                    filter=filter_,
                    with_payload=True,
                )
                for qv in query_vectors
            ]
            results = client.query_batch_points(collection_name=name, requests=requests)
            return [
                [
                    VectorSearchResult(id=str(r.id), score=r.score, payload=r.payload or {})
                    for r in batch.points
                ]
                for batch in results
            ]
        except Exception as e:
            if self._collection_missing(e):
                logger.debug(f"Collection {name} not found, returning empty results")
                return [[] for _ in query_vectors]
            logger.error(f"Batch vector search failed: {e}")
            raise

    def scroll(
        self,
        collection_name: str | None = None,
        filter_: Filter | None = None,
        limit: int = 100,
        offset: int | None = None,
        with_vectors: bool = False,
    ) -> tuple[list[VectorSearchResult], int | None]:
        """Scroll through points with optional filtering."""
        client = self._get_client()
        name = collection_name or self._default_collection

        try:
            points, next_offset = client.scroll(
                collection_name=name,
                scroll_filter=filter_,
                limit=limit,
                offset=offset,
                with_vectors=with_vectors,
                with_payload=True,
            )
            return (
                [
                    VectorSearchResult(
                        id=str(p.id),
                        score=1.0,
                        payload=p.payload or {},
                        vector=p.vector if with_vectors else None,
                    )
                    for p in points
                ],
                next_offset,
            )
        except Exception as e:
            if self._collection_missing(e):
                logger.debug(f"Collection {name} not found, returning empty results")
                return [], None
            logger.error(f"Scroll failed: {e}")
            raise

    def delete_points(
        self,
        point_ids: list[str | uuid.UUID],
        collection_name: str | None = None,
    ) -> bool:
        """Delete points by IDs."""
        client = self._get_client()
        name = collection_name or self._default_collection
        try:
            client.delete(collection_name=name, points_selector=point_ids)
            return True
        except Exception as e:
            logger.error(f"Failed to delete points: {e}")
            return False

    def count_points(
        self,
        collection_name: str | None = None,
        filter_: Filter | None = None,
    ) -> int:
        """Count points matching filter."""
        client = self._get_client()
        name = collection_name or self._default_collection
        try:
            result = client.count(collection_name=name, count_filter=filter_, exact=True)
            return result.count
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0

    def retrieve(
        self,
        point_ids: list[str],
        collection_name: str | None = None,
    ) -> list[VectorSearchResult]:
        """Retrieve points by ID without searching (for detail views)."""
        client = self._get_client()
        name = collection_name or self._default_collection
        if not point_ids:
            return []
        try:
            points = client.retrieve(
                collection_name=name,
                ids=point_ids,
                with_payload=True,
                with_vectors=False,
            )
            return [
                VectorSearchResult(id=str(p.id), score=1.0, payload=p.payload or {})
                for p in points
            ]
        except Exception as e:
            logger.error(f"Retrieve failed: {e}")
            return []

    def create_tenant_filter(
        self,
        organization_id: str,
        project_id: str | None = None,
        service: str | None = None,
        level: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> Filter:
        """Create a filter for tenant-scoped queries."""
        must = [
            FieldCondition(key="organization_id", match=MatchValue(value=organization_id)),
        ]
        if project_id:
            must.append(FieldCondition(key="project_id", match=MatchValue(value=project_id)))
        if service:
            must.append(FieldCondition(key="service", match=MatchValue(value=service)))
        if level:
            must.append(FieldCondition(key="level", match=MatchValue(value=level)))

        should = []
        if start_time or end_time:
            range_conditions = {}
            if start_time:
                range_conditions["gte"] = start_time
            if end_time:
                range_conditions["lte"] = end_time
            should.append(FieldCondition(key="timestamp", range=Range(**range_conditions)))

        return Filter(must=must, should=should if should else None)


def create_point_from_chunk(chunk, embedding: list[float]) -> PointStruct:
    """Create a Qdrant PointStruct from a Chunk and its embedding."""
    return PointStruct(
        id=chunk.id,
        vector=embedding,
        payload=chunk.to_payload(),
    )


# Singleton instance
_qdrant_service: QdrantService | None = None


def get_qdrant_service() -> QdrantService:
    """Get or create singleton Qdrant service."""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
        try:
            _qdrant_service.ensure_payload_indexes()
        except Exception as e:
            logger.warning(f"Could not ensure Qdrant payload indexes: {e}")
    return _qdrant_service
