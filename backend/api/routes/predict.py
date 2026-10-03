"""Prediction routes: single and batch synchronous endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Response, Header
from backend.api.dependencies import verify_api_key, get_request_id
from backend.schemas.predict import (
    PredictRequest,
    PredictResponse,
    BatchRequest,
    BatchResponse
)
from backend.services.prediction_service import PredictionService

router = APIRouter(tags=["Core", "Evaluation"])


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Classify one support ticket",
    description="Predicts primary category, optional secondary category, and urgency flag. Requires API key."
)
async def predict_single(
    request: PredictRequest,
    response: Response,
    request_id: Optional[str] = Depends(get_request_id),
    _api_key: str = Depends(verify_api_key),
) -> PredictResponse:
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return PredictionService.predict_single(request)


@router.post(
    "/predict/batch",
    response_model=BatchResponse,
    summary="Classify 1 to 100 tickets in one synchronous call",
    description="Synchronous batch classification for 1 to 100 tickets. Requires API key."
)
async def predict_batch(
    request: BatchRequest,
    response: Response,
    request_id: Optional[str] = Depends(get_request_id),
    _api_key: str = Depends(verify_api_key),
) -> BatchResponse:
    if request_id:
        response.headers["X-Request-ID"] = request_id

    return PredictionService.predict_batch(request)
