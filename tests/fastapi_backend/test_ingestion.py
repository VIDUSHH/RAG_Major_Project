"""
FastAPI text-ingestion endpoint tests.

Covers tenant auth, request validation, and wiring of the shared
chunk -> embed -> store pipeline (the pipeline itself is stubbed).
"""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)

TEST_HEADERS = {
    "X-Internal-API-Key": settings.FASTAPI_INTERNAL_API_KEY,
    "X-Organization-ID": "org_test",
}


def test_text_ingest_requires_internal_key():
    """Unauthenticated requests to /ingest/text must be rejected."""
    response = client.post("/api/v1/ingest/text", json={"title": "t", "content": "c"})
    assert response.status_code in (401, 403)


def test_text_ingest_validates_input():
    """Empty title/content must fail validation (422)."""
    response = client.post(
        "/api/v1/ingest/text",
        headers=TEST_HEADERS,
        json={"title": "", "content": ""},
    )
    assert response.status_code == 422


def test_text_ingest_wires_shared_pipeline(monkeypatch):
    """A valid postmortem text request runs the shared ingest pipeline."""
    import app.api.v1.ingestion as ingestion

    def fake_ingest_entries(entries, org_id, proj_id, *, chunking_strategy="hierarchical"):
        assert org_id == "org_test"
        assert entries[0].source_type == "postmortem"
        assert entries[0].source_file == "Incident RCA"
        assert entries[0].service == "api"
        return {
            "entries_parsed": 1,
            "chunks_created": 3,
            "chunks_requested": 3,
            "truncated": False,
            "embedding_model": "mock",
            "embedding_dimension": 768,
        }

    monkeypatch.setattr(ingestion, "_ingest_entries", fake_ingest_entries)

    response = client.post(
        "/api/v1/ingest/text",
        headers=TEST_HEADERS,
        json={
            "title": "Incident RCA",
            "content": "Root cause was a bad deploy.",
            "service": "api",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["title"] == "Incident RCA"
    assert data["chunks_created"] == 3
    assert data["processing_time_ms"] >= 0
