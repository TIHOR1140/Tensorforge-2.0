"""Batch jobs request, status, and result schemas conforming to official schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from backend.core.constants import JobStatus
from backend.schemas.predict import BatchRequestTicket, PredictResponse


class BatchJobRequest(BaseModel):
    tickets: List[BatchRequestTicket] = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Array of 1 to 5,000 tickets to classify in the asynchronous job."
    )

    @model_validator(mode="after")
    def validate_unique_ticket_ids(self) -> "BatchJobRequest":
        seen = set()
        for idx, ticket in enumerate(self.tickets):
            if ticket.ticket_id in seen:
                raise ValueError(f"Duplicate ticket_id '{ticket.ticket_id}' at index {idx}.")
            seen.add(ticket.ticket_id)
        return self


class BatchJobError(BaseModel):
    code: str = Field(..., description="Error code e.g. 'interrupted'.")
    message: str = Field(..., description="Detailed failure message.")


class BatchJobStatus(BaseModel):
    job_id: str = Field(..., description="Unique job identifier.")
    status: JobStatus = Field(..., description="Current status of the job.")
    total: int = Field(..., description="Total tickets in the job.")
    processed: int = Field(..., description="Tickets classified so far.")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp when created.")
    started_at: Optional[str] = Field(default=None, description="ISO timestamp when started.")
    finished_at: Optional[str] = Field(default=None, description="ISO timestamp when finished.")
    expires_at: Optional[str] = Field(default=None, description="ISO timestamp when results expire.")
    model_version: Optional[str] = Field(default=None, description="Model version producing predictions.")
    error: Optional[BatchJobError] = Field(default=None, description="Error details if status is failed.")


class BatchJobResults(BaseModel):
    job_id: str = Field(..., description="Unique job identifier.")
    status: str = Field(default="succeeded", description="Status must be 'succeeded'.")
    total: int = Field(..., description="Total predictions across all pages.")
    offset: int = Field(..., description="Starting index of this page.")
    limit: int = Field(..., description="Maximum items returned in this page.")
    next_offset: Optional[int] = Field(default=None, description="Offset for next page, or null if last.")
    model_version: Optional[str] = Field(default=None, description="Model version used.")
    predictions: List[PredictResponse] = Field(..., description="Page of predictions in ticket order.")
