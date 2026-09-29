import logging
from app.ai.base import AIProvider
from app.schemas.classification import ClassificationResult

logger = logging.getLogger(__name__)

class FallbackAIProvider(AIProvider):
    def __init__(self, primary: AIProvider, fallback: AIProvider):
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name
        self.model = primary.model

    def classify(self, text: str, channel: str | None = None) -> ClassificationResult:
        try:
            return self.primary.classify(text, channel)
        except Exception as exc:
            logger.warning(
                f"Primary provider {self.primary.name} failed ({exc}). Retrying with fallback {self.fallback.name}..."
            )
            return self.fallback.classify(text, channel)
