import uuid
from json import JSONDecodeError

from app.llm.provider import GeminiProvider, MockLLMProvider
from app.rag.models import QueryIntent, QueryUnderstanding


def _evidence():
    return [
        {
            "type": "vector",
            "source": "Datasets/Apache.log",
            "chunk_id": "chunk-1",
            "score": 0.92,
            "content": "connection refused to payments-service",
            "metadata": {"service": "payments", "timestamp": "2026-01-15T14:23:00Z"},
        }
    ]


def _understanding():
    return QueryUnderstanding(
        original_query="payments service error",
        intent=QueryIntent.ROOT_CAUSE_ANALYSIS,
    )


def test_grounded_response_overrides_fabricated_fields(monkeypatch):
    provider = GeminiProvider()
    fake_llm_output = {
        "incident_id": "not-a-uuid",
        "severity": "P9",
        "status": "obliterated",
        "source": "blackmail",
        "sources": [{"source_file": "hallucinated.log", "chunk_id": "bogus"}],
        "evidence": [{"content": "fabricated evidence"}],
        "graph_relationships": [{"source": "fake", "target": "fake", "type": "FAKE"}],
    }
    monkeypatch.setattr(
        provider, "generate_structured", lambda prompt, schema, **kw: fake_llm_output
    )

    result = provider.generate_incident_analysis(
        query="payments service error",
        understanding=_understanding(),
        evidence=_evidence(),
        graph_relationships=[{"source": "svc-a", "target": "svc-b", "type": "DEPENDS_ON"}],
        context=None,
    )

    uuid.UUID(result["incident_id"])  # server-generated, valid UUID
    assert result["severity"] == "P2"
    assert result["status"] == "investigating"
    assert result["source"] == "analysis"
    assert result["evidence"] == _evidence()
    assert result["graph_relationships"] == [
        {"source": "svc-a", "target": "svc-b", "type": "DEPENDS_ON"}
    ]
    assert result["sources"] == [
        {
            "source_file": "Datasets/Apache.log",
            "chunk_id": "chunk-1",
            "retrieval_score": 0.92,
            "source_type": "vector",
            "service": "payments",
            "timestamp": "2026-01-15T14:23:00Z",
        }
    ]


def test_generation_failure_returns_grounded_fallback(monkeypatch):
    provider = GeminiProvider()

    def _boom(prompt, schema, **kwargs):
        raise JSONDecodeError("boom", "doc", 0)

    monkeypatch.setattr(provider, "generate_structured", _boom)

    result = provider.generate_incident_analysis(
        query="payments service error",
        understanding=_understanding(),
        evidence=_evidence(),
        graph_relationships=[],
        context=None,
    )

    uuid.UUID(result["incident_id"])
    assert result["evidence"] == _evidence()
    assert result["confidence"] == "Medium"
    assert result["root_cause"] != "Insufficient evidence found in the indexed knowledge base."


def test_mock_provider_is_server_grounded():
    provider = MockLLMProvider()
    result = provider.generate_incident_analysis(
        query="payments service error",
        understanding=_understanding(),
        evidence=_evidence(),
        graph_relationships=[],
        context=None,
    )

    uuid.UUID(result["incident_id"])
    assert result["evidence"] == _evidence()
    assert result["sources"][0]["chunk_id"] == "chunk-1"
    assert result["confidence"] == "Medium"
