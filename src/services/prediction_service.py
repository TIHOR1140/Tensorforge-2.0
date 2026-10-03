"""Prediction service orchestrating classification workflow."""

from typing import List, Optional
import time

from src.models.pipeline import pipeline
from src.schemas.predict import (
    PredictRequest,
    PredictResponse,
    BatchRequest,
    BatchResponse,
    BatchMeta
)


class PredictionService:
    """Service layer coordinating preprocessing, pipeline prediction, and batch handling."""

    @staticmethod
    def predict_single(ticket: PredictRequest) -> PredictResponse:
        """Process a single ticket prediction."""
        return pipeline.predict(ticket)

    @staticmethod
    def predict_batch(batch_req: BatchRequest) -> BatchResponse:
        """Process a synchronous batch of 1 to 100 tickets."""
        start_time = time.perf_counter()
        predictions = pipeline.predict_batch(batch_req.tickets)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        meta = BatchMeta(
            count=len(predictions),
            model_version=pipeline.model_version,
            processing_time_ms=elapsed_ms
        )
        return BatchResponse(predictions=predictions, meta=meta)
