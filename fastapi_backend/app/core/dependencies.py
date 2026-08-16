"""
FastAPI dependency injection providers.

Phase 3: Inject validated tenant context into route handlers.
"""

from typing import Annotated

from fastapi import Depends, Header, Security
from pydantic import BaseModel, Field

from app.core.security import verify_internal_api_key


class TenantContext(BaseModel):
    """
    Holds the validated tenant and user identity for a request.

    Populated from the internal API key after Phase 3.
    """

    organization_id: str = Field(..., description="UUID of the organization")
    user_id: str | None = Field(None, description="UUID of the user making the request")
    user_email: str | None = Field(None, description="Email of the user")
    user_roles: list[str] = Field(
        default_factory=list, description="User's roles in the organization"
    )


async def get_tenant_context(
    _internal_key: Annotated[str, Security(verify_internal_api_key)],
    x_organization_id: str = Header(..., alias="X-Organization-ID"),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
    x_user_roles: str | None = Header(None, alias="X-User-Roles"),
) -> TenantContext:
    """
    Dependency that extracts and validates tenant context from request headers.

    Django passes these headers when calling FastAPI on behalf of an authenticated user.
    All downstream Qdrant/Neo4j queries MUST filter by organization_id from this context.

    Usage in route handlers::

        @router.post("/search")
        async def search(ctx: Annotated[TenantContext, Depends(get_tenant_context)]):
            ...
    """
    # Parse roles from comma-separated string
    roles = []
    if x_user_roles:
        roles = [r.strip() for r in x_user_roles.split(",") if r.strip()]

    return TenantContext(
        organization_id=x_organization_id,
        user_id=x_user_id,
        user_email=x_user_email,
        user_roles=roles,
    )


# Convenience type alias for route handler signatures
TenantDep = Annotated[TenantContext, Depends(get_tenant_context)]
