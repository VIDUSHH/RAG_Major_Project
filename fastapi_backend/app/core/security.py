"""
Security utilities for the FastAPI AI/Data Plane.

Phase 3: Internal API key validation for Django → FastAPI service-to-service calls.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

# Header name used for internal service-to-service authentication.
# Django passes this header when calling FastAPI on behalf of an authenticated user.
INTERNAL_API_KEY_HEADER = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)


async def verify_internal_api_key(api_key: str | None = Security(INTERNAL_API_KEY_HEADER)) -> str:
    """
    Validates the internal service-to-service API key.

    Validates against FASTAPI_INTERNAL_API_KEY from environment/settings.

    Returns the validated API key string if valid.
    Raises HTTP 403 if the key is missing or invalid.
    """
    expected_key = settings.FASTAPI_INTERNAL_API_KEY

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Internal-API-Key header",
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )

    return api_key


# Dependency for internal service calls
InternalAPIKeyDep = Annotated[str, Depends(verify_internal_api_key)]
