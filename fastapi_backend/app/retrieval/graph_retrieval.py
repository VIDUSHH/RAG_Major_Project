"""
Graph retrieval module for combining Neo4j graph queries with vector search.
"""

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.logging import logger
from app.services.graph_service import (
    GraphNode,
    GraphRelationship,
    Neo4jService,
    NodeType,
    RelationshipType,
    get_neo4j_service,
)


class GraphQueryType(StrEnum):
    """Types of graph queries."""

    INCIDENT_GRAPH = "incident_graph"
    SERVICE_DEPENDENCIES = "service_dependencies"
    ERROR_PATTERNS = "error_patterns"
    SIMILAR_INCIDENTS = "similar_incidents"
    ROOT_CAUSE_PATH = "root_cause_path"
    IMPACT_ANALYSIS = "impact_analysis"


@dataclass
class GraphRetrievalResult:
    """Result from graph retrieval."""

    query_type: GraphQueryType
    nodes: list[GraphNode] = field(default_factory=list)
    relationships: list[GraphRelationship] = field(default_factory=list)
    query_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityExtractionResult:
    """Result of entity extraction from query."""

    services: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    incidents: list[str] = field(default_factory=list)
    deployments: list[str] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)
    severity: str | None = None


class GraphRetriever:
    """Retriever for graph-based queries."""

    def __init__(self, neo4j_service: Neo4jService | None = None):
        self.neo4j = neo4j_service or get_neo4j_service()

    def extract_entities(self, query: str) -> EntityExtractionResult:
        """Extract entities from natural language query."""
        result = EntityExtractionResult()
        query_lower = query.lower()

        import re

        # Extract service names (common patterns)
        service_patterns = [
            r"\b(payment|auth|authentication|checkout|billing|notification|user|order|inventory|shipping)\s*(service|api|microservice)?\b",
            r"\b(api[- ]?gateway|load[- ]?balancer|reverse[- ]?proxy)\b",
            r"\b(redis|postgres|postgresql|mysql|mongodb|cassandra|kafka|rabbitmq|elasticsearch)\b",
        ]

        for pattern in service_patterns:
            matches = re.findall(pattern, query_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    service_name = "".join(match).strip()
                else:
                    service_name = match.strip()
                if service_name and service_name not in result.services:
                    result.services.append(service_name)

        # Dynamically match service names/ids that actually exist in the graph
        # (e.g. Hadoop/Windows log components like mapreduce, yarn, hdfs, cbs).
        try:
            with self.neo4j.session() as session:
                rows = session.run(
                    "MATCH (s:Service) RETURN DISTINCT s.name AS name, s.id AS id"
                )
                for row in rows:
                    for candidate in (row.get("name"), row.get("id")):
                        if not candidate or len(candidate) < 3:
                            continue
                        normalized = str(candidate).lower()
                        if normalized.startswith("service-"):
                            normalized = normalized[len("service-") :]
                        if re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", query_lower):
                            if normalized not in result.services:
                                result.services.append(normalized)
        except Exception as e:  # graph may be unavailable; regex results still apply
            logger.debug(f"Dynamic service lookup skipped: {e}")

        # Extract error patterns
        error_keywords = [
            "timeout",
            "connection refused",
            "connection pool",
            "out of memory",
            "null pointer",
            "nullpointer",
            "500",
            "502",
            "503",
            "504",
            "database error",
            "deadlock",
            "lock wait",
            "replication lag",
            "circuit breaker",
            "rate limit",
            "throttl",
            "unavailable",
        ]
        for keyword in error_keywords:
            if keyword in query_lower:
                result.errors.append(keyword)

        # Extract severity
        severity_map = {
            "p1": "P1",
            "p2": "P2",
            "p3": "P3",
            "p4": "P4",
            "critical": "P1",
            "high": "P2",
            "medium": "P3",
            "low": "P4",
        }
        for k, v in severity_map.items():
            if k in query_lower:
                result.severity = v
                break

        # Extract timestamps (simple patterns)
        time_patterns = [
            r"\b(last night|yesterday|today|this morning|this afternoon)\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{1,2}:\d{2})\b",
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, query_lower)
            result.timestamps.extend(matches)

        return result

    def retrieve_incident_graph(
        self,
        incident_id: str,
        include_logs: bool = True,
        include_fixes: bool = True,
        include_lessons: bool = True,
    ) -> GraphRetrievalResult:
        """Retrieve full incident graph."""
        start_time = time.time()
        result = self.neo4j.find_incident_graph(
            incident_id=incident_id,
            include_logs=include_logs,
            include_fixes=include_fixes,
            include_lessons=include_lessons,
        )
        return GraphRetrievalResult(
            query_type=GraphQueryType.INCIDENT_GRAPH,
            nodes=result.nodes,
            relationships=result.relationships,
            query_time_ms=(time.time() - start_time) * 1000,
            metadata={"incident_id": incident_id, "records": result.records},
        )

    def retrieve_service_dependencies(
        self,
        service_name: str,
        direction: str = "both",
    ) -> GraphRetrievalResult:
        """Retrieve service dependencies."""
        start_time = time.time()
        nodes = []

        if direction in ("both", "downstream"):
            deps = self.neo4j.get_service_dependencies(service_name)
            nodes.extend(deps)

        if direction in ("both", "upstream"):
            # Find services that depend on this service
            query = """
            MATCH (s:Service {name: $service_name})<-[:DEPENDS_ON|CALLS|USES]-(caller:Service)
            RETURN DISTINCT caller
            """
            with self.neo4j.session() as session:
                result = session.run(query, {"service_name": service_name})
                for record in result:
                    caller = record["caller"]
                    nodes.append(
                        GraphNode(
                            id=caller["id"],
                            type=NodeType.SERVICE,
                            properties=dict(caller),
                            labels=list(caller.labels),
                        )
                    )

        return GraphRetrievalResult(
            query_type=GraphQueryType.SERVICE_DEPENDENCIES,
            nodes=nodes,
            query_time_ms=(time.time() - start_time) * 1000,
            metadata={"service_name": service_name, "direction": direction},
        )

    def retrieve_error_patterns(
        self,
        service_name: str,
        time_window_hours: int = 24,
        limit: int = 20,
    ) -> GraphRetrievalResult:
        """Retrieve recent error patterns for a service."""
        start_time = time.time()
        errors = self.neo4j.get_error_patterns(
            service_name=service_name,
            time_window_hours=time_window_hours,
            limit=limit,
        )
        return GraphRetrievalResult(
            query_type=GraphQueryType.ERROR_PATTERNS,
            nodes=errors,
            query_time_ms=(time.time() - start_time) * 1000,
            metadata={"service_name": service_name, "time_window_hours": time_window_hours},
        )

    def retrieve_similar_incidents(
        self,
        service_name: str,
        error_message: str | None = None,
        limit: int = 10,
    ) -> GraphRetrievalResult:
        """Retrieve similar historical incidents."""
        start_time = time.time()
        incidents = self.neo4j.find_similar_incidents(
            service_name=service_name,
            error_message=error_message,
            limit=limit,
        )
        return GraphRetrievalResult(
            query_type=GraphQueryType.SIMILAR_INCIDENTS,
            nodes=incidents,
            query_time_ms=(time.time() - start_time) * 1000,
            metadata={"service_name": service_name, "error_message": error_message},
        )

    def retrieve_root_cause_path(
        self,
        service_name: str,
        error_message: str | None = None,
        max_depth: int = 3,
    ) -> GraphRetrievalResult:
        """Find potential root cause paths using graph traversal."""
        start_time = time.time()

        query = """
        MATCH (s:Service {name: $service_name})
        CALL apoc.path.expandConfig(s, {
            relationshipFilter: 'DEPENDS_ON|CALLS|USES|TRIGGERED|CAUSED_BY',
            minLevel: 1,
            maxLevel: $max_depth,
            labelFilter: 'Service|Error|Component|Deployment',
            uniqueness: 'NODE_GLOBAL'
        }) YIELD path
        RETURN path
        LIMIT 50
        """

        nodes = []
        relationships = []

        with self.neo4j.session() as session:
            try:
                result = session.run(
                    query,
                    {
                        "service_name": service_name,
                        "max_depth": max_depth,
                    },
                )
                for record in result:
                    path = record["path"]
                    for node in path.nodes:
                        nodes.append(
                            GraphNode(
                                id=node["id"],
                                type=NodeType(node.labels[0]) if node.labels else NodeType.SERVICE,
                                properties=dict(node),
                                labels=list(node.labels),
                            )
                        )
                    for rel in path.relationships:
                        relationships.append(
                            GraphRelationship(
                                source_id=rel.start_node["id"],
                                target_id=rel.end_node["id"],
                                type=RelationshipType(rel.type)
                                if rel.type in [rt.value for rt in RelationshipType]
                                else RelationshipType.RELATED_TO,
                                properties=dict(rel),
                            )
                        )
            except Exception as e:
                logger.warning(f"APOC path expansion failed, using fallback: {e}")
                # Fallback
                fallback_query = """
                MATCH (s:Service {name: $service_name})-[r:DEPENDS_ON|CALLS|USES*1..3]-(related)
                WHERE related:Service OR related:Error OR related:Component
                RETURN DISTINCT related, r
                """
                result = session.run(fallback_query, {"service_name": service_name})
                for record in result:
                    related = record["related"]
                    nodes.append(
                        GraphNode(
                            id=related["id"],
                            type=NodeType(related.labels[0])
                            if related.labels
                            else NodeType.SERVICE,
                            properties=dict(related),
                            labels=list(related.labels),
                        )
                    )

        return GraphRetrievalResult(
            query_type=GraphQueryType.ROOT_CAUSE_PATH,
            nodes=nodes,
            relationships=relationships,
            query_time_ms=(time.time() - start_time) * 1000,
            metadata={
                "service_name": service_name,
                "error_message": error_message,
                "max_depth": max_depth,
            },
        )

    def retrieve_impact_analysis(
        self,
        service_name: str,
    ) -> GraphRetrievalResult:
        """Analyze impact of a service failure."""
        start_time = time.time()

        query = """
        MATCH (s:Service {name: $service_name})<-[:DEPENDS_ON|CALLS|USES*]-(affected:Service)
        OPTIONAL MATCH (affected)-[:HAS_INCIDENT]->(i:Incident)
        RETURN affected, collect(i) as incidents
        """

        nodes = []
        with self.neo4j.session() as session:
            result = session.run(query, {"service_name": service_name})
            for record in result:
                affected = record["affected"]
                nodes.append(
                    GraphNode(
                        id=affected["id"],
                        type=NodeType.SERVICE,
                        properties=dict(affected),
                        labels=list(affected.labels),
                    )
                )

        return GraphRetrievalResult(
            query_type=GraphQueryType.IMPACT_ANALYSIS,
            nodes=nodes,
            query_time_ms=(time.time() - start_time) * 1000,
            metadata={"service_name": service_name, "affected_count": len(nodes)},
        )

    def retrieve_service_context(
        self,
        service_name: str,
        limit: int = 8,
    ) -> GraphRetrievalResult:
        """Return a service node plus its recent warning/error log entries.

        Unlike ``retrieve_error_patterns`` this is not time-windowed, so it still
        surfaces evidence for historical datasets whose timestamps are old.
        """
        start_time = time.time()
        query = """
        MATCH (s:Service)
        WHERE toLower(coalesce(s.name, '')) = toLower($service_name)
           OR toLower(s.id) = toLower($service_name)
        OPTIONAL MATCH (s)-[:PRODUCED_LOG]->(le:LogEntry)
        RETURN s AS service, collect(le) AS logs
        """

        nodes: list[GraphNode] = []
        relationships: list[GraphRelationship] = []
        error_levels = {"ERROR", "CRITICAL", "FATAL", "WARN", "WARNING"}

        with self.neo4j.session() as session:
            for record in session.run(query, {"service_name": service_name}):
                service = record["service"]
                if service is None:
                    continue
                nodes.append(
                    GraphNode(
                        id=service["id"],
                        type=NodeType.SERVICE,
                        properties=dict(service),
                        labels=list(service.labels),
                    )
                )
                log_entries = [le for le in (record["logs"] or []) if le is not None]
                error_entries = [
                    le
                    for le in log_entries
                    if str(le.get("level") or "").upper() in error_levels
                ]
                selected = error_entries if error_entries else log_entries
                selected.sort(
                    key=lambda le: str(le.get("timestamp") or ""), reverse=True
                )
                for le in selected[:limit]:
                    nodes.append(
                        GraphNode(
                            id=le["id"],
                            type=NodeType.LOG_ENTRY,
                            properties=dict(le),
                            labels=list(le.labels),
                        )
                    )
                    relationships.append(
                        GraphRelationship(
                            source_id=service["id"],
                            target_id=le["id"],
                            type=RelationshipType.PRODUCED_LOG,
                            properties={},
                        )
                    )

        return GraphRetrievalResult(
            query_type=GraphQueryType.ERROR_PATTERNS,
            nodes=nodes,
            relationships=relationships,
            query_time_ms=(time.time() - start_time) * 1000,
            metadata={"service_name": service_name, "log_limit": limit},
        )

    def retrieve_by_query(self, query: str) -> list[GraphRetrievalResult]:
        """Automatically determine query type and retrieve relevant graph data."""
        entities = self.extract_entities(query)
        results: list[GraphRetrievalResult] = []

        def _safe(fn, *args, **kwargs) -> GraphRetrievalResult | None:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger.debug(f"Graph query {getattr(fn, '__name__', fn)} skipped: {e}")
                return None

        # If specific services mentioned, pull their context/errors/dependencies.
        for service in entities.services:
            context = _safe(self.retrieve_service_context, service)
            if context and context.nodes:
                results.append(context)

            deps = _safe(self.retrieve_service_dependencies, service)
            if deps and deps.nodes:
                results.append(deps)

            errors = _safe(self.retrieve_error_patterns, service)
            if errors and errors.nodes:
                results.append(errors)

            if entities.errors:
                similar = _safe(
                    self.retrieve_similar_incidents, service, entities.errors[0]
                )
                if similar and similar.nodes:
                    results.append(similar)

            if any(k in query.lower() for k in ("why", "root cause", "cause")):
                root_cause = _safe(
                    self.retrieve_root_cause_path,
                    service,
                    entities.errors[0] if entities.errors else None,
                )
                if root_cause and root_cause.nodes:
                    results.append(root_cause)

        # If incident ID mentioned, get incident graph
        for incident in entities.incidents:
            incident_graph = _safe(self.retrieve_incident_graph, incident)
            if incident_graph and incident_graph.nodes:
                results.append(incident_graph)

        return results


_graph_retriever: GraphRetriever | None = None


def get_graph_retriever() -> GraphRetriever:
    """Get or create singleton graph retriever."""
    global _graph_retriever
    if _graph_retriever is None:
        _graph_retriever = GraphRetriever()
    return _graph_retriever
