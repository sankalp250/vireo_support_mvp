import json
import time
from app.ai.base import AIProvider
from app.ai.prompts import structured_schema, SYSTEM_PROMPT
from app.schemas.classification import ClassificationResult

SCHEMA = structured_schema()

class GroqAIProvider(AIProvider):
    name = "groq"
    def __init__(self, api_key: str, model: str):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model

    def classify(self, text: str, channel: str | None = None) -> ClassificationResult:
        last_error = None
        for attempt in range(4):
            try:
                user = f"Channel: {channel or 'unknown'}\n\n{text}"
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user},
                    ],
                    temperature=0,
                    response_format={"type": "json_schema", "json_schema": SCHEMA},
                )
                content = response.choices[0].message.content or "{}"
                return ClassificationResult.model_validate(json.loads(content))
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    err_str = str(exc)
                    wait = 1.0 * (2 ** attempt)
                    if "try again in" in err_str:
                        import re
                        m = re.search(r"try again in ([\d\.]+)s", err_str)
                        wait = float(m.group(1)) + 0.5 if m else 5.0
                    elif "429" in err_str:
                        wait = max(wait, 5.0)
                    time.sleep(wait)
        raise RuntimeError(f"Groq classification failed after 4 attempts: {last_error}")
