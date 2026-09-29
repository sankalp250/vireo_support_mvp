from abc import ABC, abstractmethod
from app.schemas.classification import ClassificationResult

class AIProvider(ABC):
    name: str = "base"
    model: str = "unknown"

    @abstractmethod
    def classify(self, text: str, channel: str | None = None) -> ClassificationResult:
        raise NotImplementedError
