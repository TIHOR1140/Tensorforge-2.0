"""Error response schemas strictly conforming to error_response.schema.json."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    index: Optional[int] = Field(
        default=None,
        description="Zero-based index of the failing item in tickets (batch requests only)."
    )
    field: Optional[str] = Field(
        default=None,
        description="The field causing the issue."
    )
    issue: Optional[str] = Field(
        default=None,
        description="Description of the issue."
    )


class ErrorPayload(BaseModel):
    code: str = Field(
        ...,
        description="Short machine-readable error code."
    )
    message: str = Field(
        ...,
        description="Human-readable explanation. Do not include stack traces."
    )
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Optional list of field-level problems."
    )


class ErrorResponse(BaseModel):
    error: ErrorPayload = Field(
        ...,
        description="The error payload containing code, message, and details."
    )
