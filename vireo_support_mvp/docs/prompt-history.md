# Prompt history

## V1
Classify a support ticket into one allowed category and return only the category.

## V2
Added explicit category definitions and instructed the model to use both customer_message and agent_notes.

## V3 (kept)
Added structured JSON output with category, calibrated confidence, rationale, and needs_review. The provider enforces a strict JSON schema; Pydantic validates the response again.

## Discarded approach
Free-form categories were discarded because even small wording differences would fragment monthly reporting. LLM-generated owner-team values were also discarded: routing is deterministic from the support policy.
