"""
Shared models for RAG pipeline to avoid circular imports.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.retrieval.graph_retrieval import EntityExtractionResult


class QueryIntent(StrEnum):
    """Detected query intents."""

    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    HISTORICAL_INCIDENT_SEARCH = "historical_incident_search"
    COMPONENT_INVESTIGATION = "component_investigation"
    DEPENDENCY_INVESTIGATION = "dependency_investigation"
    PREVIOUS_FIX_SEARCH = "previous_fix_search"
    LESSON_LEARNED_SEARCH = "lesson_learned_search"
    INCIDENT_COMPARISON = "incident_comparison"
    IMPACT_ANALYSIS = "impact_analysis"
    SERVICE_RELATIONSHIP = "service_relationship"
    ERROR_DIAGNOSIS = "error_diagnosis"
    POSTMORTEM_RETRIEVAL = "postmortem_retrieval"
    GENERAL_QUERY = "general_query"


@dataclass
class QueryUnderstanding:
    """Structured understanding of user query."""

    original_query: str
    intent: QueryIntent = QueryIntent.GENERAL_QUERY
    entities: EntityExtractionResult = field(default_factory=EntityExtractionResult)
    keywords: list[str] = field(default_factory=list)
    time_range: dict[str, str] | None = None
    confidence: float = 0.0


@dataclass
class RAGContext:
    """Assembled context for LLM generation."""

    vector_results: Any = None
    graph_results: list[Any] = field(default_factory=list)
    query_understanding: QueryUnderstanding = field(
        default_factory=lambda: QueryUnderstanding(original_query="")
    )
    total_evidence_count: int = 0
