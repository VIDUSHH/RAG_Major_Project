"""
Django -> FastAPI client tests.

Verifies that FastAPIClient.trigger_postmortem_ingestion posts the correct
payload with tenant headers to the data plane.
"""

import asyncio
import json

import httpx


def test_trigger_postmortem_ingestion_payload():
    from apps.core.clients import FastAPIClient

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["org"] = request.headers.get("X-Organization-ID")
        captured["key"] = request.headers.get("X-Internal-API-Key")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "completed", "chunks_created": 3})

    client = FastAPIClient(base_url="http://testserver")
    client.internal_api_key = "internal-api-secret-key"
    client._client = httpx.AsyncClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
        headers=client._get_base_headers(),
    )

    response = asyncio.run(
        client.trigger_postmortem_ingestion(
            title="Incident RCA",
            content='{"title": "Incident RCA"}',
            organization_id="org-1",
            project_id="proj-1",
            service="api",
        )
    )

    assert response.status_code == 200
    assert captured["path"] == "/api/v1/ingest/text"
    assert captured["org"] == "org-1"
    assert captured["key"] == "internal-api-secret-key"
    assert captured["body"] == {
        "title": "Incident RCA",
        "content": '{"title": "Incident RCA"}',
        "service": "api",
        "project_id": "proj-1",
    }
