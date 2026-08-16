"""
Data Ingestion Script for RAG Project

This script ingests log datasets from the Datasets folder and stores them in:
- Qdrant (vector database) for semantic search
- Neo4j (graph database) for relationship analysis

Run this script after starting Docker infrastructure (from the project root):
    docker compose -f infrastructure/docker-compose.yml up -d qdrant neo4j

Then run:
    python scripts/ingest_datasets.py
"""

import os
import re
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi

# Third-party imports
from sentence_transformers import SentenceTransformer

# Load environment variables from .env file (same location as project root)
# This allows QDRANT_URL, QDRANT_API_KEY to be set in .env
from dotenv import load_dotenv
# Try to load .env from project root (parent of scripts/)
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    # Paths
    DATASETS_DIR: Path = Path("C:/Users/dabee/Downloads/RAG_Project/Datasets")
    OUTPUT_DIR: Path = Path("C:/Users/dabee/Downloads/RAG_Project/data/processed")

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    # QDRANT_URL read from environment (Qdrant Cloud URL)
    # Set QDRANT_URL in .env to use Cloud mode, leave empty for local fallback
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    # QDRANT_API_KEY read from environment
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = "postmortems_v1"
    VECTOR_DIM: int = 768  # all-mpnet-base-v2 dimension

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "postmortem_neo4j_pass"

    # Processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    BATCH_SIZE: int = 100
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"

    # Organization context (for multi-tenancy)
    ORGANIZATION_ID: str = "00000000-0000-0000-0000-000000000001"
    PROJECT_ID: str = "00000000-0000-0000-0000-000000000002"


CONFIG = Config()


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class NormalizedLog:
    timestamp: datetime
    service: str
    host: str
    level: str
    message: str
    trace_id: str | None = None
    request_id: str | None = None
    environment: str = "production"
    exception: str | None = None
    stack_trace: str | None = None
    raw: dict[str, Any] = None

    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = [
            f"[{self.timestamp.isoformat()}]",
            f"service={self.service}",
            f"host={self.host}",
            f"level={self.level}",
            self.message
        ]
        if self.exception:
            parts.append(f"exception={self.exception}")
        if self.stack_trace:
            parts.append(f"stack_trace={self.stack_trace}")
        return " ".join(parts)


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    source_type: str
    organization_id: str
    project_id: str
    service: str | None = None
    severity: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ============================================================================
# Log Parsers
# ============================================================================

class LogParser:
    """Base log parser."""

    def parse(self, line: str) -> NormalizedLog | None:
        raise NotImplementedError


class SSHLogParser(LogParser):
    """Parser for SSH auth logs."""

    # Example: Jan  7 15:26:44 LabSZ sshd[29967]: Failed password for invalid user admin from 41.32.163.225 port 56665 ssh2
    PATTERN = re.compile(
        r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[\d+\])?:\s+(.+)$'
    )

    def parse(self, line: str) -> NormalizedLog | None:
        match = self.PATTERN.match(line.strip())
        if not match:
            return None

        timestamp_str, host, service, message = match.groups()

        # Parse timestamp (assume current year)
        try:
            timestamp = datetime.strptime(f"2024 {timestamp_str}", "%Y %b %d %H:%M:%S")
        except ValueError:
            timestamp = datetime.now()

        # Determine level
        level = "INFO"
        if any(kw in message.lower() for kw in ["failed", "error", "invalid", "failure", "break-in"]):
            level = "ERROR"
        elif any(kw in message.lower() for kw in ["accepted", "opened", "closed"]):
            level = "INFO"
        elif "warning" in message.lower() or "warn" in message.lower():
            level = "WARN"

        # Extract IP and user
        ip_match = re.search(r'from\s+(\d+\.\d+\.\d+\.\d+)', message)
        user_match = re.search(r'(?:invalid user|user)\s+(\S+)', message)

        return NormalizedLog(
            timestamp=timestamp,
            service="sshd",
            host=host,
            level=level,
            message=message,
            raw={"ip": ip_match.group(1) if ip_match else None, "user": user_match.group(1) if user_match else None}
        )


class ProxifierLogParser(LogParser):
    """Parser for Proxifier logs."""

    # Example: [10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 close, 0 bytes sent, 0 bytes received, lifetime <1 sec
    PATTERN = re.compile(
        r'^\[(\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\S+)\s+-\s+(\S+)\s+(.+)$'
    )

    def parse(self, line: str) -> NormalizedLog | None:
        match = self.PATTERN.match(line.strip())
        if not match:
            return None

        timestamp_str, process, endpoint, details = match.groups()

        try:
            timestamp = datetime.strptime(f"2024 {timestamp_str}", "%Y %m.%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.now()

        return NormalizedLog(
            timestamp=timestamp,
            service="proxifier",
            host=endpoint.split(":")[0] if ":" in endpoint else endpoint,
            level="INFO",
            message=f"{process} - {details}",
            raw={"process": process, "endpoint": endpoint, "details": details}
        )


class HealthAppLogParser(LogParser):
    """Parser for HealthApp Android logs."""

    # Example: 20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579
    PATTERN = re.compile(
        r'^(\d{8}-\d{2}:\d{2}:\d{2}:\d{3})\|(\S+)\|(\d+)\|(.+)$'
    )

    def parse(self, line: str) -> NormalizedLog | None:
        match = self.PATTERN.match(line.strip())
        if not match:
            return None

        timestamp_str, tag, pid, message = match.groups()

        try:
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d-%H:%M:%S:%f")
        except ValueError:
            timestamp = datetime.now()

        return NormalizedLog(
            timestamp=timestamp,
            service="healthapp",
            host=tag,
            level="DEBUG",
            message=message,
            raw={"tag": tag, "pid": pid}
        )


class ApacheLogParser(LogParser):
    """Parser for Apache error logs."""

    # Example: [Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP LDAP SDK
    PATTERN = re.compile(
        r'^\[(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})\]\s+\[(\w+)\]\s+(.+)$'
    )

    def parse(self, line: str) -> NormalizedLog | None:
        match = self.PATTERN.match(line.strip())
        if not match:
            return None

        timestamp_str, level, message = match.groups()

        try:
            timestamp = datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
        except ValueError:
            timestamp = datetime.now()

        # Map Apache levels
        level_map = {
            "notice": "INFO",
            "warn": "WARN",
            "error": "ERROR",
            "crit": "CRITICAL",
            "alert": "CRITICAL",
            "emerg": "CRITICAL",
            "debug": "DEBUG",
            "info": "INFO"
        }

        return NormalizedLog(
            timestamp=timestamp,
            service="apache",
            host="apache-server",
            level=level_map.get(level.lower(), "INFO"),
            message=message,
            raw={"apache_level": level}
        )


class AndroidLogParser(LogParser):
    """Parser for Android logcat format."""

    # Example: 12-17 19:31:36.263  1795  1825 I PowerManager_screenOn: DisplayPowerStatesetColorFadeLevel: level=1.0
    PATTERN = re.compile(
        r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(\S+):\s+(.+)$'
    )

    def parse(self, line: str) -> NormalizedLog | None:
        match = self.PATTERN.match(line.strip())
        if not match:
            return None

        timestamp_str, pid, tid, level_char, tag, message = match.groups()

        try:
            timestamp = datetime.strptime(f"2024 {timestamp_str}", "%Y %m-%d %H:%M:%S.%f")
        except ValueError:
            timestamp = datetime.now()

        level_map = {
            "V": "DEBUG",
            "D": "DEBUG",
            "I": "INFO",
            "W": "WARN",
            "E": "ERROR",
            "F": "CRITICAL"
        }

        return NormalizedLog(
            timestamp=timestamp,
            service="android",
            host=tag,
            level=level_map.get(level_char, "INFO"),
            message=message,
            raw={"pid": pid, "tid": tid, "tag": tag, "level_char": level_char}
        )


# ============================================================================
# Parser Factory
# ============================================================================

PARSERS = {
    "SSH.log": SSHLogParser(),
    "Proxifier.log": ProxifierLogParser(),
    "HealthApp.log": HealthAppLogParser(),
    "Apache.log": ApacheLogParser(),
    "Android.log": AndroidLogParser(),
}


def get_parser(filename: str) -> LogParser:
    """Get appropriate parser for a log file."""
    return PARSERS.get(filename, SSHLogParser())  # Default to SSH parser


# ============================================================================
# Ingestion Pipeline
# ============================================================================

class IngestionPipeline:
    def __init__(self, config: Config = CONFIG):
        self.config = config
        self.embedding_model = None
        self.qdrant_client = None
        self.neo4j_driver = None
        self.bm25_corpus = []
        self.bm25 = None

    def initialize(self):
        """Initialize connections and models."""
        print("Initializing embedding model...")
        self.embedding_model = SentenceTransformer(self.config.EMBEDDING_MODEL)

        print("Connecting to Qdrant...")
        if self.config.QDRANT_URL:
            # Qdrant Cloud: use URL + API keys
            print(f"Using Qdrant Cloud: {self.config.QDRANT_URL}")
            self.qdrant_client = QdrantClient(
                url=self.config.QDRANT_URL,
                api_key=self.config.QDRANT_API_KEY or None,
            )
        else:
            # Local Qdrant: use host + port + optional API key
            print(f"Using local Qdrant at {self.config.QDRANT_HOST}:{self.config.QDRANT_PORT}")
            self.qdrant_client = QdrantClient(
                host=self.config.QDRANT_HOST,
                port=self.config.QDRANT_PORT,
                api_key=self.config.QDRANT_API_KEY or None,
            )
        self._ensure_qdrant_collection()

        print("Connecting to Neo4j...")
        self.neo4j_driver = GraphDatabase.driver(
            self.config.NEO4J_URI,
            auth=(self.config.NEO4J_USER, self.config.NEO4J_PASSWORD)
        )
        self._ensure_neo4j_schema()

    def _ensure_qdrant_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        collections = self.qdrant_client.get_collections().collections
        if not any(c.name == self.config.QDRANT_COLLECTION for c in collections):
            print(f"Creating Qdrant collection: {self.config.QDRANT_COLLECTION}")
            self.qdrant_client.create_collection(
                collection_name=self.config.QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=self.config.VECTOR_DIM,
                    distance=Distance.COSINE
                )
            )
        else:
            print(f"Qdrant collection {self.config.QDRANT_COLLECTION} already exists")

    def _ensure_neo4j_schema(self):
        """Create Neo4j constraints and indexes."""
        with self.neo4j_driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (l:LogEntry) REQUIRE l.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Error) REQUIRE e.id IS UNIQUE",
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Constraint creation warning: {e}")

            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (l:LogEntry) ON (l.timestamp)",
                "CREATE INDEX IF NOT EXISTS FOR (l:LogEntry) ON (l.service)",
                "CREATE INDEX IF NOT EXISTS FOR (l:LogEntry) ON (l.level)",
                "CREATE INDEX IF NOT EXISTS FOR (l:LogEntry) ON (l.organization_id)",
            ]
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"Index creation warning: {e}")

    def parse_log_file(self, filepath: Path) -> Generator[NormalizedLog, None, None]:
        """Parse a log file and yield normalized logs."""
        parser = get_parser(filepath.name)

        with open(filepath, encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    log = parser.parse(line)
                    if log:
                        yield log
                except Exception as e:
                    print(f"Error parsing {filepath.name}:{line_num}: {e}")
                    continue

    def create_chunks(self, logs: list[NormalizedLog], source: str, source_type: str) -> list[Chunk]:
        """Create chunks from normalized logs using hierarchical chunking."""
        chunks = []

        # Group logs by service and time window (1 hour windows)
        from collections import defaultdict
        grouped = defaultdict(list)

        for log in logs:
            if log.timestamp:
                window_key = log.timestamp.replace(minute=0, second=0, microsecond=0)
            else:
                window_key = datetime.now().replace(minute=0, second=0, microsecond=0)
            grouped[(log.service, window_key)].append(log)

        for (service, window), window_logs in grouped.items():
            # Sort by timestamp
            window_logs.sort(key=lambda x: x.timestamp or datetime.min)

            # Create parent chunk (summary of the window)
            parent_text = f"Service: {service}, Time window: {window}, Log count: {len(window_logs)}. "
            parent_text += " ".join([log.message[:200] for log in window_logs[:10]])

            parent_chunk = Chunk(
                id=str(uuid.uuid4()),
                text=parent_text[:2048],
                source=source,
                source_type=source_type,
                organization_id=self.config.ORGANIZATION_ID,
                project_id=self.config.PROJECT_ID,
                service=service,
                timestamp=window,
                metadata={
                    "chunk_type": "parent",
                    "log_count": len(window_logs),
                    "levels": list(set(l.level for l in window_logs)),
                }
            )
            chunks.append(parent_chunk)

            # Create child chunks (individual logs or small groups)
            for i in range(0, len(window_logs), 5):
                batch = window_logs[i:i+5]
                child_text = " | ".join([log.to_text() for log in batch])

                child_chunk = Chunk(
                    id=str(uuid.uuid4()),
                    text=child_text[:512],
                    source=source,
                    source_type=source_type,
                    organization_id=self.config.ORGANIZATION_ID,
                    project_id=self.config.PROJECT_ID,
                    service=service,
                    timestamp=batch[0].timestamp if batch else window,
                    metadata={
                        "chunk_type": "child",
                        "parent_id": parent_chunk.id,
                        "log_count": len(batch),
                        "levels": list(set(l.level for l in batch)),
                    }
                )
                chunks.append(child_chunk)

        return chunks

    def generate_embeddings(self, chunks: list[Chunk]) -> list[list[float]]:
        """Generate embeddings for chunks."""
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, batch_size=32, show_progress_bar=True)
        return embeddings.tolist()

    def store_in_qdrant(self, chunks: list[Chunk], embeddings: list[list[float]]):
        """Store chunks and embeddings in Qdrant."""
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            payload = {
                "organization_id": chunk.organization_id,
                "project_id": chunk.project_id,
                "service": chunk.service or "unknown",
                "source": chunk.source,
                "source_type": chunk.source_type,
                "text": chunk.text,
                "timestamp": chunk.timestamp.isoformat() if chunk.timestamp else None,
                "metadata": chunk.metadata,
            }
            points.append(PointStruct(
                id=chunk.id,
                vector=embedding,
                payload=payload
            ))

        # Upsert in batches
        for i in range(0, len(points), self.config.BATCH_SIZE):
            batch = points[i:i+self.config.BATCH_SIZE]
            self.qdrant_client.upsert(
                collection_name=self.config.QDRANT_COLLECTION,
                points=batch
            )
            print(f"  Upserted batch {i//self.config.BATCH_SIZE + 1}/{(len(points)-1)//self.config.BATCH_SIZE + 1}")

    def build_bm25_index(self, chunks: list[Chunk]):
        """Build BM25 index from chunk texts."""
        corpus = [chunk.text.split() for chunk in chunks]
        self.bm25 = BM25Okapi(corpus)
        self.bm25_corpus = chunks
        print(f"Built BM25 index with {len(chunks)} documents")

    def store_in_neo4j(self, chunks: list[Chunk]):
        """Store log relationships in Neo4j."""
        with self.neo4j_driver.session() as session:
            # Create organization and project nodes
            session.run(
                """
                MERGE (o:Organization {id: $org_id})
                MERGE (p:Project {id: $proj_id})
                MERGE (o)-[:HAS_PROJECT]->(p)
                """,
                org_id=self.config.ORGANIZATION_ID,
                proj_id=self.config.PROJECT_ID
            )

            # Create service nodes and log entries
            for chunk in chunks:
                if chunk.metadata.get("chunk_type") == "child":  # Only store child chunks as individual logs
                    service_id = f"service-{chunk.service}" if chunk.service else "service-unknown"

                    session.run(
                        """
                        MERGE (s:Service {id: $service_id, name: $service_name})
                        MERGE (p:Project {id: $proj_id})-[:HAS_SERVICE]->(s)
                        CREATE (l:LogEntry {
                            id: $chunk_id,
                            text: $text,
                            service: $service,
                            level: $level,
                            timestamp: $timestamp,
                            source: $source,
                            organization_id: $org_id
                        })
                        MERGE (s)-[:PRODUCED_LOG]->(l)
                        """,
                        service_id=service_id,
                        service_name=chunk.service or "unknown",
                        proj_id=self.config.PROJECT_ID,
                        chunk_id=chunk.id,
                        text=chunk.text[:1000],  # Limit text length
                        service=chunk.service or "unknown",
                        level=chunk.metadata.get("levels", ["UNKNOWN"])[0] if chunk.metadata.get("levels") else "UNKNOWN",
                        timestamp=chunk.timestamp.isoformat() if chunk.timestamp else datetime.now().isoformat(),
                        source=chunk.source,
                        org_id=self.config.ORGANIZATION_ID
                    )

            # Create error pattern relationships
            session.run(
                """
                MATCH (l1:LogEntry), (l2:LogEntry)
                WHERE l1.service = l2.service 
                  AND l1.level = 'ERROR' 
                  AND l2.level = 'ERROR'
                  AND l1.timestamp < l2.timestamp
                  AND duration.between(l1.timestamp, l2.timestamp).minutes < 60
                MERGE (l1)-[:RELATED_ERROR]->(l2)
                """
            )

    def run(self):
        """Run the full ingestion pipeline."""
        print("=" * 60)
        print("Starting Data Ingestion Pipeline")
        print("=" * 60)

        self.initialize()

        log_files = [
            ("SSH.log", "ssh"),
            ("Proxifier.log", "proxifier"),
            ("HealthApp.log", "healthapp"),
            ("Apache.log", "apache"),
        ]

        # Also process Android log
        android_path = self.config.DATASETS_DIR / "Android_v1" / "Android.log"
        if android_path.exists():
            log_files.append((android_path, "android"))

        all_chunks = []
        total_logs_parsed = 0

        for filepath, source_type in log_files:
            if isinstance(filepath, str):
                filepath = Path(filepath)

            if not filepath.exists():
                print(f"File not found: {filepath}")
                continue

            print(f"\nProcessing {filepath.name}...")

            # Parse logs
            logs = list(self.parse_log_file(filepath))
            total_logs_parsed += len(logs)
            print(f"  Parsed {len(logs)} log entries")

            if not logs:
                continue

            # Create chunks
            chunks = self.create_chunks(logs, filepath.name, source_type)
            print(f"  Created {len(chunks)} chunks")

            all_chunks.extend(chunks)

        if not all_chunks:
            print("No chunks created!")
            return

        print(f"\nTotal chunks: {len(all_chunks)}")

        # Generate embeddings
        print("\nGenerating embeddings...")
        embeddings = self.generate_embeddings(all_chunks)

        # Store in Qdrant
        print("\nStoring in Qdrant...")
        self.store_in_qdrant(all_chunks, embeddings)

        # Build BM25 index
        print("\nBuilding BM25 index...")
        self.build_bm25_index(all_chunks)

        # Store in Neo4j
        print("\nStoring in Neo4j...")
        self.store_in_neo4j(all_chunks)

        print("\n" + "=" * 60)
        print("Ingestion Complete!")
        print("=" * 60)
        print(f"Total logs processed: {total_logs_parsed}")
        print(f"Total chunks stored: {len(all_chunks)}")
        print(f"Qdrant collection: {self.config.QDRANT_COLLECTION}")
        print(f"Neo4j: Organization={self.config.ORGANIZATION_ID}, Project={self.config.PROJECT_ID}")

    def close(self):
        """Close connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.qdrant_client:
            self.qdrant_client.close()


def main():
    pipeline = IngestionPipeline()
    try:
        pipeline.run()
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
