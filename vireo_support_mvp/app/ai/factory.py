from app.core.config import Settings
from app.ai.base import AIProvider
from app.ai.mock import MockAIProvider
from app.ai.groq_provider import GroqAIProvider
from app.ai.gemini_provider import GeminiAIProvider
from app.ai.fallback import FallbackAIProvider

def build_provider(settings: Settings) -> AIProvider:
    provider = settings.ai_provider.lower()
    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("AI_PROVIDER=groq requires GROQ_API_KEY")
        groq_p = GroqAIProvider(settings.groq_api_key, settings.groq_model)
        if settings.gemini_api_key:
            gemini_p = GeminiAIProvider(settings.gemini_api_key, settings.gemini_model)
            return FallbackAIProvider(primary=groq_p, fallback=gemini_p)
        return groq_p
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("AI_PROVIDER=gemini requires GEMINI_API_KEY")
        gemini_p = GeminiAIProvider(settings.gemini_api_key, settings.gemini_model)
        if settings.groq_api_key:
            groq_p = GroqAIProvider(settings.groq_api_key, settings.groq_model)
            return FallbackAIProvider(primary=gemini_p, fallback=groq_p)
        return gemini_p
    return MockAIProvider()
