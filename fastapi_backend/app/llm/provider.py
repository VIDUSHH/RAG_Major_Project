"""
LLM provider abstraction for the RAG pipeline.

Supports Google Gemini with structured output generation for incident analysis.
Falls back to mock provider for development when Gemini is unavailable.
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.rag.models import QueryUnderstanding, RAGContext


class LLMProviderType(StrEnum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.1
    max_output_tokens: int = 8192
    top_p: float = 0.95
    top_k: int = 40
    system_prompt: str | None = None


@dataclass
class LLMResponse:
    """Response from LLM generation."""

    content: str
    model: str
    tokens_used: int = 0
    duration_ms: float = 0.0
    finish_reason: str = "unknown"


_ALLOWED_SOURCES = {"github", "confluence", "pagerduty", "manual", "logs", "analysis"}
_ALLOWED_STATUSES = {"resolved", "mitigated", "open", "investigating"}
_ALLOWED_SEVERITIES = {"P0", "P1", "P2", "P3"}
_ALLOWED_RISKS = {"Critical", "High", "Medium", "Low"}
_ALLOWED_CONFIDENCE = {"High", "Medium", "Low", "Insufficient Evidence"}
_LLM_TIMEOUT_S = 60.0


def _normalize_str(value: Any, allowed: set[str] | None, default: str) -> str:
    """Return a cleaned string, matched case-insensitively against allowed values."""
    if not isinstance(value, str):
        return default
    candidate = value.strip()
    if not candidate:
        return default
    if allowed is not None:
        for allowed_value in allowed:
            if allowed_value.lower() == candidate.lower():
                return allowed_value
        return default
    return candidate


def _ground_analysis_response(
    data: dict[str, Any],
    query: str,
    understanding: QueryUnderstanding,
    evidence: list[dict[str, Any]],
    graph_relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge an LLM analysis with server-verified retrieval data.

    The LLM writes the narrative fields (title, root cause, timeline, ...).
    Evidence-derived fields (incident_id, evidence, sources,
    graph_relationships) are always rebuilt from the actual retrieval
    results so the API can never cite fabricated sources or chunks.
    """
    services = understanding.entities.services or ["unknown-service"]
    errors = understanding.entities.errors or ["unknown-error"]

    sources = [
        {
            "source_file": e.get("metadata", {}).get("source_file") or e.get("source", "unknown"),
            "chunk_id": e.get("chunk_id", "unknown"),
            "retrieval_score": e.get("score", 0),
            "source_type": e.get("type", "unknown"),
            "service": e.get("metadata", {}).get("service", "unknown"),
            "timestamp": e.get("metadata", {}).get("timestamp", "unknown"),
        }
        for e in evidence[:10]
    ]

    timeline = data.get("timeline")
    if isinstance(timeline, list):
        timeline = [
            t for t in timeline if isinstance(t, dict) and t.get("timestamp") and t.get("event")
        ]
    if not timeline:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        timeline = [
            {"timestamp": now, "event": f"Analysis requested: {query[:100]}", "actor": "user"},
            {
                "timestamp": now,
                "event": f"Found {len(evidence)} evidence items from vector/graph search",
                "actor": "rag-system",
            },
        ]

    lessons_learned = data.get("lessons_learned")
    if not isinstance(lessons_learned, list) or not lessons_learned:
        lessons_learned = (
            [
                "Implement better monitoring for early detection",
                "Ensure proper alerting on error rate thresholds",
                "Document runbooks for common failure scenarios",
            ]
            if evidence
            else ["Insufficient historical data for lessons learned"]
        )

    log_snippets = data.get("log_snippets")
    if not isinstance(log_snippets, list):
        log_snippets = [e.get("content", "")[:200] for e in evidence[:3]]

    tags = data.get("tags")
    if not isinstance(tags, list):
        tags = services + errors + [understanding.intent.value]

    recommended_investigation = data.get("recommended_investigation")
    if not isinstance(recommended_investigation, list) or not recommended_investigation:
        recommended_investigation = [
            f"Check {services[0]} logs for error patterns",
            f"Review recent deployments to {services[0]}",
            f"Verify {errors[0]} related configurations" if errors else "Analyze error patterns",
            "Compare with similar historical incidents",
            "Validate dependency health for upstream services",
        ]

    default_confidence = "Insufficient Evidence" if not evidence else "Medium"

    return {
        "incident_id": str(uuid.uuid4()),
        "title": _normalize_str(data.get("title"), None, f"Incident Analysis: {query[:80]}"),
        "source": _normalize_str(data.get("source"), _ALLOWED_SOURCES, "analysis"),
        "source_url": data.get("source_url") if isinstance(data.get("source_url"), str) else None,
        "severity": _normalize_str(
            data.get("severity"),
            _ALLOWED_SEVERITIES,
            understanding.entities.severity or "P2",
        ),
        "status": _normalize_str(data.get("status"), _ALLOWED_STATUSES, "investigating"),
        "service": _normalize_str(data.get("service"), None, services[0]),
        "team": _normalize_str(data.get("team"), None, "platform-engineering"),
        "timeline": timeline,
        "root_cause": _normalize_str(
            data.get("root_cause"),
            None,
            "Insufficient evidence found in the indexed knowledge base."
            if not evidence
            else "Based on retrieved evidence showing similar patterns in historical incidents.",
        ),
        "impact": _normalize_str(
            data.get("impact"),
            None,
            f"Service {services[0]} experiencing degraded performance or errors"
            if services
            else "Impact under investigation",
        ),
        "resolution": _normalize_str(
            data.get("resolution"), None, "Under investigation. Check retrieved evidence for fixes."
        ),
        "lessons_learned": lessons_learned,
        "log_snippets": log_snippets,
        "tags": tags,
        "created_at": _normalize_str(
            data.get("created_at"),
            None,
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
        "resolved_at": (
            data.get("resolved_at") if isinstance(data.get("resolved_at"), str) else None
        ),
        "raw_content": _normalize_str(
            data.get("raw_content"),
            None,
            f"Analysis generated from {len(evidence)} retrieved evidence items for query: {query}",
        ),
        "evidence": evidence[:10],
        "graph_relationships": graph_relationships[:10],
        "recommended_investigation": recommended_investigation,
        "potential_root_cause": _normalize_str(
            data.get("potential_root_cause"),
            None,
            f"Likely related to {', '.join(errors)} in {', '.join(services)}"
            if (services or errors)
            else "Under investigation",
        ),
        "risk_severity": _normalize_str(data.get("risk_severity"), _ALLOWED_RISKS, "Medium"),
        "confidence": _normalize_str(
            data.get("confidence"), _ALLOWED_CONFIDENCE, default_confidence
        ),
        "sources": sources,
    }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: dict[str, Any], **kwargs) -> dict[str, Any]:
        """Generate structured output matching schema."""
        pass

    @abstractmethod
    def generate_incident_analysis(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> dict[str, Any]:
        """Generate incident analysis response."""
        pass


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for development and testing."""

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        return LLMResponse(
            content="Mock response for development",
            model="mock",
            duration_ms=10.0,
        )

    def generate_structured(self, prompt: str, schema: dict[str, Any], **kwargs) -> dict[str, Any]:
        return self.generate_incident_analysis(
            query="mock query",
            understanding=QueryUnderstanding(original_query="mock"),
            evidence=[],
            graph_relationships=[],
            context=RAGContext(
                vector_results=None,
                graph_results=[],
                query_understanding=QueryUnderstanding(original_query="mock"),
            ),
        )

    def generate_incident_analysis(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> dict[str, Any]:
        """Generate a mock incident analysis for development."""
        return _ground_analysis_response({}, query, understanding, evidence, graph_relationships)


# Try to import Gemini, fall back to mock if unavailable
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    _GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("google-generativeai not available, using mock provider")
    genai = None
    GenerationConfig = None


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, config: LLMConfig | None = None):
        super().__init__(config)
        self._model = None
        self._api_key = settings.GEMINI_API_KEY

    def _get_model(self):
        """Lazy initialize Gemini model."""
        if not _GEMINI_AVAILABLE:
            raise RuntimeError("google-generativeai package not available")

        if self._model is None:
            if not self._api_key:
                raise ValueError("GEMINI_API_KEY not set in environment")
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(
                model_name=self.config.model_name,
                generation_config=GenerationConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                    top_p=self.config.top_p,
                    top_k=self.config.top_k,
                ),
            )
        return self._model

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate text from prompt."""
        start_time = time.time()
        model = self._get_model()

        try:
            response = model.generate_content(
                prompt,
                request_options={"timeout": _LLM_TIMEOUT_S},
                **kwargs,
            )
            duration_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                content=response.text or "",
                model=self.config.model_name,
                tokens_used=getattr(response.usage_metadata, "total_token_count", 0)
                if hasattr(response, "usage_metadata")
                else 0,
                duration_ms=duration_ms,
                finish_reason=response.candidates[0].finish_reason.name
                if response.candidates
                else "unknown",
            )
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    def generate_structured(self, prompt: str, schema: dict[str, Any], **kwargs) -> dict[str, Any]:
        """Generate structured output using JSON mode."""
        model = self._get_model()

        json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Do not include any explanation, markdown, or text outside the JSON object."""

        try:
            response = model.generate_content(
                json_prompt,
                generation_config=GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=self.config.max_output_tokens,
                    response_mime_type="application/json",
                ),
                request_options={"timeout": _LLM_TIMEOUT_S},
            )
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response.text}")
            raise
        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            raise

    def generate_incident_analysis(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> dict[str, Any]:
        """Generate structured incident analysis response."""
        prompt = self._build_incident_analysis_prompt(
            query, understanding, evidence, graph_relationships, context
        )

        schema = {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string", "format": "uuid"},
                "title": {"type": "string"},
                "source": {
                    "type": "string",
                    "enum": ["github", "confluence", "pagerduty", "manual", "logs", "analysis"],
                },
                "source_url": {"type": ["string", "null"], "format": "uri"},
                "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                "status": {
                    "type": "string",
                    "enum": ["resolved", "mitigated", "open", "investigating"],
                },
                "service": {"type": "string"},
                "team": {"type": "string"},
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string", "format": "date-time"},
                            "event": {"type": "string"},
                            "actor": {"type": "string"},
                        },
                        "required": ["timestamp", "event", "actor"],
                    },
                },
                "root_cause": {"type": "string"},
                "impact": {"type": "string"},
                "resolution": {"type": "string"},
                "lessons_learned": {"type": "array", "items": {"type": "string"}},
                "log_snippets": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "created_at": {"type": "string", "format": "date-time"},
                "resolved_at": {"type": ["string", "null"], "format": "date-time"},
                "raw_content": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "object"}},
                "graph_relationships": {"type": "array", "items": {"type": "object"}},
                "recommended_investigation": {"type": "array", "items": {"type": "string"}},
                "potential_root_cause": {"type": "string"},
                "risk_severity": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]},
                "confidence": {
                    "type": "string",
                    "enum": ["High", "Medium", "Low", "Insufficient Evidence"],
                },
                "sources": {"type": "array", "items": {"type": "object"}},
            },
            "required": [
                "incident_id",
                "title",
                "source",
                "severity",
                "status",
                "service",
                "team",
                "timeline",
                "root_cause",
                "impact",
                "resolution",
                "lessons_learned",
                "log_snippets",
                "tags",
                "created_at",
                "raw_content",
                "evidence",
                "graph_relationships",
                "recommended_investigation",
                "potential_root_cause",
                "risk_severity",
                "confidence",
                "sources",
            ],
        }

        try:
            data = self.generate_structured(prompt, schema)
        except Exception as e:
            logger.error(f"Incident analysis generation failed, returning grounded fallback: {e}")
            data = {}
        return _ground_analysis_response(data, query, understanding, evidence, graph_relationships)

    def _build_incident_analysis_prompt(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> str:
        """Build the prompt for incident analysis generation."""

        evidence_text = self._format_evidence_for_prompt(evidence)
        graph_text = self._format_graph_for_prompt(graph_relationships)

        intent_guidance = {
            "root_cause_analysis": "Focus on identifying the root cause with supporting evidence.",
            "historical_incident_search": "Focus on finding and comparing similar historical incidents.",  # noqa: E501
            "component_investigation": "Focus on which components to investigate first.",  # noqa: E501
            "dependency_investigation": "Focus on service dependencies and upstream/downstream impacts.",  # noqa: E501
            "previous_fix_search": "Focus on what fixes worked previously.",
            "lesson_learned_search": "Focus on lessons learned and preventive measures.",
            "incident_comparison": "Focus on comparing this incident with similar ones.",
            "impact_analysis": "Focus on blast radius and affected services.",
            "service_relationship": "Focus on how services interact and depend on each other.",
            "error_diagnosis": "Focus on diagnosing the specific error.",
            "postmortem_retrieval": "Focus on retrieving postmortem details.",
        }

        guidance = intent_guidance.get(
            understanding.intent.value, "Provide comprehensive incident analysis."
        )

        prompt = f"""You are an expert SRE and Incident Commander analyzing production incidents.

USER QUERY: "{query}"

QUERY UNDERSTANDING:
- Intent: {understanding.intent.value}
- Detected Services: {", ".join(understanding.entities.services) or "None"}
- Detected Errors: {", ".join(understanding.entities.errors) or "None"}
- Severity Hint: {understanding.entities.severity or "Not specified"}
- Guidance: {guidance}

RETRIEVED EVIDENCE (Vector + Graph):
{evidence_text}

GRAPH RELATIONSHIPS:
{graph_text}

TASK: Generate a comprehensive incident analysis report. Follow these rules STRICTLY:

1. EVIDENCE-BACKED: Every claim must be supported by retrieved evidence. Cite using [Source N].
2. NO HALLUCINATION: Never invent incidents, fixes, logs, or relationships not in the evidence.
3. DISTINGUISH EVIDENCE vs INFERENCE: Clearly separate what was retrieved vs what you infer.
4. CONFIDENCE SCORING: Rate confidence High/Medium/Low/Insufficient Evidence based on quality.
5. ACTIONABLE RECOMMENDATIONS: Provide specific, prioritized investigation steps.

If evidence is insufficient, say "Insufficient evidence found" and state what was vs what's missing.

OUTPUT FORMAT: Return ONLY a JSON object matching the schema. No markdown, no extra text.

Generate incident_id as a valid UUID v4 string.
Use current timestamp for created_at if not found in evidence.
For timeline, extract from evidence or create reasonable timeline based on evidence.
For sources, include: source_file, chunk_id, retrieval_score, source_type, service, timestamp."""

        return prompt

    def _format_evidence_for_prompt(self, evidence: list[dict[str, Any]]) -> str:
        """Format evidence for inclusion in prompt."""
        if not evidence:
            return "No evidence retrieved."

        lines = []
        for i, ev in enumerate(evidence[:15], 1):
            source_info = f"[Source {i}] "
            source_info += f"Type: {ev.get('type', 'unknown')}, "
            source_info += f"Source: {ev.get('source', 'unknown')}, "
            source_info += f"Score: {ev.get('score', 0):.3f}, "
            source_info += f"Service: {ev.get('metadata', {}).get('service', 'unknown')}, "
            source_info += f"Time: {ev.get('metadata', {}).get('timestamp', 'unknown')}"
            lines.append(source_info)
            lines.append(f"Content: {ev.get('content', '')[:400]}")
            lines.append("")

        return "\n".join(lines)

    def _format_graph_for_prompt(self, relationships: list[dict[str, Any]]) -> str:
        """Format graph relationships for prompt."""
        if not relationships:
            return "No graph relationships retrieved."

        lines = ["Graph structure:"]
        for rel in relationships[:20]:
            lines.append(
                f"  {rel.get('source', '?')} --[{rel.get('type', 'RELATED_TO')}]--> {rel.get('target', '?')}"  # noqa: E501
            )
        return "\n".join(lines)


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    PROVIDERS = {
        LLMProviderType.GEMINI: GeminiProvider,
        LLMProviderType.MOCK: MockLLMProvider,
    }

    @classmethod
    def create(cls, provider_type: LLMProviderType, config: LLMConfig | None = None) -> LLMProvider:
        if provider_type not in cls.PROVIDERS:
            raise ValueError(f"Unknown LLM provider: {provider_type}")
        return cls.PROVIDERS[provider_type](config)

    @classmethod
    def register(cls, provider_type: LLMProviderType, provider_class: type[LLMProvider]):
        cls.PROVIDERS[provider_type] = provider_class


def get_llm_provider(
    provider_type: LLMProviderType | None = None,
    config: LLMConfig | None = None,
) -> LLMProvider:
    """Get LLM provider from environment or explicit config."""
    if provider_type is None:
        provider_name = settings.LLM_PROVIDER
        try:
            provider_type = LLMProviderType(provider_name)
        except ValueError:
            provider_type = LLMProviderType.MOCK

    if config is None:
        config = LLMConfig(
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )

    # Fallback to mock if Gemini requested but not available
    if provider_type == LLMProviderType.GEMINI and not _GEMINI_AVAILABLE:
        logger.warning("Gemini requested but not available, falling back to mock provider")
        provider_type = LLMProviderType.MOCK

    return LLMProviderFactory.create(provider_type, config)
