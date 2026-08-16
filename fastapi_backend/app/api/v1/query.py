"""
Query and analysis API endpoints for the FastAPI data plane.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import TenantDep
from app.core.logging import logger
from app.rag.pipeline import QueryIntent, get_rag_pipeline

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for incident analysis query."""

    query: str = Field(
        ..., min_length=1, max_length=5000, description="Natural language incident query"
    )
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return")
    project_id: str | None = Field(None, description="Optional project filter")


class SearchRequest(BaseModel):
    """Request model for simple search."""

    query: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(20, ge=1, le=100)
    project_id: str | None = None


class QueryResponse(BaseModel):
    """Response model for incident analysis."""

    incident_id: str
    title: str
    source: str
    source_url: str | None
    severity: str
    status: str
    service: str
    team: str
    timeline: list[dict[str, Any]]
    root_cause: str
    impact: str
    resolution: str
    lessons_learned: list[str]
    log_snippets: list[str]
    tags: list[str]
    created_at: str
    resolved_at: str | None
    raw_content: str
    evidence: list[dict[str, Any]]
    graph_relationships: list[dict[str, Any]]
    recommended_investigation: list[str]
    potential_root_cause: str
    risk_severity: str
    confidence: str
    sources: list[dict[str, Any]]


class SearchResponse(BaseModel):
    """Response model for search."""

    query: str
    vector_results: list[dict[str, Any]]
    graph_results: list[dict[str, Any]]


@router.post("/analyze", response_model=QueryResponse, summary="Analyze an incident")
def analyze_incident(
    request: QueryRequest,
    ctx: TenantDep,
):
    """
    Perform full incident analysis using hybrid RAG:
    1. Query understanding
    2. Vector retrieval (dense + sparse + RRF + rerank)
    3. Graph retrieval (dependencies, error patterns, similar incidents)
    4. Context assembly
    5. LLM generation with evidence citations
    """
    try:
        logger.info(
            f"Analyzing incident query: {request.query[:100]} for org={ctx.organization_id}"
        )

        pipeline = get_rag_pipeline()
        response = pipeline.analyze_incident(
            query=request.query,
            organization_id=ctx.organization_id,
            project_id=request.project_id,
            top_k=request.top_k,
        )

        from app.services.activity_service import record_activity

        record_activity(
            "analyze",
            f"Analyzed: {request.query[:80]}",
            org_id=ctx.organization_id,
            detail=(
                f"Confidence {response.get('confidence', 'N/A')}, "
                f"{len(response.get('evidence', []))} evidence items"
            ),
            meta={"confidence": response.get("confidence")},
        )

        return response

    except Exception as e:
        logger.error(f"Incident analysis failed: {e}")

        from app.services.activity_service import record_activity

        record_activity(
            "analyze",
            f"Analysis failed: {request.query[:60]}",
            org_id=ctx.organization_id,
            status="failed",
            detail=str(e)[:300],
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        ) from e


@router.post("/search", response_model=SearchResponse, summary="Search incidents and logs")
def search_incidents(
    request: SearchRequest,
    ctx: TenantDep,
):
    """
    Search for similar incidents and relevant logs without full LLM analysis.
    Returns raw retrieval results from vector and graph stores.
    """
    try:
        logger.info(f"Searching: {request.query[:100]} for org={ctx.organization_id}")

        pipeline = get_rag_pipeline()
        result = pipeline.search_incidents(
            query=request.query,
            organization_id=ctx.organization_id,
            project_id=request.project_id,
            top_k=request.top_k,
        )

        return result

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        ) from e


@router.get("/intents", summary="List supported query intents")
async def list_intents(ctx: TenantDep):
    """List supported query intent types."""
    return {
        "intents": [
            {"value": intent.value, "description": intent.value.replace("_", " ").title()}
            for intent in QueryIntent
        ]
    }


@router.get("/examples", summary="Get example queries")
async def get_examples(ctx: TenantDep):
    """Get example queries for each intent."""
    return {
        "examples": {
            "root_cause_analysis": [
                "Why did the payment service fail last night?",
                "What caused the authentication service to return 500 errors?",
                "Root cause of the database connection pool exhaustion",
            ],
            "historical_incident_search": [
                "Show previous incidents related to authentication service",
                "Find similar incidents to the current Redis timeout issue",
                "What happened during the last payment service outage?",
            ],
            "component_investigation": [
                "Which components should I investigate first for the checkout failure?",
                "What services are affected by the API gateway issue?",
            ],
            "dependency_investigation": [
                "What services depend on the failing payment service?",
                "Show upstream dependencies of the authentication service",
            ],
            "previous_fix_search": [
                "What fixes worked previously for database timeouts?",
                "How was the Redis connection issue resolved last time?",
            ],
            "lesson_learned_search": [
                "What lessons were learned from the last major outage?",
                "What preventive measures were recommended after the payment failure?",
            ],
            "impact_analysis": [
                "What is the blast radius of the auth service failure?",
                "Which services will be impacted if the database goes down?",
            ],
            "error_diagnosis": [
                "Diagnose: NullPointerException in payment adapter v2.3.1",
                "Intermittent 500 errors from checkout service after deployment",
            ],
        }
    }
