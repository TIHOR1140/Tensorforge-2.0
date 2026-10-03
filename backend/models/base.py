"""Abstract base predictor interface."""

from abc import ABC, abstractmethod
from typing import List
from backend.schemas.predict import PredictRequest, PredictResponse


class BasePredictor(ABC):
    """Abstract interface that all ticket classification models must implement."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True if model weights and components are fully loaded."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the current model version identifier."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load model artifacts and initialize inference components."""
        pass

    @abstractmethod
    def predict(self, ticket: PredictRequest) -> PredictResponse:
        """Perform inference on a single ticket."""
        pass

    @abstractmethod
    def predict_batch(self, tickets: List[PredictRequest]) -> List[PredictResponse]:
        """Perform inference on a batch of tickets."""
        pass
