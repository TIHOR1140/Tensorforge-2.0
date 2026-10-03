"""Pydantic schemas mirroring OpenAPI 3.0 specification for TensorForge 2.0."""

from backend.schemas.common import *  # noqa: F401, F403
from backend.schemas.error import ErrorDetail, ErrorPayload, ErrorResponse
from backend.schemas.health import HealthResponse
from backend.schemas.predict import (
    PredictRequest,
    PredictResponse,
    BatchRequest,
    BatchResponse,
    BatchMeta,
    BatchRequestTicket,
)
from backend.schemas.batch_jobs import (
    BatchJobRequest,
    BatchJobStatus,
    BatchJobResults,
    BatchJobError,
)

__all__ = [
    "ErrorDetail",
    "ErrorPayload",
    "ErrorResponse",
    "HealthResponse",
    "PredictRequest",
    "PredictResponse",
    "BatchRequest",
    "BatchResponse",
    "BatchMeta",
    "BatchRequestTicket",
    "BatchJobRequest",
    "BatchJobStatus",
    "BatchJobResults",
    "BatchJobError",
]
