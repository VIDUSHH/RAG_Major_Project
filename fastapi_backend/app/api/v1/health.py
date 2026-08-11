from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse, StatusResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns basic health status of the FastAPI data plane service."""
    return HealthResponse(
        status="healthy",
        service="fastapi_data_plane",
        version="1.0.0"
    )

@router.get("/status", response_model=StatusResponse)
async def service_status() -> StatusResponse:
    """Returns detailed service status and infrastructure configuration flags."""
    return StatusResponse(
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        qdrant_host=settings.QDRANT_HOST,
        neo4j_host=settings.NEO4J_HOST,
        gemini_configured=bool(settings.GEMINI_API_KEY)
    )
