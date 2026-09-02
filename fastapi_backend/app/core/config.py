from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ROOT_ENV = ROOT_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Postmortem Intelligence System - AI Plane"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Server settings
    FASTAPI_HOST: str = "0.0.0.0"  # noqa: S104 - bind all interfaces in containers/dev
    FASTAPI_PORT: int = 8001
    FASTAPI_SECRET_KEY: str = "fastapi-insecure-default-secret-key"  # noqa: S105 - placeholder; override in .env
    FASTAPI_INTERNAL_API_KEY: str = "internal-api-secret-key"  # noqa: S105 - placeholder; override in .env

    # Infrastructure settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: str = ""
    QDRANT_URL: str = ""

    NEO4J_HOST: str = "localhost"
    NEO4J_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "postmortem_neo4j_pass"  # noqa: S105 - local dev default; override in .env

    # LLM Settings
    GEMINI_API_KEY: str = ""
    # Local embedding provider (no API quota): sentence-transformers runs fully offline.
    # Set EMBEDDING_PROVIDER=gemini + EMBEDDING_MODEL=gemini-embedding-2 to use the API instead.
    EMBEDDING_PROVIDER: str = "sentence-transformers"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "gemini-1.5-flash"
    LLM_TEMPERATURE: float = 0.1

    # Optional cross-encoder reranking (needs a local model download; off by default
    # to keep retrieval fast on free-tier hardware)
    RERANKING_ENABLED: bool = False

    # Django Control Plane integration
    DJANGO_INTERNAL_URL: str = "http://localhost:8000"

    # Runtime directories
    DATA_DIR: str = str(ROOT_DIR / "data")

    # Ingestion guardrails
    MAX_CHUNKS_PER_FILE: int = 5000

    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
