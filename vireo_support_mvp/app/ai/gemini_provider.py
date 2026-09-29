import json
from app.ai.base import AIProvider
from app.ai.prompts import SYSTEM_PROMPT, structured_schema
from app.schemas.classification import ClassificationResult

class GeminiAIProvider(AIProvider):
    name = "gemini"
    def __init__(self, api_key: str, model: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def classify(self, text: str, channel: str | None = None) -> ClassificationResult:
        user = f"Channel: {channel or 'unknown'}\n\n{text}"
        response = self.client.models.generate_content(
            model=self.model,
            contents=[SYSTEM_PROMPT, user],
            config={"response_mime_type": "application/json", "response_schema": structured_schema()["schema"], "temperature": 0},
        )
        return ClassificationResult.model_validate_json(response.text)
