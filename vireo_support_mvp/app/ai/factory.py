from app.core.config import Settings
from app.ai.base import AIProvider
from app.ai.mock import MockAIProvider
from app.ai.groq_provider import GroqAIProvider
from app.ai.gemini_provider import GeminiAIProvider

def build_provider(settings: Settings) -> AIProvider:
    provider = settings.ai_provider.lower()
    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("AI_PROVIDER=groq requires GROQ_API_KEY")
        return GroqAIProvider(settings.groq_api_key, settings.groq_model)
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("AI_PROVIDER=gemini requires GEMINI_API_KEY")
        return GeminiAIProvider(settings.gemini_api_key, settings.gemini_model)
    return MockAIProvider()
