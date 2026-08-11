import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure fastapi_backend is in sys.path
fastapi_dir = Path(__file__).resolve().parent.parent.parent / "fastapi_backend"
if str(fastapi_dir) not in sys.path:
    sys.path.insert(0, str(fastapi_dir))

from app.main import app

client = TestClient(app)

def test_root_health():
    """Test root level /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "fastapi_data_plane"

def test_v1_health():
    """Test API v1 /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "fastapi_data_plane"

def test_v1_status():
    """Test API v1 /api/v1/status endpoint."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert "qdrant_host" in data
    assert "neo4j_host" in data
