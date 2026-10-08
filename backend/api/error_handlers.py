"""Centralized HTTP exception handlers conforming strictly to error_response.schema.json."""

from typing import List
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.schemas.error import ErrorDetail, ErrorPayload, ErrorResponse


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors and format into standard ErrorResponse (400 or 422)."""
    # Check if any error is due to malformed JSON decoding
    for err in exc.errors():
        err_type = str(err.get("type", ""))
        err_msg = str(err.get("msg", ""))
        if "json_invalid" in err_type or "jsondecode" in err_type.lower() or "JSON decode error" in err_msg:
            payload = ErrorResponse(
                error=ErrorPayload(
                    code="malformed_json",
                    message="Request body is not valid JSON."
                )
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=payload.model_dump(exclude_none=True)
            )

    details: List[ErrorDetail] = []
    main_msg = "Request validation failed."

    for err in exc.errors():
        loc = err.get("loc", ())
        msg = err.get("msg", "Invalid value")
        
        # Check if error relates to an item in tickets list
        index = None
        field = None
        
        # loc could be ('body', 'tickets', 3, 'text') or ('tickets', 3, 'text')
        if len(loc) >= 3 and (loc[0] == "tickets" or (len(loc) >= 4 and loc[1] == "tickets")):
            try:
                ticket_idx_pos = 1 if loc[0] == "tickets" else 2
                field_pos = 2 if loc[0] == "tickets" else 3
                index = int(loc[ticket_idx_pos])
                field = str(loc[field_pos]) if len(loc) > field_pos else None
            except (ValueError, IndexError):
                field = str(loc[-1]) if loc else None
        elif len(loc) >= 2:
            field = str(loc[-1])
        elif len(loc) == 1 and loc[0] != "body":
            field = str(loc[0])

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
    elif status_code == 400:
        code = "malformed_json"
        message = "Request body is not valid JSON."
    elif status_code == 401:
        code = "unauthorized"
        message = "Invalid or missing API key."
    elif status_code == 404:
        code = "job_not_found" if "/batch/jobs" in request.url.path else "not_found"
        message = "Requested resource not found."
    elif status_code == 405:
        code = "method_not_allowed"
        message = f"Method {request.method} not allowed on this path."
    elif status_code == 409:
        code = "job_not_ready"
        message = "Job is not yet completed."
    elif status_code == 410:
        code = "job_expired"
        message = "Job has expired and was discarded."
    elif status_code == 413:
        code = "payload_too_large"
        message = "Request payload exceeds size limit."
    elif status_code == 415:
        code = "unsupported_media_type"
        message = "Content-Type must be application/json."
    elif status_code == 429:
        code = "too_many_jobs"
        message = "Too many active or queued jobs. Please retry later."
    elif status_code == 503:
        code = "service_unavailable"
        message = "Service is temporarily unavailable or models are still loading."

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

