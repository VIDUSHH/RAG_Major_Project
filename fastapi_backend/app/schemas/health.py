from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    service: str = Field(..., json_schema_extra={"example": "fastapi_data_plane"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})


class StatusResponse(BaseModel):
    environment: str
    debug: bool
    qdrant_host: str
    neo4j_host: str
    gemini_configured: bool
