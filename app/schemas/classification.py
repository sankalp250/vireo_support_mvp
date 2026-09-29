from typing import Literal
from pydantic import BaseModel, Field, field_validator

CATEGORIES = [
    "Account & Login", "App & Firmware", "Audio Quality", "Billing & Payments",
    "Charging & Battery", "Connectivity", "Delivery & Shipping", "Other",
    "Product Enquiry", "Returns & Refunds", "Warranty & Repair",
]
FRONTLINE_TEAMS = ["Chat Frontline", "Email Frontline", "Voice Frontline"]
TEAMS = ["Billing", "Chat Frontline", "Email Frontline", "Escalations & Warranty", "Logistics", "Returns Desk", "Voice Frontline"]

class ClassificationResult(BaseModel):
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=5, max_length=600)
    needs_review: bool

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError(f"Unsupported category: {v}")
        return v

class TicketInput(BaseModel):
    ticket_id: str
    customer_message: str | None = None
    agent_notes: str | None = None
    channel: str | None = None

class JobCreate(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=50000)
    force: bool = False

class JobResponse(BaseModel):
    id: str
    status: str
    total: int
    completed: int
    failed: int

class ReviewLabelInput(BaseModel):
    ticket_id: str
    gold_category: str
    reviewer: str = "human"
    notes: str | None = None
