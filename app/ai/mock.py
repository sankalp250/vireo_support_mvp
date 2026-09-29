import re
from app.ai.base import AIProvider
from app.ai.prompts import CATEGORIES
from app.schemas.classification import ClassificationResult

KEYWORDS = {
    "Delivery & Shipping": ["delivery", "delivered", "courier", "tracking", "awb", "shipment", "dispatch", "parcel", "missing package", "not arrived", "reship"],
    "Returns & Refunds": ["refund", "return", "pickup", "returned", "money back", "cancelled", "cancellation"],
    "Billing & Payments": ["payment", "charged", "charge", "invoice", "billing", "coupon", "price", "paid", "bank", "upi", "duplicate payment"],
    "Charging & Battery": ["battery", "charge", "charging", "case won't charge", "won't turn on"],
    "Connectivity": ["bluetooth", "pair", "pairing", "connect", "disconnect", "connection"],
    "Audio Quality": ["sound", "audio", "volume", "noise", "anc", "mic", "microphone", "left earbud", "right earbud"],
    "App & Firmware": ["app", "firmware", "update", "software"],
    "Warranty & Repair": ["warranty", "repair", "rma", "replacement", "faulty", "defective", "dead on arrival", "doa"],
    "Account & Login": ["login", "log in", "password", "account", "otp"],
    "Product Enquiry": ["which model", "specification", "specs", "compatible", "availability", "feature", "buy"],
}

class MockAIProvider(AIProvider):
    name = "mock"
    model = "keyword-baseline"

    def classify(self, text: str, channel: str | None = None) -> ClassificationResult:
        low = text.lower()
        scores = {cat: 0 for cat in CATEGORIES}
        for cat, words in KEYWORDS.items():
            for w in words:
                scores[cat] += len(re.findall(re.escape(w), low))
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            best = "Other"
            conf = 0.35
        else:
            conf = min(0.98, 0.55 + 0.08 * scores[best])
            second = sorted(scores.values(), reverse=True)[1]
            if scores[best] - second == 0:
                conf = 0.55
        rationale = f"Keyword baseline matched evidence for {best}."
        return ClassificationResult(category=best, confidence=conf, rationale=rationale, needs_review=conf < 0.80)
