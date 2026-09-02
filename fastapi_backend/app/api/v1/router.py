from fastapi import APIRouter

from app.api.v1 import database, health, ingestion, query

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health & Status"])
api_router.include_router(ingestion.router, prefix="/ingest", tags=["Ingestion"])
api_router.include_router(query.router, prefix="/query", tags=["Query & Analysis"])
api_router.include_router(database.router, prefix="/database", tags=["Database Inspection"])
