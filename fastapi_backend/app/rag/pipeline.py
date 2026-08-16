"""
RAG pipeline orchestrator combining vector retrieval, graph retrieval,
reranking, and LLM generation for incident analysis.
"""

import time
from dataclasses import dataclass
from typing import Any

from app.core.logging import logger
from app.llm.provider import LLMProvider, get_llm_provider
from app.rag.models import QueryIntent, QueryUnderstanding, RAGContext
from app.retrieval.graph_retrieval import (
    GraphRetrievalResult,
    GraphRetriever,
    get_graph_retriever,
)
from app.retrieval.hybrid import (
    HybridRetriever,
    RetrievalResult,
    get_hybrid_retriever,
)


@dataclass
class IncidentAnalysisResponse:
    """Structured incident analysis response."""

    incident_id: str
    title: str
    source: str
    source_url: str | None
    severity: str
    status: str
    service: str
    team: str
    timeline: list[dict[str, Any]]
    root_cause: str
    impact: str
    resolution: str
    lessons_learned: list[str]
    log_snippets: list[str]
    tags: list[str]
    created_at: str
    resolved_at: str | None
    raw_content: str
    evidence: list[dict[str, Any]]
    graph_relationships: list[dict[str, Any]]
    recommended_investigation: list[str]
    potential_root_cause: str
    risk_severity: str
    confidence: str
    sources: list[dict[str, Any]]


class QueryUnderstandingEngine:
    """Engine for understanding user queries and extracting intent/entities."""

    def __init__(self):
        self.intent_keywords = {
            QueryIntent.ROOT_CAUSE_ANALYSIS: [
                "why",
                "root cause",
                "cause",
                "reason",
                "what caused",
            ],
            QueryIntent.HISTORICAL_INCIDENT_SEARCH: [
                "previous",
                "past",
                "historical",
                "similar",
                "before",
                "earlier",
            ],
            QueryIntent.COMPONENT_INVESTIGATION: [
                "which component",
                "what component",
                "investigate",
                "check",
            ],
            QueryIntent.DEPENDENCY_INVESTIGATION: [
                "depend",
                "dependency",
                "depends on",
                "upstream",
                "downstream",
            ],
            QueryIntent.PREVIOUS_FIX_SEARCH: [
                "fix",
                "fixed",
                "solution",
                "resolved",
                "remediation",
            ],
            QueryIntent.LESSON_LEARNED_SEARCH: ["lesson", "learned", "takeaway", "prevent"],
            QueryIntent.INCIDENT_COMPARISON: ["compare", "similar to", "like", "versus", "vs"],
            QueryIntent.IMPACT_ANALYSIS: ["impact", "affect", "blast radius", "scope"],
            QueryIntent.SERVICE_RELATIONSHIP: ["relationship", "connect", "call", "interact"],
            QueryIntent.ERROR_DIAGNOSIS: ["error", "exception", "fail", "crash", "bug", "issue"],
            QueryIntent.POSTMORTEM_RETRIEVAL: ["postmortem", "post-mortem", "retrospective", "rca"],
        }

    def understand(self, query: str) -> QueryUnderstanding:
        """Analyze query and extract structured understanding."""
        query_lower = query.lower()
        entities = get_graph_retriever().extract_entities(query)

        # Detect intent
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                intent_scores[intent] = score

        intent = (
            max(intent_scores, key=intent_scores.get)
            if intent_scores
            else QueryIntent.GENERAL_QUERY
        )
        confidence = intent_scores.get(intent, 0) / max(sum(intent_scores.values()), 1)

        # Extract keywords
        import re

        keywords = re.findall(r"\b\w{4,}\b", query_lower)
        keywords = [
            k
            for k in keywords
            if k
            not in {
                "what",
                "when",
                "where",
                "which",
                "how",
                "why",
                "the",
                "and",
                "for",
                "with",
                "from",
            }
        ]

        return QueryUnderstanding(
            original_query=query,
            intent=intent,
            entities=entities,
            keywords=keywords[:20],
            confidence=confidence,
        )


class ContextAssembler:
    """Assembles retrieval results into structured context for LLM."""

    def assemble(
        self,
        vector_results: RetrievalResult,
        graph_results: list[GraphRetrievalResult],
        query_understanding: QueryUnderstanding,
    ) -> RAGContext:
        """Assemble context from all retrieval results."""
        context = RAGContext(
            vector_results=vector_results,
            graph_results=graph_results,
            query_understanding=query_understanding,
            total_evidence_count=len(vector_results.candidates)
            + sum(len(gr.nodes) for gr in graph_results),
        )
        return context

    def format_evidence(self, context: RAGContext) -> list[dict[str, Any]]:
        """Format evidence for citation in response."""
        evidence = []

        # Vector evidence
        for candidate in context.vector_results.candidates:
            evidence.append(
                {
                    "type": "vector",
                    "source": candidate.source,
                    "chunk_id": candidate.id,
                    "score": candidate.score,
                    "retrieval_method": candidate.retrieval_method,
                    "content": candidate.text[:500],
                    "metadata": {
                        "service": candidate.metadata.get("service"),
                        "timestamp": candidate.metadata.get("timestamp"),
                        "level": candidate.metadata.get("severity")
                        or candidate.metadata.get("level"),
                        "source_file": candidate.metadata.get("source"),
                    },
                }
            )

        # Graph evidence
        for gr in context.graph_results:
            for node in gr.nodes:
                evidence.append(
                    {
                        "type": "graph",
                        "query_type": gr.query_type.value,
                        "node_id": node.id,
                        "node_type": node.type.value,
                        "properties": node.properties,
                        "content": str(node.properties)[:500],
                    }
                )

        return evidence

    def format_graph_relationships(self, context: RAGContext) -> list[dict[str, Any]]:
        """Format graph relationships for response."""
        relationships = []
        for gr in context.graph_results:
            for rel in gr.relationships:
                relationships.append(
                    {
                        "source": rel.source_id,
                        "target": rel.target_id,
                        "type": rel.type.value,
                        "properties": rel.properties,
                    }
                )
        return relationships


class RAGPipeline:
    """Main RAG pipeline orchestrating retrieval, context assembly, and generation."""

    def __init__(
        self,
        hybrid_retriever: HybridRetriever | None = None,
        graph_retriever: GraphRetriever | None = None,
        llm_provider: LLMProvider | None = None,
        query_understanding_engine: QueryUnderstandingEngine | None = None,
        context_assembler: ContextAssembler | None = None,
    ):
        self.hybrid_retriever = hybrid_retriever or get_hybrid_retriever()
        self.graph_retriever = graph_retriever or get_graph_retriever()
        self.llm_provider = llm_provider or get_llm_provider()
        self.query_understanding = query_understanding_engine or QueryUnderstandingEngine()
        self.context_assembler = context_assembler or ContextAssembler()

    def analyze_incident(
        self,
        query: str,
        organization_id: str,
        project_id: str | None = None,
        top_k: int = 10,
    ) -> IncidentAnalysisResponse:
        """Full incident analysis pipeline."""
        start_time = time.time()

        # 1. Understand query
        logger.info(f"Understanding query: {query[:100]}")
        understanding = self.query_understanding.understand(query)

        # 2. Build filter for tenant isolation
        filter_dict = {
            "organization_id": organization_id,
            "project_id": project_id,
        }

        # 3. Vector retrieval
        logger.info("Performing vector retrieval...")
        vector_results = self.hybrid_retriever.retrieve(
            query=query,
            filter_=filter_dict,
            top_k=top_k,
        )

        # 4. Graph retrieval (best-effort: vector results remain usable if the graph is down)
        logger.info("Performing graph retrieval...")
        graph_results: list[GraphRetrievalResult] = []
        try:
            graph_results = self.graph_retriever.retrieve_by_query(query)
        except Exception as e:
            logger.warning(f"Graph retrieval skipped (unavailable or failed): {e}")

        # 5. Assemble context
        logger.info("Assembling context...")
        context = self.context_assembler.assemble(vector_results, graph_results, understanding)

        # 6. Format evidence
        evidence = self.context_assembler.format_evidence(context)
        graph_relationships = self.context_assembler.format_graph_relationships(context)

        # 7. Generate response with LLM
        logger.info("Generating incident analysis...")
        response = self.llm_provider.generate_incident_analysis(
            query=query,
            understanding=understanding,
            evidence=evidence,
            graph_relationships=graph_relationships,
            context=context,
        )

        total_time_ms = (time.time() - start_time) * 1000
        logger.info(f"Incident analysis completed in {total_time_ms:.0f}ms")

        return response

    def search_incidents(
        self,
        query: str,
        organization_id: str,
        project_id: str | None = None,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """Search for similar incidents without full analysis."""
        filter_dict = {"organization_id": organization_id, "project_id": project_id}
        vector_results = self.hybrid_retriever.retrieve(query, filter_=filter_dict, top_k=top_k)
        try:
            graph_results = self.graph_retriever.retrieve_by_query(query)
        except Exception as e:
            logger.warning(f"Graph retrieval skipped (unavailable or failed): {e}")
            graph_results = []

        return {
            "query": query,
            "vector_results": [
                {
                    "id": c.id,
                    "text": c.text[:300],
                    "score": c.score,
                    "source": c.source,
                    "metadata": c.metadata,
                }
                for c in vector_results.candidates
            ],
            "graph_results": [
                {
                    "query_type": gr.query_type.value,
                    "nodes": [
                        {"id": n.id, "type": n.type.value, "properties": n.properties}
                        for n in gr.nodes
                    ],
                }
                for gr in graph_results
            ],
        }


_rag_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create singleton RAG pipeline."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
