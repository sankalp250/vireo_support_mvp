PROMPT_VERSION = "v3"
CATEGORIES = [
    "Account & Login", "App & Firmware", "Audio Quality", "Billing & Payments",
    "Charging & Battery", "Connectivity", "Delivery & Shipping", "Other",
    "Product Enquiry", "Returns & Refunds", "Warranty & Repair",
]
SYSTEM_PROMPT = """You classify Vireo Audio support tickets.
Choose exactly one category from the allowed taxonomy. Use BOTH the customer message and the agent closing note.
The agent note can contain the final diagnosis or action and should resolve ambiguity in the opening message.
Do not invent categories. Confidence is your calibrated confidence in the selected category, from 0 to 1.
Set needs_review=true when the evidence is ambiguous, conflicting, or weak (roughly below 0.80 confidence).
Return only JSON matching the supplied schema.
Allowed categories: """ + ", ".join(CATEGORIES)

def structured_schema() -> dict:
    return {
        "name": "support_ticket_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": CATEGORIES},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "rationale": {"type": "string", "minLength": 5, "maxLength": 600},
                "needs_review": {"type": "boolean"},
            },
            "required": ["category", "confidence", "rationale", "needs_review"],
            "additionalProperties": False,
        },
    }
