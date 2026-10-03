"""Pydantic schemas mirroring OpenAPI 3.0 specification for TensorForge 2.0."""

from src.schemas.common import *  # noqa: F401, F403
from src.schemas.error import ErrorDetail, ErrorPayload, ErrorResponse
from src.schemas.health import HealthResponse
from src.schemas.predict import (
    PredictRequest,
    PredictResponse,
    BatchRequest,
    BatchResponse,
    BatchMeta,
    BatchRequestTicket,
)
from src.schemas.batch_jobs import (
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
