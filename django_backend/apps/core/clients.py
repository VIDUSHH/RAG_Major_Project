"""
Service client for Django → FastAPI communication.

Handles internal API key authentication and tenant context propagation.
"""

import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class FastAPIClient:
    """
    Client for making authenticated requests to FastAPI data plane.

    Automatically includes:
    - X-Internal-API-Key for service-to-service auth
    - X-Organization-ID for tenant isolation
    - X-User-ID, X-User-Email, X-User-Roles for user context
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or getattr(
            settings, "FASTAPI_INTERNAL_URL", "http://localhost:8001"
        )
        self.internal_api_key = getattr(settings, "FASTAPI_INTERNAL_API_KEY", None)

        # Configure timeout: 30s connect, 120s read for long-running operations
        self.timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=10.0)
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=str(self.base_url) if self.base_url else "http://localhost:8001",
                timeout=self.timeout,
                headers=self._get_base_headers(),
            )
        return self._client

    def _get_base_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.internal_api_key:
            headers["X-Internal-API-Key"] = self.internal_api_key
        return headers

    def _get_tenant_headers(
        self,
        organization_id: str,
        user_id: str | None = None,
        user_email: str | None = None,
        user_roles: list[str] | None = None,
    ) -> dict[str, str]:
        headers = self._get_base_headers()
        headers["X-Organization-ID"] = str(organization_id)
        if user_id:
            headers["X-User-ID"] = str(user_id)
        if user_email:
            headers["X-User-Email"] = user_email
        if user_roles:
            headers["X-User-Roles"] = ",".join(user_roles)
        return headers

    async def request(
        self,
        method: str,
        path: str,
        organization_id: str,
        user_id: str | None = None,
        user_email: str | None = None,
        user_roles: list[str] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Make an authenticated request to FastAPI with tenant context.
        """
        headers = self._get_tenant_headers(organization_id, user_id, user_email, user_roles)

        response = await self.client.request(
            method=method,
            url=path,
            json=json,
            params=params,
            headers=headers,
        )

        # Log errors
        if response.status_code >= 400:
            logger.error(
                f"FastAPI request failed: {method} {path} - "
                f"Status: {response.status_code} - Response: {response.text}"
            )

        return response

    async def get(self, path: str, organization_id: str, **kwargs) -> httpx.Response:
        return await self.request("GET", path, organization_id, **kwargs)

    async def post(self, path: str, organization_id: str, **kwargs) -> httpx.Response:
        return await self.request("POST", path, organization_id, **kwargs)

    async def put(self, path: str, organization_id: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", path, organization_id, **kwargs)

    async def patch(self, path: str, organization_id: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", path, organization_id, **kwargs)

    async def delete(self, path: str, organization_id: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", path, organization_id, **kwargs)

    async def trigger_postmortem_ingestion(
        self,
        title: str,
        content: str,
        organization_id: str,
        project_id: str,
        service: str | None = None,
    ) -> httpx.Response:
        """
        Ingest a postmortem document into the FastAPI data plane.
        """
        payload = {
            "title": title,
            "content": content,
            "service": service,
            "project_id": project_id,
        }
        return await self.post("/api/v1/ingest/text", organization_id, json=payload)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Singleton instance
_fastapi_client: FastAPIClient | None = None


def get_fastapi_client() -> FastAPIClient:
    """Get or create the singleton FastAPI client."""
    global _fastapi_client
    if _fastapi_client is None:
        _fastapi_client = FastAPIClient()
    return _fastapi_client
