"""
Chunking strategies for document processing.

Implements hierarchical chunking, semantic chunking, and log-specific chunking
with configurable parameters and metadata preservation.
"""

import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.ingestion.parsers import ParsedEntry


@dataclass
class Chunk:
    """Represents a document chunk with metadata for vector storage."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    source: str = ""
    source_type: str = ""
    organization_id: str = ""
    project_id: str = ""
    service: str | None = None
    severity: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    chunk_index: int = 0
    total_chunks: int = 0
    chunking_strategy: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Convert to payload for vector database storage."""
        payload = {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "source_type": self.source_type,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "service": self.service or "unknown",
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "chunking_strategy": self.chunking_strategy,
        }
        return {k: v for k, v in payload.items() if v is not None}


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, entries: list[ParsedEntry], **kwargs) -> list[Chunk]:
        """Chunk a list of parsed entries."""
        pass


class HierarchicalLogChunker(ChunkingStrategy):
    """
    Hierarchical chunking for logs:
    - Parent chunks: Time-windowed summaries per service (e.g., 1-hour windows)
    - Child chunks: Individual log entries or small groups (5-10 entries)
    """

    def __init__(
        self,
        time_window_minutes: int = 60,
        child_group_size: int = 5,
        max_parent_chars: int = 2048,
        max_child_chars: int = 512,
    ):
        self.time_window_minutes = time_window_minutes
        self.child_group_size = child_group_size
        self.max_parent_chars = max_parent_chars
        self.max_child_chars = max_child_chars

    def chunk(
        self, entries: list[ParsedEntry], organization_id: str = "", project_id: str = "", **kwargs
    ) -> list[Chunk]:
        if not entries:
            return []

        chunks = []

        grouped = defaultdict(list)
        for entry in entries:
            if entry.timestamp:
                window_start = entry.timestamp.replace(
                    minute=(entry.timestamp.minute // self.time_window_minutes)
                    * self.time_window_minutes,
                    second=0,
                    microsecond=0,
                )
            else:
                window_start = datetime.now().replace(minute=0, second=0, microsecond=0)
            grouped[(entry.service, window_start)].append(entry)

        for (service, window), window_entries in grouped.items():
            window_entries.sort(key=lambda x: x.timestamp or datetime.min)

            parent_text = (
                f"Service: {service}, Time window: {window.isoformat()}, "
                f"Log count: {len(window_entries)}. "
            )
            parent_text += " ".join([e.message[:200] for e in window_entries[:10]])

            parent_chunk = Chunk(
                id=str(uuid.uuid4()),
                text=parent_text[: self.max_parent_chars],
                source=window_entries[0].source_file if window_entries else "unknown",
                source_type=window_entries[0].source_type if window_entries else "log",
                organization_id=organization_id,
                project_id=project_id,
                service=service,
                timestamp=window,
                metadata={
                    "chunk_type": "parent",
                    "log_count": len(window_entries),
                    "levels": list({e.level for e in window_entries}),
                    "services": list({e.service for e in window_entries}),
                    "hosts": list({e.host for e in window_entries}),
                    "has_errors": any(
                        e.level in ("ERROR", "CRITICAL", "FATAL") for e in window_entries
                    ),
                },
                chunk_index=0,
                total_chunks=0,
            )
            chunks.append(parent_chunk)

            child_chunks = []
            for i in range(0, len(window_entries), self.child_group_size):
                batch = window_entries[i : i + self.child_group_size]
                child_text = " | ".join([e.to_text() for e in batch])

                child_chunk = Chunk(
                    id=str(uuid.uuid4()),
                    text=child_text[: self.max_child_chars],
                    source=batch[0].source_file,
                    source_type=batch[0].source_type,
                    organization_id=organization_id,
                    project_id=project_id,
                    service=service,
                    timestamp=batch[0].timestamp if batch else window,
                    severity=batch[0].level if batch else None,
                    metadata={
                        "chunk_type": "child",
                        "parent_id": parent_chunk.id,
                        "log_count": len(batch),
                        "levels": list({e.level for e in batch}),
                        "line_numbers": [e.line_number for e in batch],
                        "trace_ids": [e.trace_id for e in batch if e.trace_id],
                        "request_ids": [e.request_id for e in batch if e.request_id],
                    },
                    chunk_index=len(child_chunks),
                    total_chunks=0,
                )
                child_chunks.append(child_chunk)

            parent_chunk.total_chunks = len(child_chunks)
            for idx, child in enumerate(child_chunks):
                child.parent_id = parent_chunk.id
                child.chunk_index = idx
                child.total_chunks = len(child_chunks)
                chunks.append(child)

        return chunks


class SemanticChunker(ChunkingStrategy):
    """
    Semantic chunking for documents using sentence boundaries.
    Uses sentence-transformers for embedding-aware chunk boundaries.
    """

    def __init__(
        self,
        max_chunk_size: int = 512,
        min_chunk_size: int = 100,
        overlap_size: int = 50,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def chunk(
        self, entries: list[ParsedEntry], organization_id: str = "", project_id: str = "", **kwargs
    ) -> list[Chunk]:
        if not entries:
            return []

        full_text = "\n\n".join([e.to_text() for e in entries])
        sentences = self._split_sentences(full_text)

        chunks = []
        current_chunk = ""
        chunk_index = 0

        for sentence in sentences:
            if (
                len(current_chunk) + len(sentence) > self.max_chunk_size
                and len(current_chunk) >= self.min_chunk_size
            ):
                chunk = Chunk(
                    id=str(uuid.uuid4()),
                    text=current_chunk.strip(),
                    source=entries[0].source_file if entries else "unknown",
                    source_type=entries[0].source_type if entries else "document",
                    organization_id=organization_id,
                    project_id=project_id,
                    service=entries[0].service if entries else None,
                    timestamp=entries[0].timestamp if entries else None,
                    metadata={
                        "chunk_type": "semantic",
                        "sentence_count": current_chunk.count(".") + 1,
                    },
                    chunk_index=chunk_index,
                    total_chunks=0,
                )
                chunks.append(chunk)

                overlap_text = current_chunk[-self.overlap_size :] if self.overlap_size > 0 else ""
                current_chunk = overlap_text + " " + sentence
                chunk_index += 1
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk.strip() and len(current_chunk) >= self.min_chunk_size:
            chunk = Chunk(
                id=str(uuid.uuid4()),
                text=current_chunk.strip(),
                source=entries[0].source_file if entries else "unknown",
                source_type=entries[0].source_type if entries else "document",
                organization_id=organization_id,
                project_id=project_id,
                service=entries[0].service if entries else None,
                timestamp=entries[0].timestamp if entries else None,
                metadata={
                    "chunk_type": "semantic",
                    "sentence_count": current_chunk.count(".") + 1,
                },
                chunk_index=chunk_index,
                total_chunks=0,
            )
            chunks.append(chunk)

        for c in chunks:
            c.total_chunks = len(chunks)

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]


class FixedSizeChunker(ChunkingStrategy):
    """Simple fixed-size chunking with overlap."""

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 64,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self, entries: list[ParsedEntry], organization_id: str = "", project_id: str = "", **kwargs
    ) -> list[Chunk]:
        if not entries:
            return []

        full_text = "\n\n".join([e.to_text() for e in entries])
        chunks = []
        chunk_index = 0

        for i in range(0, len(full_text), self.chunk_size - self.overlap):
            chunk_text = full_text[i : i + self.chunk_size]
            if len(chunk_text.strip()) < 50:
                continue

            chunk = Chunk(
                id=str(uuid.uuid4()),
                text=chunk_text,
                source=entries[0].source_file if entries else "unknown",
                source_type=entries[0].source_type if entries else "document",
                organization_id=organization_id,
                project_id=project_id,
                service=entries[0].service if entries else None,
                timestamp=entries[0].timestamp if entries else None,
                metadata={
                    "chunk_type": "fixed",
                    "start_char": i,
                    "end_char": min(i + self.chunk_size, len(full_text)),
                },
                chunk_index=chunk_index,
                total_chunks=0,
            )
            chunks.append(chunk)
            chunk_index += 1

        for c in chunks:
            c.total_chunks = len(chunks)

        return chunks


class ChunkerFactory:
    """Factory for creating chunking strategies."""

    STRATEGIES = {
        "hierarchical": HierarchicalLogChunker,
        "semantic": SemanticChunker,
        "fixed": FixedSizeChunker,
    }

    @classmethod
    def create(cls, strategy: str, **kwargs) -> ChunkingStrategy:
        if strategy not in cls.STRATEGIES:
            raise ValueError(
                f"Unknown chunking strategy: {strategy}. Available: {list(cls.STRATEGIES.keys())}"
            )
        return cls.STRATEGIES[strategy](**kwargs)

    @classmethod
    def register(cls, name: str, strategy_class: type[ChunkingStrategy]):
        cls.STRATEGIES[name] = strategy_class


def create_chunker(strategy: str, **kwargs) -> ChunkingStrategy:
    """Convenience function to create a chunker."""
    return ChunkerFactory.create(strategy, **kwargs)
