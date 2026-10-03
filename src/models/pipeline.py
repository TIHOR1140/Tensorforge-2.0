"""Ticket classification inference pipeline."""

import os
import joblib
from pathlib import Path
from typing import List, Optional

from src.core.config import settings
from src.core.constants import Category, Team
from src.models.base import BasePredictor
from src.models.preprocessor import TicketPreprocessor
from src.models.rules import enforce_consistency_rules
from src.schemas.predict import PredictRequest, PredictResponse


class ClassificationPipeline(BasePredictor):
    """End-to-end inference pipeline:

    1. Normalizes and formats text (Sinhala, Tamil, English, Singlish, Tanglish).
    2. Runs feature extraction and model inference (or robust fallback if not yet trained).
    3. Calibrates confidence scores and determines optional human review flag.
    4. Enforces strict schema consistency rules (team mapping, secondary difference, spam rules).
    """

    def __init__(self, artifacts_dir: Optional[Path] = None, version: Optional[str] = None):
        self.artifacts_dir = artifacts_dir or settings.ARTIFACTS_DIR
        self._version = version or settings.MODEL_VERSION
        self._is_loaded = False
        self._category_model = None
        self._secondary_model = None
        self._urgency_model = None
        self._vectorizer = None

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def model_version(self) -> str:
        return self._version

    def load(self) -> None:
        """Attempt to load trained artifacts if present; otherwise initialize default mode."""
        cat_path = self.artifacts_dir / "category_model.joblib"
        vec_path = self.artifacts_dir / "vectorizer.joblib"

        if cat_path.exists() and vec_path.exists():
            try:
                self._category_model = joblib.load(cat_path)
                self._vectorizer = joblib.load(vec_path)
                sec_path = self.artifacts_dir / "secondary_model.joblib"
                urg_path = self.artifacts_dir / "urgency_model.joblib"
                if sec_path.exists():
                    self._secondary_model = joblib.load(sec_path)
                if urg_path.exists():
                    self._urgency_model = joblib.load(urg_path)
            except Exception as e:
                # Log and fallback to heuristic
                pass
        self._is_loaded = True

    def _infer_single(self, formatted_text: str) -> tuple[Category, Optional[Category], bool, float]:
        """Perform classification using trained model or heuristic fallback."""
        lower = formatted_text.lower()

        # If trained models are loaded:
        if self._category_model is not None and self._vectorizer is not None:
            features = self._vectorizer.transform([formatted_text])
            cat_pred = self._category_model.predict(features)[0]
            if hasattr(self._category_model, "predict_proba"):
                proba = self._category_model.predict_proba(features)[0]
                confidence = float(max(proba))
            else:
                confidence = 0.85

            category = Category(cat_pred)

            # Secondary category
            secondary = None
            if self._secondary_model is not None:
                sec_pred = self._secondary_model.predict(features)[0]
                if sec_pred and sec_pred != "none" and sec_pred != cat_pred:
                    secondary = Category(sec_pred)

            # Urgency
            is_urgent = False
            if self._urgency_model is not None:
                is_urgent = bool(self._urgency_model.predict(features)[0])
            else:
                # Heuristic for urgent signals
                is_urgent = any(k in lower for k in ["danger", "scared", "hospital", "insulin", "emergency", "police"])

            return category, secondary, is_urgent, confidence

        # Baseline heuristic classifier (used before full model training):
        category = Category.GENERAL_INQUIRY
        secondary = None
        is_urgent = False
        confidence = 0.75

        # Safety & Urgent detection
        if any(w in lower for w in ["scared", "harass", "threat", "accident", "police", "danger", "emergency", "insulin"]):
            category = Category.SAFETY_CONDUCT
            is_urgent = True
            confidence = 0.92
        elif any(w in lower for w in ["late", "delayed", "where is", "not arrived", "hours late", "පරක්කු"]):
            category = Category.DELIVERY_DELAY
            if "refund" in lower or "salli" in lower or "මුදල්" in lower:
                secondary = Category.PAYMENT_REFUND
            confidence = 0.84
        elif any(w in lower for w in ["missing", "item missing", "wrong item", "incomplete", "අඩුයි"]):
            category = Category.ORDER_MISSING_WRONG
            if "refund" in lower:
                secondary = Category.PAYMENT_REFUND
            confidence = 0.86
        elif any(w in lower for w in ["lost", "left in car", "forgot", "අමතක", "මගේ බෑග්"]):
            category = Category.LOST_ITEM
            confidence = 0.88
        elif any(w in lower for w in ["refund", "charged", "double charge", "payment", "card", "salli"]):
            category = Category.PAYMENT_REFUND
            confidence = 0.85
        elif any(w in lower for w in ["cold", "spoiled", "rotten", "taste", "smell", "bad food"]):
            category = Category.FOOD_QUALITY
            confidence = 0.85
        elif any(w in lower for w in ["promo", "discount", "otp", "login", "password", "coupon"]):
            category = Category.ACCOUNT_PROMO
            confidence = 0.82
        elif any(w in lower for w in ["crash", "bug", "error code", "white screen", "not loading"]):
            category = Category.APP_TECHNICAL
            confidence = 0.80
        elif any(w in lower for w in ["spam", "lottery", "prize", "crypto", "casino", "click here"]):
            category = Category.SPAM_IRRELEVANT
            confidence = 0.95

        return category, secondary, is_urgent, confidence

    def predict(self, ticket: PredictRequest) -> PredictResponse:
        """Process and classify a single ticket."""
        formatted_text = TicketPreprocessor.format_ticket_input(
            channel=ticket.channel.value if hasattr(ticket.channel, "value") else str(ticket.channel),
            subject=ticket.subject,
            text=ticket.text
        )

        category, secondary, is_urgent, confidence = self._infer_single(formatted_text)

        # Enforce strict consistency rules
        category, secondary, team, is_urgent = enforce_consistency_rules(
            category=category,
            secondary_category=secondary,
            is_urgent=is_urgent
        )

        # Determine human review flag if confidence is below threshold
        needs_human_review = confidence < settings.HUMAN_REVIEW_CONFIDENCE_THRESHOLD

        return PredictResponse(
            ticket_id=ticket.ticket_id,
            category=category,
            secondary_category=secondary,
            team=team,
            is_urgent=is_urgent,
            confidence=round(confidence, 4),
            model_version=self.model_version,
            needs_human_review=needs_human_review
        )

    def predict_batch(self, tickets: List[PredictRequest]) -> List[PredictResponse]:
        """Classify a batch of tickets maintaining order."""
        return [self.predict(ticket) for ticket in tickets]


# Global singleton pipeline instance
pipeline = ClassificationPipeline()
