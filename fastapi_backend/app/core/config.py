import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_ENV = BASE_DIR.parent / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Postmortem Intelligence System - AI Plane"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Server settings
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8001
    FASTAPI_SECRET_KEY: str = "fastapi-insecure-default-secret-key"
    FASTAPI_INTERNAL_API_KEY: str = "internal-api-secret-key"

    # Infrastructure settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: str = ""

    NEO4J_HOST: str = "localhost"
    NEO4J_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "postmortem_neo4j_pass"

    # LLM Settings
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-004"
    LLM_MODEL: str = "gemini-1.5-flash"

    # Django Control Plane integration
    DJANGO_INTERNAL_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV) if ROOT_ENV.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
