"""Centralized HTTP exception handlers conforming strictly to error_response.schema.json."""

from typing import List
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.schemas.error import ErrorDetail, ErrorPayload, ErrorResponse


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors and format into standard ErrorResponse (422)."""
    details: List[ErrorDetail] = []
    main_msg = "Request validation failed."

    for err in exc.errors():
        loc = err.get("loc", ())
        msg = err.get("msg", "Invalid value")
        
        # Check if error relates to an item in tickets list
        index = None
        field = None
        
        # loc could be ('body', 'tickets', 3, 'text')
        if len(loc) >= 4 and loc[1] == "tickets":
            try:
                index = int(loc[2])
                field = str(loc[3])
            except (ValueError, IndexError):
                field = str(loc[-1])
        elif len(loc) >= 2:
            field = str(loc[-1])

        details.append(ErrorDetail(index=index, field=field, issue=msg))

    if details and details[0].issue:
        main_msg = details[0].issue

    payload = ErrorResponse(
        error=ErrorPayload(
            code="validation_error",
            message=main_msg,
            details=details if details else None
        )
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload.model_dump(exclude_none=True)
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Format all HTTP exceptions into JSON ErrorResponse (never raw HTML)."""
    headers = getattr(exc, "headers", None)
    status_code = exc.status_code

    code = "error"
    message = str(exc.detail)

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "error")
        message = exc.detail.get("message", "An error occurred.")
    elif status_code == 401:
        code = "unauthorized"
        message = "Invalid or missing API key."
    elif status_code == 404:
        code = "not_found"
        message = "Requested endpoint or resource not found."
    elif status_code == 405:
        code = "method_not_allowed"
        message = f"Method {request.method} not allowed on this path."
    elif status_code == 413:
        code = "payload_too_large"
        message = "Request payload exceeds size limit."
    elif status_code == 415:
        code = "unsupported_media_type"
        message = "Content-Type must be application/json."
    elif status_code == 429:
        code = "rate_limited"
        message = "Too many active or queued jobs. Please retry later."

    payload = ErrorResponse(
        error=ErrorPayload(
            code=code,
            message=message
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(exclude_none=True),
        headers=headers
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled server exceptions."""
    payload = ErrorResponse(
        error=ErrorPayload(
            code="internal_error",
            message="An unexpected server error occurred."
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload.model_dump(exclude_none=True)
    )
