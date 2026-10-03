"""Health check endpoint (public)."""

from fastapi import APIRouter, Response, status
from backend.models.pipeline import pipeline
from backend.schemas.health import HealthResponse

router = APIRouter(tags=["Core"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health and loaded model version",
    description="Public endpoint. Returns 200 once model is loaded, or 503 while loading."
)
async def get_health(response: Response) -> HealthResponse:
    if not pipeline.is_loaded:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="loading",
            model_version=None,
            model_loaded=False
        )

    return HealthResponse(
        status="ok",
        model_version=pipeline.model_version,
        model_loaded=True
    )
