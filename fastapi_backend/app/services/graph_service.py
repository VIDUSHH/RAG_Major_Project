"""
Neo4j graph database service for the RAG pipeline.

Provides high-level operations for graph schema management, node/relationship
creation, and graph queries for incident analysis.
"""

import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from neo4j import Driver, GraphDatabase, Result, Session
from neo4j.exceptions import Neo4jError

from app.core.config import settings
from app.core.logging import logger


class NodeType(StrEnum):
    """Node types in the knowledge graph."""

    ORGANIZATION = "Organization"
    PROJECT = "Project"
    SERVICE = "Service"
    INCIDENT = "Incident"
    POSTMORTEM = "Postmortem"
    LOG_ENTRY = "LogEntry"
    ERROR = "Error"
    COMPONENT = "Component"
    DEPLOYMENT = "Deployment"
    TEAM = "Team"
    FIX = "Fix"
    LESSON = "Lesson"


class RelationshipType(StrEnum):
    """Relationship types in the knowledge graph."""

    HAS_PROJECT = "HAS_PROJECT"
    HAS_SERVICE = "HAS_SERVICE"
    PRODUCED_LOG = "PRODUCED_LOG"
    CAUSED_BY = "CAUSED_BY"
    AFFECTED = "AFFECTED"
    RELATED_TO = "RELATED_TO"
    FIXED_BY = "FIXED_BY"
    RESOLVED_BY = "RESOLVED_BY"
    LEARNED = "LEARNED"
    DEPENDS_ON = "DEPENDS_ON"
    CALLS = "CALLS"
    DEPLOYED_TO = "DEPLOYED_TO"
    OCCURRED_IN = "OCCURRED_IN"
    PRECEDED_BY = "PRECEDED_BY"
    TRIGGERED = "TRIGGERED"
    USES = "USES"
    OWNED_BY = "OWNED_BY"
    MONITORS = "MONITORS"


@dataclass
class GraphNode:
    """Represents a graph node."""

    id: str
    type: NodeType
    properties: dict[str, Any] = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.type.value not in self.labels:
            self.labels.insert(0, self.type.value)


@dataclass
class GraphRelationship:
    """Represents a graph relationship."""

    source_id: str
    target_id: str
    type: RelationshipType
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphQueryResult:
    """Result from a graph query."""

    nodes: list[GraphNode] = field(default_factory=list)
    relationships: list[GraphRelationship] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)


class Neo4jService:
    """Service for interacting with Neo4j graph database."""

    def __init__(self):
        self._driver: Driver | None = None

    def _get_driver(self) -> Driver:
        """Get or create Neo4j driver."""
        if self._driver is None:
            uri = f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}"
            logger.info(f"Connecting to Neo4j at {uri}")
            self._driver = GraphDatabase.driver(
                uri,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
            )
        return self._driver

    def close(self):
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def health_check(self) -> bool:
        """Check if Neo4j is accessible."""
        try:
            driver = self._get_driver()
            driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False

    @contextmanager
    def session(self) -> Session:
        """Get a Neo4j session."""
        driver = self._get_driver()
        session = driver.session()
        try:
            yield session
        finally:
            session.close()

    def run_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Result:
        """Execute a Cypher query."""
        with self.session() as session:
            return session.run(query, parameters or {})

    def initialize_schema(self):
        """Create constraints and indexes for the graph schema."""
        constraints = [
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.ORGANIZATION}) REQUIRE n.id IS UNIQUE",  # noqa: E501
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.PROJECT}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.SERVICE}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.INCIDENT}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.POSTMORTEM}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.LOG_ENTRY}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.ERROR}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.COMPONENT}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.DEPLOYMENT}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.TEAM}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.FIX}) REQUIRE n.id IS UNIQUE",
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{NodeType.LESSON}) REQUIRE n.id IS UNIQUE",
        ]

        indexes = [
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.LOG_ENTRY}) ON (n.timestamp)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.LOG_ENTRY}) ON (n.service)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.LOG_ENTRY}) ON (n.level)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.LOG_ENTRY}) ON (n.organization_id)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.INCIDENT}) ON (n.severity)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.INCIDENT}) ON (n.status)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.INCIDENT}) ON (n.started_at)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.SERVICE}) ON (n.name)",
            f"CREATE INDEX IF NOT EXISTS FOR (n:{NodeType.ERROR}) ON (n.message)",
        ]

        with self.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.debug(f"Created constraint: {constraint}")
                except Neo4jError as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Constraint creation warning: {e}")

            for index in indexes:
                try:
                    session.run(index)
                    logger.debug(f"Created index: {index}")
                except Neo4jError as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Index creation warning: {e}")

    def merge_node(self, node: GraphNode) -> str:
        """Merge a node (create if not exists)."""
        labels_str = ":".join(node.labels)
        props = {**node.properties, "id": node.id}

        query = f"""
        MERGE (n:{labels_str} {{id: $id}})
        SET n += $props
        RETURN n.id as id
        """

        with self.session() as session:
            result = session.run(query, {"id": node.id, "props": props})
            return result.single()["id"]

    def create_node(self, node: GraphNode) -> str:
        """Create a new node (fails if exists)."""
        labels_str = ":".join(node.labels)
        props = dict(node.properties)
        props["id"] = node.id
        prop_str = ", ".join([f"{k}: ${k}" for k in props.keys()])

        query = f"""
        CREATE (n:{labels_str} {{{prop_str}}})
        RETURN n.id as id
        """

        with self.session() as session:
            result = session.run(query, props)
            return result.single()["id"]

    def merge_relationship(self, rel: GraphRelationship) -> bool:
        """Merge a relationship between two nodes."""
        query = f"""
        MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
        MERGE (a)-[r:{rel.type.value}]->(b)
        SET r += $props
        RETURN r
        """

        params = {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "props": rel.properties,
        }

        with self.session() as session:
            try:
                session.run(query, params)
                return True
            except Neo4jError as e:
                logger.error(f"Failed to merge relationship: {e}")
                return False

    def find_related_services(
        self,
        service_id: str,
        depth: int = 2,
        relationship_types: list[RelationshipType] | None = None,
    ) -> list[GraphNode]:
        """Find services related to a given service."""
        rel_filter = ""
        if relationship_types:
            types = "|".join([rt.value for rt in relationship_types])
            rel_filter = f":{types}"

        query = f"""
        MATCH (s:Service {{id: $service_id}})
        CALL apoc.path.subgraphNodes(s, {{
            relationshipFilter: '{rel_filter}',
            minLevel: 1,
            maxLevel: $depth,
            labelFilter: 'Service'
        }}) YIELD node
        RETURN node
        """

        with self.session() as session:
            try:
                result = session.run(query, {"service_id": service_id, "depth": depth})
                nodes = []
                for record in result:
                    node = record["node"]
                    nodes.append(
                        GraphNode(
                            id=node["id"],
                            type=NodeType.SERVICE,
                            properties=dict(node),
                            labels=list(node.labels),
                        )
                    )
                return nodes
            except Neo4jError:
                # Fallback without APOC
                fallback_query = f"""
                MATCH (s:Service {{id: $service_id}})-[r{rel_filter}*1..{depth}]-(related:Service)
                RETURN DISTINCT related
                """
                result = session.run(fallback_query, {"service_id": service_id})
                nodes = []
                for record in result:
                    node = record["related"]
                    nodes.append(
                        GraphNode(
                            id=node["id"],
                            type=NodeType.SERVICE,
                            properties=dict(node),
                            labels=list(node.labels),
                        )
                    )
                return nodes

    def find_incident_graph(
        self,
        incident_id: str,
        include_logs: bool = True,
        include_fixes: bool = True,
        include_lessons: bool = True,
    ) -> GraphQueryResult:
        """Get the full graph around an incident."""
        query_parts = [
            "MATCH (i:Incident {id: $incident_id})",
            "OPTIONAL MATCH (i)-[:AFFECTED]->(s:Service)",
            "OPTIONAL MATCH (i)-[:CAUSED_BY]->(e:Error)",
            "OPTIONAL MATCH (i)-[:RELATED_TO]->(prev:Incident)",
        ]

        if include_fixes:
            query_parts.append("OPTIONAL MATCH (i)-[:FIXED_BY|RESOLVED_BY]->(f:Fix)")

        if include_lessons:
            query_parts.append("OPTIONAL MATCH (i)-[:LEARNED]->(l:Lesson)")

        if include_logs:
            query_parts.append("OPTIONAL MATCH (i)-[:HAS_LOG]->(le:LogEntry)")

        query_parts.append("""
        RETURN i, collect(DISTINCT s) as services, collect(DISTINCT e) as errors,
               collect(DISTINCT prev) as related_incidents,
               collect(DISTINCT f) as fixes, collect(DISTINCT l) as lessons,
               collect(DISTINCT le) as logs
        """)

        query = "\n".join(query_parts)

        with self.session() as session:
            result = session.run(query, {"incident_id": incident_id})
            record = result.single()

            if not record:
                return GraphQueryResult()

            nodes = []
            relationships = []

            # Add incident
            incident = record["i"]
            if incident:
                nodes.append(
                    GraphNode(
                        id=incident["id"],
                        type=NodeType.INCIDENT,
                        properties=dict(incident),
                        labels=list(incident.labels),
                    )
                )

            # Add related entities
            for entities, node_type in [
                (record["services"], NodeType.SERVICE),
                (record["errors"], NodeType.ERROR),
                (record["related_incidents"], NodeType.INCIDENT),
                (record["fixes"], NodeType.FIX),
                (record["lessons"], NodeType.LESSON),
                (record["logs"], NodeType.LOG_ENTRY),
            ]:
                for entity in entities:
                    if entity:
                        nodes.append(
                            GraphNode(
                                id=entity["id"],
                                type=node_type,
                                properties=dict(entity),
                                labels=list(entity.labels),
                            )
                        )

            return GraphQueryResult(
                nodes=nodes, relationships=relationships, records=[dict(record)]
            )

    def find_similar_incidents(
        self,
        service_name: str,
        error_message: str | None = None,
        limit: int = 10,
    ) -> list[GraphNode]:
        """Find incidents similar to a given service/error."""
        query = """
        MATCH (i:Incident)-[:AFFECTED]->(s:Service {name: $service_name})
        """
        params = {"service_name": service_name, "limit": limit}

        if error_message:
            query += """
            OPTIONAL MATCH (i)-[:CAUSED_BY]->(e:Error)
            WHERE e.message CONTAINS $error_message
            """
            params["error_message"] = error_message

        query += """
        RETURN i, s, e
        ORDER BY i.started_at DESC
        LIMIT $limit
        """

        with self.session() as session:
            result = session.run(query, params)
            incidents = []
            for record in result:
                incident = record["i"]
                if incident:
                    incidents.append(
                        GraphNode(
                            id=incident["id"],
                            type=NodeType.INCIDENT,
                            properties=dict(incident),
                            labels=list(incident.labels),
                        )
                    )
            return incidents

    def get_service_dependencies(self, service_name: str) -> list[GraphNode]:
        """Get all dependencies for a service."""
        query = """
        MATCH (s:Service {name: $service_name})-[:DEPENDS_ON|CALLS|USES*]->(dep:Service)
        RETURN DISTINCT dep
        """

        with self.session() as session:
            result = session.run(query, {"service_name": service_name})
            deps = []
            for record in result:
                dep = record["dep"]
                deps.append(
                    GraphNode(
                        id=dep["id"],
                        type=NodeType.SERVICE,
                        properties=dict(dep),
                        labels=list(dep.labels),
                    )
                )
            return deps

    def get_error_patterns(
        self,
        service_name: str,
        time_window_hours: int = 24,
        limit: int = 20,
    ) -> list[GraphNode]:
        """Get recent error patterns for a service."""
        query = """
        MATCH (s:Service {name: $service_name})-[:PRODUCED_LOG]->(le:LogEntry)
        WHERE le.level IN ['ERROR', 'CRITICAL', 'FATAL']
          AND le.timestamp >= datetime() - duration({hours: $hours})
        RETURN le
        ORDER BY le.timestamp DESC
        LIMIT $limit
        """

        with self.session() as session:
            result = session.run(
                query,
                {
                    "service_name": service_name,
                    "hours": time_window_hours,
                    "limit": limit,
                },
            )
            errors = []
            for record in result:
                le = record["le"]
                errors.append(
                    GraphNode(
                        id=le["id"],
                        type=NodeType.LOG_ENTRY,
                        properties=dict(le),
                        labels=list(le.labels),
                    )
                )
            return errors

    def create_incident_from_analysis(
        self,
        organization_id: str,
        project_id: str,
        title: str,
        description: str,
        severity: str,
        affected_services: list[str],
        root_cause: str,
        resolution: str,
        lessons: list[str],
        log_entries: list[str],
    ) -> str:
        """Create an incident node with all relationships from analysis."""
        incident_id = str(uuid.uuid4())

        with self.session() as session:
            # Create incident
            session.run(
                """
                CREATE (i:Incident {
                    id: $id,
                    title: $title,
                    description: $description,
                    severity: $severity,
                    status: 'open',
                    root_cause: $root_cause,
                    resolution: $resolution,
                    created_at: datetime(),
                    organization_id: $org_id,
                    project_id: $proj_id
                })
            """,
                {
                    "id": incident_id,
                    "title": title,
                    "description": description,
                    "severity": severity,
                    "root_cause": root_cause,
                    "resolution": resolution,
                    "org_id": organization_id,
                    "proj_id": project_id,
                },
            )

            # Link to organization and project
            session.run(
                """
                MATCH (o:Organization {id: $org_id}), (i:Incident {id: $incident_id})
                MERGE (o)-[:HAS_INCIDENT]->(i)
            """,
                {"org_id": organization_id, "incident_id": incident_id},
            )

            session.run(
                """
                MATCH (p:Project {id: $proj_id}), (i:Incident {id: $incident_id})
                MERGE (p)-[:HAS_INCIDENT]->(i)
            """,
                {"proj_id": project_id, "incident_id": incident_id},
            )

            # Link affected services
            for svc_name in affected_services:
                session.run(
                    """
                    MATCH (s:Service {name: $svc_name}), (i:Incident {id: $incident_id})
                    MERGE (i)-[:AFFECTED]->(s)
                """,
                    {"svc_name": svc_name, "incident_id": incident_id},
                )

            # Create fix node
            fix_id = str(uuid.uuid4())
            session.run(
                """
                CREATE (f:Fix {
                    id: $id,
                    description: $resolution,
                    created_at: datetime()
                })
            """,
                {"id": fix_id, "resolution": resolution},
            )
            session.run(
                """
                MATCH (i:Incident {id: $incident_id}), (f:Fix {id: $fix_id})
                MERGE (i)-[:FIXED_BY]->(f)
            """,
                {"incident_id": incident_id, "fix_id": fix_id},
            )

            # Create lesson nodes
            for lesson in lessons:
                lesson_id = str(uuid.uuid4())
                session.run(
                    """
                    CREATE (l:Lesson {
                        id: $id,
                        description: $lesson,
                        created_at: datetime()
                    })
                """,
                    {"id": lesson_id, "lesson": lesson},
                )
                session.run(
                    """
                    MATCH (i:Incident {id: $incident_id}), (l:Lesson {id: $lesson_id})
                    MERGE (i)-[:LEARNED]->(l)
                """,
                    {"incident_id": incident_id, "lesson_id": lesson_id},
                )

            # Link log entries
            for log_id in log_entries:
                session.run(
                    """
                    MATCH (le:LogEntry {id: $log_id}), (i:Incident {id: $incident_id})
                    MERGE (i)-[:HAS_LOG]->(le)
                """,
                    {"log_id": log_id, "incident_id": incident_id},
                )

        return incident_id

    def get_stats(self) -> dict[str, int]:
        """Get graph statistics."""
        queries = {
            "organizations": "MATCH (n:Organization) RETURN count(n) as count",
            "projects": "MATCH (n:Project) RETURN count(n) as count",
            "services": "MATCH (n:Service) RETURN count(n) as count",
            "incidents": "MATCH (n:Incident) RETURN count(n) as count",
            "postmortems": "MATCH (n:Postmortem) RETURN count(n) as count",
            "log_entries": "MATCH (n:LogEntry) RETURN count(n) as count",
            "errors": "MATCH (n:Error) RETURN count(n) as count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) as count",
        }

        stats = {}
        with self.session() as session:
            for key, query in queries.items():
                try:
                    result = session.run(query)
                    stats[key] = result.single()["count"]
                except Exception:
                    stats[key] = 0
        return stats


# Singleton instance
_neo4j_service: Neo4jService | None = None


def get_neo4j_service() -> Neo4jService:
    """Get or create singleton Neo4j service."""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
        try:
            _neo4j_service.initialize_schema()
        except Exception as e:
            logger.warning(f"Neo4j schema initialization skipped (unavailable): {e}")
    return _neo4j_service
