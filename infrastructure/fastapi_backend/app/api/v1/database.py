"""
Database inspection API endpoints for viewing stored data.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.core.dependencies import TenantDep
from app.core.logging import logger
from app.services.activity_service import recent_activity
from app.services.graph_service import get_neo4j_service
from app.services.vector_service import get_qdrant_service

router = APIRouter()


# Vector Database Endpoints


@router.get("/vectors/stats", summary="Get vector database statistics")
def get_vector_stats(ctx: TenantDep):
    """Get Qdrant collection statistics."""
    try:
        qdrant = get_qdrant_service()
        stats = qdrant.get_collection_stats()
        return {
            "collection": stats.name,
            "vectors_count": stats.vectors_count,
            "points_count": stats.points_count,
            "segments_count": stats.segments_count,
            "status": stats.status,
            "optimizer_status": stats.optimizer_status,
            "dimension": stats.dimension,
            "distance": stats.distance,
        }
    except Exception as e:
        logger.error(f"Failed to get vector stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vector stats: {str(e)}",
        ) from e


@router.get("/vectors/summary", summary="Documents summary with chunking strategies")
def get_vector_summary(
    ctx: TenantDep,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: str | None = Query(None),
):
    """Group stored chunks by source document, showing per-document chunk counts
    and the chunking strategy used to ingest each one."""
    try:
        qdrant = get_qdrant_service()
        filter_dict = {"organization_id": ctx.organization_id, "service": service}
        qdrant_filter = qdrant.create_tenant_filter(
            **{k: v for k, v in filter_dict.items() if v}
        )

        docs: dict[str, dict] = {}
        next_offset: int | None = 0
        scanned = 0
        while next_offset is not None and scanned < 20000:
            points, next_offset = qdrant.scroll(
                filter_=qdrant_filter, limit=1000, offset=next_offset
            )
            for p in points:
                scanned += 1
                payload = p.payload or {}
                source = payload.get("source") or "unknown"
                entry = docs.setdefault(
                    source,
                    {
                        "source": source,
                        "chunks": 0,
                        "strategies": {},
                        "service": payload.get("service"),
                        "source_type": payload.get("source_type"),
                        "first_timestamp": payload.get("timestamp"),
                        "last_timestamp": payload.get("timestamp"),
                        "sample_text": payload.get("text", "")[:120],
                    },
                )
                entry["chunks"] += 1
                strategy = payload.get("chunking_strategy") or "unknown"
                entry["strategies"][strategy] = entry["strategies"].get(strategy, 0) + 1
                ts = payload.get("timestamp")
                if ts:
                    if entry["first_timestamp"] is None or ts < entry["first_timestamp"]:
                        entry["first_timestamp"] = ts
                    if entry["last_timestamp"] is None or ts > entry["last_timestamp"]:
                        entry["last_timestamp"] = ts

        all_docs = list(docs.values())
        all_docs.sort(key=lambda d: d["first_timestamp"] or "", reverse=True)

        total_chunks = sum(d["chunks"] for d in all_docs)
        return {
            "documents_count": len(all_docs),
            "total_chunks": total_chunks,
            "documents": all_docs[offset : offset + limit],
            "offset": offset,
            "limit": limit,
            "scanned_points": scanned,
        }
    except Exception as e:
        logger.error(f"Failed to get vector summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vector summary: {str(e)}",
        ) from e


@router.get("/vectors/collections", summary="List all collections")
def list_collections(ctx: TenantDep):
    """List all Qdrant collections."""
    try:
        qdrant = get_qdrant_service()
        collections = qdrant.list_collections()
        return {"collections": collections}
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}",
        ) from e


@router.get("/vectors/search", summary="Search vectors directly")
def search_vectors(
    ctx: TenantDep,
    query: str = Query(..., description="Search query text"),
    limit: int = Query(10, ge=1, le=100),
    score_threshold: float = Query(0.0, ge=0.0, le=1.0),
    service: str | None = Query(None, description="Filter by service"),
    level: str | None = Query(None, description="Filter by log level"),
):
    """Direct vector search with optional filters."""
    try:
        from app.embeddings.provider import get_embedding_provider

        embedding_provider = get_embedding_provider()
        query_vector = embedding_provider.embed_query(query)

        qdrant = get_qdrant_service()
        filter_dict = {
            "organization_id": ctx.organization_id,
            "service": service,
            "level": level,
        }
        qdrant_filter = qdrant.create_tenant_filter(**{k: v for k, v in filter_dict.items() if v})

        results = qdrant.search(
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            filter_=qdrant_filter,
        )

        return {
            "query": query,
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "text": r.payload.get("text", "")[:500],
                    "source": r.payload.get("source"),
                    "service": r.payload.get("service"),
                    "timestamp": r.payload.get("timestamp"),
                    "metadata": r.payload.get("metadata"),
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}",
        ) from e


@router.get("/vectors/documents", summary="List documents in vector DB")
def list_vector_documents(
    ctx: TenantDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: str | None = Query(None),
):
    """Scroll through stored documents in vector DB."""
    try:
        qdrant = get_qdrant_service()
        filter_dict = {"organization_id": ctx.organization_id, "service": service}
        qdrant_filter = qdrant.create_tenant_filter(**{k: v for k, v in filter_dict.items() if v})

        points, next_offset = qdrant.scroll(filter_=qdrant_filter, limit=limit, offset=offset)

        return {
            "documents": [
                {
                    "id": p.id,
                    "text": p.payload.get("text", "")[:300],
                    "source": p.payload.get("source"),
                    "service": p.payload.get("service"),
                    "timestamp": p.payload.get("timestamp"),
                    "chunk_type": p.payload.get("metadata", {}).get("chunk_type"),
                }
                for p in points
            ],
            "next_offset": next_offset,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Failed to list vector documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        ) from e


@router.get("/vectors/document/{doc_id}", summary="Get document by ID")
def get_vector_document(
    doc_id: str,
    ctx: TenantDep,
):
    """Get a specific document from vector DB."""
    try:
        qdrant = get_qdrant_service()
        points = qdrant.retrieve([doc_id])

        if not points:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        p = points[0]
        payload = p.payload or {}
        return {
            "id": p.id,
            "text": payload.get("text", ""),
            "source": payload.get("source"),
            "source_type": payload.get("source_type"),
            "service": payload.get("service"),
            "timestamp": payload.get("timestamp"),
            "chunk_index": payload.get("chunk_index"),
            "total_chunks": payload.get("total_chunks"),
            "chunking_strategy": payload.get("chunking_strategy"),
            "metadata": payload.get("metadata"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}",
        ) from e


# Graph Database Endpoints


@router.get("/graph/stats", summary="Get graph database statistics")
def get_graph_stats(ctx: TenantDep):
    """Get Neo4j graph statistics."""
    try:
        neo4j = get_neo4j_service()
        stats = neo4j.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph stats: {str(e)}",
        ) from e


@router.get("/graph/nodes", summary="List graph nodes")
def list_graph_nodes(
    ctx: TenantDep,
    node_type: str | None = Query(None, description="Filter by node type"),
    limit: int = Query(100, ge=1, le=500),
):
    """List nodes in Neo4j."""
    try:
        neo4j = get_neo4j_service()

        type_filter = f":{node_type}" if node_type else ""
        query = f"MATCH (n{type_filter}) WHERE n.organization_id = $org_id RETURN n LIMIT $limit"

        with neo4j.session() as session:
            result = session.run(query, {"org_id": ctx.organization_id, "limit": limit})
            nodes = []
            for record in result:
                node = record["n"]
                nodes.append(
                    {
                        "id": node["id"],
                        "type": list(node.labels)[0] if node.labels else "Unknown",
                        "properties": dict(node),
                    }
                )

        return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        logger.error(f"Failed to list graph nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list nodes: {str(e)}",
        ) from e


@router.get("/graph/relationships", summary="List graph relationships")
def list_graph_relationships(
    ctx: TenantDep,
    rel_type: str | None = Query(None, description="Filter by relationship type"),
    limit: int = Query(100, ge=1, le=500),
):
    """List relationships in Neo4j."""
    try:
        neo4j = get_neo4j_service()

        type_filter = f":{rel_type}" if rel_type else ""
        query = f"""
        MATCH (a)-[r{type_filter}]->(b)
        WHERE a.organization_id = $org_id OR b.organization_id = $org_id
        RETURN a.id as source, b.id as target, type(r) as type, properties(r) as props
        LIMIT $limit
        """

        with neo4j.session() as session:
            result = session.run(query, {"org_id": ctx.organization_id, "limit": limit})
            relationships = []
            for record in result:
                relationships.append(
                    {
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["type"],
                        "properties": record["props"],
                    }
                )

        return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        logger.error(f"Failed to list graph relationships: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list relationships: {str(e)}",
        ) from e


@router.get("/graph/service/{service_name}", summary="Get service graph")
def get_service_graph(
    ctx: TenantDep,
    service_name: str,
    depth: int = Query(2, ge=1, le=4),
):
    """Get service dependency graph (nodes + relationships up to ``depth``)."""
    try:
        neo4j = get_neo4j_service()
        depth = int(depth)

        def _node_entry(node) -> dict:
            props = dict(node)
            return {
                "id": props.get("id") or node.element_id,
                "type": list(node.labels)[0] if node.labels else "Unknown",
                "properties": props,
            }

        # Primary: APOC subgraph (nodes) starting from the service.
        apoc_query = """
        MATCH (s:Service {name: $service_name})
        CALL apoc.path.subgraphNodes(s, {
            relationshipFilter: 'DEPENDS_ON|CALLS|USES|PRODUCED_LOG',
            minLevel: 1,
            maxLevel: $depth,
            labelFilter: 'Service|Error|LogEntry|Component'
        }) YIELD node
        RETURN s, collect(DISTINCT node) AS nodes
        """
        # Fallback without APOC: variable-length pattern (depth interpolated as a
        # validated int because Cypher does not allow parameterised lengths).
        fallback_query = f"""
        MATCH (start:Service {{name: $service_name}})
        OPTIONAL MATCH (start)-[:DEPENDS_ON|CALLS|USES|PRODUCED_LOG*1..{depth}]-(related)
        RETURN start, collect(DISTINCT related) AS related
        """

        all_nodes: list = []

        with neo4j.session() as session:
            try:
                records = list(
                    session.run(apoc_query, {"service_name": service_name, "depth": depth})
                )
            except Exception as e:
                logger.warning(f"APOC subgraph unavailable, falling back to plain Cypher: {e}")
                records = []

            if records:
                for row in records:
                    if row.get("s"):
                        all_nodes.append(row.get("s"))
                    all_nodes.extend(row.get("nodes") or [])
            else:
                row = session.run(fallback_query, {"service_name": service_name}).single()
                if row and row.get("start"):
                    all_nodes.append(row.get("start"))
                    all_nodes.extend(row.get("related") or [])

            nodes: dict[str, dict] = {}
            for node in all_nodes:
                if node is None:
                    continue
                entry = _node_entry(node)
                nodes[entry["id"]] = entry

            relationships = []
            if nodes:
                edge_rows = session.run(
                    """
                    MATCH (a)-[r:DEPENDS_ON|CALLS|USES|PRODUCED_LOG]-(b)
                    WHERE a.id IN $ids AND b.id IN $ids
                    RETURN a.id AS source, b.id AS target, type(r) AS type
                    """,
                    {"ids": list(nodes.keys())},
                )
                for row in edge_rows:
                    relationships.append(
                        {
                            "type": row["type"],
                            "source": row["source"],
                            "target": row["target"],
                        }
                    )

        return {
            "service": service_name,
            "nodes": list(nodes.values()),
            "relationships": relationships,
            "count": len(nodes),
        }
    except Exception as e:
        logger.error(f"Failed to get service graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service graph: {str(e)}",
        ) from e


@router.get("/graph/incident/{incident_id}", summary="Get incident graph")
def get_incident_graph(
    ctx: TenantDep,
    incident_id: str,
    include_logs: bool = Query(True),
    include_fixes: bool = Query(True),
    include_lessons: bool = Query(True),
):
    """Get full incident graph with related entities."""
    try:
        neo4j = get_neo4j_service()
        result = neo4j.find_incident_graph(
            incident_id=incident_id,
            include_logs=include_logs,
            include_fixes=include_fixes,
            include_lessons=include_lessons,
        )

        return {
            "incident_id": incident_id,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "properties": n.properties,
                }
                for n in result.nodes
            ],
            "relationships": [
                {
                    "source": r.source_id,
                    "target": r.target_id,
                    "type": r.type.value,
                    "properties": r.properties,
                }
                for r in result.relationships
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get incident graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get incident graph: {str(e)}",
        ) from e


@router.get("/graph/errors/{service_name}", summary="Get error patterns for service")
def get_service_errors(
    ctx: TenantDep,
    service_name: str,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
):
    """Get recent error patterns for a service."""
    try:
        neo4j = get_neo4j_service()
        errors = neo4j.get_error_patterns(
            service_name=service_name,
            time_window_hours=hours,
            limit=limit,
        )

        return {
            "service": service_name,
            "time_window_hours": hours,
            "errors": [
                {
                    "id": e.id,
                    "properties": e.properties,
                }
                for e in errors
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get service errors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get errors: {str(e)}",
        ) from e


# Health/Status Endpoint


@router.get("/system/status", summary="Get overall system status")
def get_system_status(ctx: TenantDep):
    """Get status of all database connections."""
    try:
        qdrant = get_qdrant_service()
        neo4j = get_neo4j_service()

        qdrant_healthy = qdrant.health_check()
        neo4j_healthy = neo4j.health_check()

        qdrant_stats = qdrant.get_collection_stats() if qdrant_healthy else None
        neo4j_stats = neo4j.get_stats() if neo4j_healthy else None

        return {
            "qdrant": {
                "healthy": qdrant_healthy,
                "stats": {
                    "vectors_count": qdrant_stats.vectors_count if qdrant_stats else 0,
                    "points_count": qdrant_stats.points_count if qdrant_stats else 0,
                }
                if qdrant_stats
                else None,
            },
            "neo4j": {
                "healthy": neo4j_healthy,
                "stats": neo4j_stats,
            },
            "overall_healthy": qdrant_healthy and neo4j_healthy,
            "embedding": {
                "provider": settings.EMBEDDING_PROVIDER,
                "model": settings.EMBEDDING_MODEL,
                "dimension": settings.EMBEDDING_DIMENSION,
            },
            "llm": {
                "provider": settings.LLM_PROVIDER,
                "model": settings.LLM_MODEL,
            },
            "project": settings.PROJECT_NAME,
        }
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}",
        ) from e


# Recent Activity


@router.get("/activity/recent", summary="Recent activity feed")
def get_recent_activity(
    ctx: TenantDep,
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
):
    """Return the most recent user actions (ingestion, analysis, etc.)."""
    try:
        return {
            "activities": recent_activity(
                org_id=ctx.organization_id,
                limit=limit,
                event_type=event_type,
            )
        }
    except Exception as e:
        logger.error(f"Failed to get activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activity: {str(e)}",
        ) from e
