"""Constants, enums, and mapping rules for TensorForge 2.0 RideEat support system."""

from enum import Enum
from typing import Dict, List


class Category(str, Enum):
    PAYMENT_REFUND = "payment_refund"
    RIDE_TRIP_ISSUE = "ride_trip_issue"
    LOST_ITEM = "lost_item"
    ORDER_MISSING_WRONG = "order_missing_wrong"
    DELIVERY_DELAY = "delivery_delay"
    FOOD_QUALITY = "food_quality"
    ACCOUNT_PROMO = "account_promo"
    SAFETY_CONDUCT = "safety_conduct"
    APP_TECHNICAL = "app_technical"
    GENERAL_INQUIRY = "general_inquiry"
    SPAM_IRRELEVANT = "spam_irrelevant"


class Team(str, Enum):
    PAYMENTS_REFUNDS = "Payments & Refunds"
    RIDE_OPERATIONS = "Ride Operations"
    LOST_FOUND = "Lost & Found"
    FOOD_OPERATIONS = "Food Operations"
    DELIVERY_OPERATIONS = "Delivery Operations"
    RESTAURANT_QUALITY = "Restaurant Quality"
    ACCOUNT_SERVICES = "Account Services"
    TRUST_SAFETY = "Trust & Safety"
    TECH_SUPPORT = "Tech Support"
    FRONT_LINE_SUPPORT = "Front-line Support"
    SPAM_FILTER = "Auto-close / Spam Filter"


class Channel(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    CALL_TRANSCRIPT = "call_transcript"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Exact Category to Team routing table per OpenAPI specification
CATEGORY_TO_TEAM: Dict[str, str] = {
    Category.PAYMENT_REFUND.value: Team.PAYMENTS_REFUNDS.value,
    Category.RIDE_TRIP_ISSUE.value: Team.RIDE_OPERATIONS.value,
    Category.LOST_ITEM.value: Team.LOST_FOUND.value,
    Category.ORDER_MISSING_WRONG.value: Team.FOOD_OPERATIONS.value,
    Category.DELIVERY_DELAY.value: Team.DELIVERY_OPERATIONS.value,
    Category.FOOD_QUALITY.value: Team.RESTAURANT_QUALITY.value,
    Category.ACCOUNT_PROMO.value: Team.ACCOUNT_SERVICES.value,
    Category.SAFETY_CONDUCT.value: Team.TRUST_SAFETY.value,
    Category.APP_TECHNICAL.value: Team.TECH_SUPPORT.value,
    Category.GENERAL_INQUIRY.value: Team.FRONT_LINE_SUPPORT.value,
    Category.SPAM_IRRELEVANT.value: Team.SPAM_FILTER.value,
}

ALL_CATEGORIES: List[str] = [cat.value for cat in Category]
ALL_TEAMS: List[str] = [team.value for team in Team]
ALL_CHANNELS: List[str] = [ch.value for ch in Channel]

# Standard error codes per OpenAPI specification
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "validation_error"
    UNAUTHORIZED = "unauthorized"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    MALFORMED_JSON = "malformed_json"
    JOB_NOT_FOUND = "job_not_found"
    JOB_NOT_READY = "job_not_ready"
    JOB_EXPIRED = "job_expired"
    TOO_MANY_JOBS = "too_many_jobs"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERRUPTED = "interrupted"
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
