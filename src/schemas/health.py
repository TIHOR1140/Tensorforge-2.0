"""Health response schema strictly conforming to health_response.schema.json."""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(
        ...,
        description="'ok' when ready to serve, or 'loading' while the model is loading."
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Loaded model version, or null while loading."
    )
    model_loaded: Optional[bool] = Field(
        default=None,
        description="true once the model is ready."
    )
