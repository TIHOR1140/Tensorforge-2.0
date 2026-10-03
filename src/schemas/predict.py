"""Prediction request and response schemas conforming to official schemas."""

import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from src.core.constants import (
    Category,
    Team,
    Channel,
    CATEGORY_TO_TEAM
)


class PredictRequest(BaseModel):
    ticket_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional identifier for /predict (required for batch endpoints)."
    )
    channel: Channel = Field(
        ...,
        description="How the ticket arrived: 'email', 'chat', or 'call_transcript'."
    )
    subject: Optional[str] = Field(
        default="",
        max_length=500,
        description="Email subject line. Empty string or omitted for chat and call transcripts."
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Ticket body, chat messages, or call transcript. Must have at least 1 non-whitespace char."
    )

    @field_validator("text")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        if not re.search(r"\S", v):
            raise ValueError("Field 'text' must contain at least one non-whitespace character.")
        return v

    class Config:
        extra = "allow"


class PredictResponse(BaseModel):
    ticket_id: Optional[str] = Field(
        default=None,
        description="Echoed from the request when provided."
    )
    category: Category = Field(
        ...,
        description="Primary issue category."
    )
    secondary_category: Optional[Category] = Field(
        default=None,
        description="Second issue if ticket contains two, otherwise null. Must differ from primary category."
    )
    team: Team = Field(
        ...,
        description="Support team derived from category using the fixed table."
    )
    is_urgent: bool = Field(
        ...,
        description="Whether the ticket needs immediate human attention."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in primary category between 0 and 1."
    )
    model_version: str = Field(
        ...,
        min_length=1,
        description="Version of the model that produced the prediction."
    )
    needs_human_review: Optional[bool] = Field(
        default=None,
        description="Optional bonus field: true when system would route ticket to human triage."
    )

    @model_validator(mode="after")
    def validate_consistency_rules(self) -> "PredictResponse":
        # 1. Team mapping rule
        expected_team = CATEGORY_TO_TEAM.get(self.category)
        if self.team != expected_team:
            self.team = Team(expected_team)

        # 2. Secondary category must not equal primary category
        if self.secondary_category is not None and self.secondary_category == self.category:
            self.secondary_category = None

        # 3. Spam rule: if spam_irrelevant, is_urgent=false, secondary_category=null
        if self.category == Category.SPAM_IRRELEVANT:
            self.is_urgent = False
            self.secondary_category = None

        return self

    class Config:
        extra = "allow"


class BatchRequestTicket(PredictRequest):
    ticket_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required unique ticket identifier for batch requests."
    )


class BatchRequest(BaseModel):
    tickets: List[BatchRequestTicket] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Array of 1 to 100 tickets to classify."
    )

    @model_validator(mode="after")
    def validate_unique_ticket_ids(self) -> "BatchRequest":
        seen = set()
        for idx, ticket in enumerate(self.tickets):
            if ticket.ticket_id in seen:
                raise ValueError(f"Duplicate ticket_id '{ticket.ticket_id}' at index {idx}.")
            seen.add(ticket.ticket_id)
        return self


class BatchMeta(BaseModel):
    count: int = Field(..., description="Number of tickets processed.")
    model_version: str = Field(..., description="Model version used.")
    processing_time_ms: Optional[int] = Field(default=None, description="Time taken in milliseconds.")


class BatchResponse(BaseModel):
    predictions: List[PredictResponse] = Field(
        ...,
        description="Predictions in the same order as the submitted tickets."
    )
    meta: Optional[BatchMeta] = Field(
        default=None,
        description="Optional metadata."
    )
