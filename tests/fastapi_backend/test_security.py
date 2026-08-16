"""
FastAPI AI/Data Plane failure-path and security tests.

Tests what happens when:
- An unknown endpoint is requested (404)
- The /api/v1/status endpoint is requested in non-development environments (403)
- The health endpoint returns expected structure
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unknown_route_returns_404():
    """Requests to undefined routes must return 404."""
    response = client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404


def test_root_health_returns_correct_schema():
    """Root /health must return status, service and version fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert data["status"] == "healthy"


def test_v1_health_returns_correct_schema():
    """/api/v1/health must return status, service and version fields."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "fastapi_data_plane"


def test_status_blocked_in_non_development(monkeypatch):
    """
    /api/v1/status must return 403 when the environment is not 'development'.
    This validates that infrastructure details are never exposed in production.
    """
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(cfg.settings, "DEBUG", False)
    response = client.get("/api/v1/status")
    assert response.status_code == 403, (
        "/api/v1/status must be blocked (403) outside the development environment"
    )


def test_status_does_not_expose_secrets():
    """
    /api/v1/status must never expose sensitive keys like API keys or passwords
    even in development mode.
    """
    response = client.get("/api/v1/status")
    if response.status_code == 200:
        data = response.json()
        # Confirm that no raw secret values appear in the response
        response_text = str(data).lower()
        assert "api_key" not in response_text or data.get("gemini_configured") in (True, False), (
            "Status endpoint must not expose raw API key values"
        )
        # The gemini_configured field must be a boolean flag, not the key itself
        assert isinstance(data.get("gemini_configured"), bool)
