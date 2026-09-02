"""
Ingestion API endpoints for the FastAPI data plane.
"""

import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import TenantDep
from app.core.logging import logger
from app.embeddings.provider import get_embedding_provider
from app.ingestion.parsers import PARSER_FACTORY, ParsedEntry
from app.processing.chunking import ChunkerFactory, create_chunker
from app.services.activity_service import record_activity
from app.services.graph_service import (
    get_neo4j_service,
)
from app.services.vector_service import create_point_from_chunk, get_qdrant_service

router = APIRouter()

UPLOAD_DIR = Path(settings.DATA_DIR) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {".log", ".txt", ".json", ".csv", ".md", ".markdown", ".yaml", ".yml"}


class TextIngestRequest(BaseModel):
    """Request model for direct text ingestion (e.g. postmortem documents)."""

    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: str = Field(..., min_length=1, description="Document text to ingest")
    service: str | None = Field(None, description="Optional service name")
    chunking_strategy: str = Field("hierarchical", description="Chunking strategy")
    organization_id: str | None = Field(None, description="Optional organization override")
    project_id: str | None = Field(None, description="Optional project override")


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


def _ingest_entries(
    entries: list[ParsedEntry],
    org_id: str,
    proj_id: str,
    *,
    chunking_strategy: str = "hierarchical",
) -> dict[str, Any]:
    """Chunk, embed and store entries (shared by file, batch and text ingestion)."""
    chunker = create_chunker(chunking_strategy)
    chunks = chunker.chunk(entries, organization_id=org_id, project_id=proj_id)
    logger.info(f"Created {len(chunks)} chunks")
    for chunk in chunks:
        chunk.chunking_strategy = chunking_strategy

    chunks_requested = len(chunks)
    truncated = False
    if chunks_requested > settings.MAX_CHUNKS_PER_FILE:
        logger.warning(
            f"Truncating {chunks_requested} chunks to {settings.MAX_CHUNKS_PER_FILE} "
            f"(raise MAX_CHUNKS_PER_FILE to ingest more)"
        )
        chunks = chunks[: settings.MAX_CHUNKS_PER_FILE]
        truncated = True

    result: dict[str, Any] = {
        "entries_parsed": len(entries),
        "chunks_created": len(chunks),
        "chunks_requested": chunks_requested,
        "truncated": truncated,
    }

    if not chunks:
        return result

    # Embed
    embedding_provider = get_embedding_provider()
    texts = [chunk.text for chunk in chunks]
    embedding_result = embedding_provider.embed_documents(texts)
    logger.info(f"Generated embeddings in {embedding_result.duration_ms:.0f}ms")

    # Store in Qdrant
    qdrant = get_qdrant_service()
    points = [
        create_point_from_chunk(chunk, embedding)
        for chunk, embedding in zip(chunks, embedding_result.embeddings, strict=True)
    ]
    qdrant.upsert_points(points, dimension=embedding_result.dimension)
    logger.info(f"Stored {len(points)} points in Qdrant")

    # Store in Neo4j (best-effort: graph is auxiliary; Qdrant is the source of truth)
    try:
        neo4j = get_neo4j_service()
        _store_chunks_in_neo4j(neo4j, chunks, org_id, proj_id)
        logger.info("Stored graph relationships in Neo4j")
    except Exception as e:
        logger.warning(f"Neo4j storage skipped (unavailable or failed): {e}")

    result.update(
        {
            "embedding_model": embedding_result.model,
            "embedding_dimension": embedding_result.dimension,
        }
    )
    return result


@router.post("", summary="Ingest a log file or document")
def ingest_file(
    ctx: TenantDep,
    file: UploadFile = File(...),
    chunking_strategy: str = Form("hierarchical"),
    organization_id: str | None = Form(None),
    project_id: str | None = Form(None),
):
    """
    Ingest a single file through the full pipeline:
    parse -> chunk -> embed -> store in Qdrant + Neo4j
    """
    start_time = time.time()
    validate_file(file)

    org_id = organization_id or ctx.organization_id
    proj_id = project_id or "default"

    # Save file temporarily
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix
    temp_path = UPLOAD_DIR / f"{file_id}{file_ext}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Processing file: {file.filename} ({file.size} bytes) for org={org_id}")

        # Parse
        parser = PARSER_FACTORY.get_parser(temp_path)
        entries = list(parser.parse(temp_path))
        logger.info(f"Parsed {len(entries)} entries")

        if not entries:
            record_activity(
                "ingest",
                f"No entries in {file.filename}",
                org_id=org_id,
                status="warning",
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "completed",
                    "message": "No parsable entries found in file",
                    "file_id": file_id,
                    "filename": file.filename,
                    "entries_parsed": 0,
                    "chunks_created": 0,
                },
            )

        # Chunk -> embed -> store (shared pipeline)
        result = _ingest_entries(
            entries,
            org_id,
            proj_id,
            chunking_strategy=chunking_strategy,
        )

        duration_ms = (time.time() - start_time) * 1000

        record_activity(
            "ingest",
            f"Ingested {file.filename}",
            org_id=org_id,
            detail=f"{result['entries_parsed']} entries, {result['chunks_created']} chunks "
            f"({chunking_strategy})",
            meta={
                "chunks_created": result["chunks_created"],
                "chunking_strategy": chunking_strategy,
            },
        )

        return {
            "status": "completed",
            "file_id": file_id,
            "filename": file.filename,
            **result,
            "processing_time_ms": duration_ms,
        }

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        record_activity(
            "ingest",
            f"Failed to ingest {file.filename}",
            org_id=org_id,
            status="failed",
            detail=str(e)[:300],
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        ) from e
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.post("/batch", summary="Ingest multiple files")
def ingest_batch(
    ctx: TenantDep,
    files: list[UploadFile] = File(...),
    chunking_strategy: str = Form("hierarchical"),
    organization_id: str | None = Form(None),
    project_id: str | None = Form(None),
):
    """Ingest multiple files in batch."""
    org_id = organization_id or ctx.organization_id
    proj_id = project_id or "default"

    results = []
    for file in files:
        try:
            validate_file(file)
            file_id = str(uuid.uuid4())
            file_ext = Path(file.filename).suffix
            temp_path = UPLOAD_DIR / f"{file_id}{file_ext}"

            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            parser = PARSER_FACTORY.get_parser(temp_path)
            entries = list(parser.parse(temp_path))

            if entries:
                result = _ingest_entries(
                    entries,
                    org_id,
                    proj_id,
                    chunking_strategy=chunking_strategy,
                )
                results.append(
                    {
                        "filename": file.filename,
                        "status": "completed",
                        **result,
                    }
                )
                record_activity(
                    "ingest",
                    f"Ingested {file.filename}",
                    org_id=org_id,
                    detail=f"{result['entries_parsed']} entries, {result['chunks_created']} chunks "
                    f"({chunking_strategy})",
                    meta={
                        "chunks_created": result["chunks_created"],
                        "chunking_strategy": chunking_strategy,
                    },
                )
            else:
                results.append(
                    {
                        "filename": file.filename,
                        "status": "no_entries",
                        "entries_parsed": 0,
                        "chunks_created": 0,
                    }
                )
                record_activity(
                    "ingest",
                    f"No entries in {file.filename}",
                    org_id=org_id,
                    status="warning",
                )

            temp_path.unlink()

        except Exception as e:
            logger.error(f"Batch ingestion failed for {file.filename}: {e}")
            results.append(
                {
                    "filename": file.filename,
                    "status": "failed",
                    "error": str(e),
                }
            )
            record_activity(
                "ingest",
                f"Failed to ingest {file.filename}",
                org_id=org_id,
                status="failed",
                detail=str(e)[:300],
            )

    return {
        "total_files": len(files),
        "results": results,
    }


@router.post("/text", summary="Ingest postmortem/document text")
def ingest_text(
    request: TextIngestRequest,
    ctx: TenantDep,
):
    """
    Ingest a text document (e.g. a postmortem) directly, without a file upload:
    chunk -> embed -> store in Qdrant + Neo4j.
    """
    start_time = time.time()
    org_id = request.organization_id or ctx.organization_id
    proj_id = request.project_id or "default"

    logger.info(f"Ingesting text document '{request.title}' for org={org_id}")

    entry = ParsedEntry(
        message=request.content.strip(),
        service=request.service or "unknown",
        source_file=request.title,
        source_type="postmortem",
    )

    result = _ingest_entries(
        [entry],
        org_id,
        proj_id,
        chunking_strategy=request.chunking_strategy,
    )
    result["status"] = "completed"
    result["title"] = request.title
    result["processing_time_ms"] = (time.time() - start_time) * 1000

    record_activity(
        "ingest",
        f"Ingested document '{request.title}'",
        org_id=org_id,
        detail=f"{result['chunks_created']} chunks ({request.chunking_strategy})",
        meta={
            "chunks_created": result["chunks_created"],
            "chunking_strategy": request.chunking_strategy,
        },
    )
    return result


@router.get("/parsers", summary="List available parsers")
async def list_parsers(ctx: TenantDep):
    """List available file parsers."""
    return {
        "parsers": [
            {
                "name": "SSHLogParser",
                "extensions": [".log"],
                "description": "SSH authentication logs",
            },
            {
                "name": "ProxifierLogParser",
                "extensions": [".log"],
                "description": "Proxifier proxy logs",
            },
            {
                "name": "HealthAppLogParser",
                "extensions": [".log"],
                "description": "HealthApp Android logs",
            },
            {"name": "ApacheLogParser", "extensions": [".log"], "description": "Apache error logs"},
            {
                "name": "AndroidLogParser",
                "extensions": [".log"],
                "description": "Android logcat format",
            },
            {
                "name": "JSONLogParser",
                "extensions": [".json", ".jsonl"],
                "description": "JSON Lines logs",
            },
            {"name": "CSVParser", "extensions": [".csv"], "description": "CSV structured logs"},
            {
                "name": "MarkdownParser",
                "extensions": [".md", ".markdown"],
                "description": "Markdown documents",
            },
            {
                "name": "JSONDocumentParser",
                "extensions": [".json"],
                "description": "JSON incident/postmortem documents",
            },
            {
                "name": "TextLogParser",
                "extensions": [".log", ".txt"],
                "description": "Generic text logs (fallback)",
            },
        ],
        "chunking_strategies": list(ChunkerFactory.STRATEGIES.keys()),
    }


def _store_chunks_in_neo4j(neo4j, chunks, org_id, proj_id):
    """Store chunks as graph nodes and relationships."""
    with neo4j.session() as session:
        # Ensure org and project exist
        session.run(
            """
            MERGE (o:Organization {id: $org_id})
            MERGE (p:Project {id: $proj_id})
            MERGE (o)-[:HAS_PROJECT]->(p)
        """,
            org_id=org_id,
            proj_id=proj_id,
        )

        # Group chunks by service
        from collections import defaultdict

        service_chunks = defaultdict(list)
        for chunk in chunks:
            service = chunk.service or "unknown"
            service_chunks[service].append(chunk)

        for service_name, service_chunks_list in service_chunks.items():
            service_id = f"service-{service_name}"

            # Create service node
            session.run(
                """
                MERGE (s:Service {id: $service_id, name: $service_name})
                MERGE (p:Project {id: $proj_id})-[:HAS_SERVICE]->(s)
            """,
                service_id=service_id,
                service_name=service_name,
                proj_id=proj_id,
            )

            # Create log entry nodes for child chunks
            for chunk in service_chunks_list:
                if chunk.metadata.get("chunk_type") == "child":
                    session.run(
                        """
                        MATCH (s:Service {id: $service_id})
                        CREATE (le:LogEntry {
                            id: $chunk_id,
                            text: $text,
                            service: $service,
                            level: $level,
                            timestamp: $timestamp,
                            source: $source,
                            organization_id: $org_id,
                            project_id: $proj_id
                        })
                        MERGE (s)-[:PRODUCED_LOG]->(le)
                    """,
                        service_id=service_id,
                        chunk_id=chunk.id,
                        text=chunk.text[:1000],
                        service=chunk.service,
                        level=chunk.metadata.get("levels", ["UNKNOWN"])[0]
                        if chunk.metadata.get("levels")
                        else "UNKNOWN",
                        # Pass the datetime object directly; the Neo4j driver
                        # converts it to a temporal value so duration.between()
                        # below works. None is converted to null and filtered out.
                        timestamp=chunk.timestamp,
                        source=chunk.source,
                        org_id=org_id,
                        proj_id=proj_id,
                    )

        # Create error relationship patterns
        session.run(
            """
            MATCH (le1:LogEntry), (le2:LogEntry)
            WHERE le1.service = le2.service
              AND le1.level IN ['ERROR', 'CRITICAL', 'FATAL']
              AND le2.level IN ['ERROR', 'CRITICAL', 'FATAL']
              AND le1.timestamp < le2.timestamp
              AND duration.between(le1.timestamp, le2.timestamp).minutes < 60
              AND le1.organization_id = $org_id
            MERGE (le1)-[:RELATED_ERROR]->(le2)
        """,
            org_id=org_id,
        )

        # Extract service-to-service dependencies: if a log line mentions another
        # known service, record that this service depends on it.
        known_names = {
            row["name"]
            for row in session.run("MATCH (s:Service) RETURN s.name AS name")
            if row["name"] and row["name"] != "unknown"
        }
        for source_name, source_chunks in service_chunks.items():
            if not source_name or source_name == "unknown":
                continue
            mentioned = set()
            for chunk in source_chunks:
                text = (chunk.text or "").lower()
                if not text:
                    continue
                for other in known_names:
                    if other == source_name:
                        continue
                    if re.search(rf"\b{re.escape(other.lower())}\b", text):
                        mentioned.add(other)
            for other in mentioned:
                session.run(
                    """
                    MATCH (a:Service {name: $a}), (b:Service {name: $b})
                    MERGE (a)-[:DEPENDS_ON]->(b)
                """,
                    a=source_name,
                    b=other,
                )
                logger.info(f"Dependency edge: {source_name} -> {other}")
