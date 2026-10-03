"""API dependencies: authentication, security, and request tracing."""

import secrets
from typing import Optional
from fastapi import Header, HTTPException, status
from src.core.config import settings
from src.schemas.error import ErrorResponse, ErrorPayload


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """Validate API key via X-API-Key or Bearer token header.

    Per spec:
    - If API_KEY environment variable is not configured, refuse with 401.
    - Constant-time comparison using secrets.compare_digest.
    - Returns 401 with WWW-Authenticate header on failure.
    """
    expected_key = settings.API_KEY

    # If no API key configured on server, refuse all requests rather than run open
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Server API_KEY is not configured."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_key: Optional[str] = None
    if x_api_key:
        provided_key = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()

    if not provided_key or not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid or missing API key."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return provided_key


async def get_request_id(
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
) -> Optional[str]:
    """Echo incoming X-Request-ID header."""
    return x_request_id
