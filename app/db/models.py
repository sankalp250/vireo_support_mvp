from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    customer_id: Mapped[str | None] = mapped_column(String(32))
    order_id: Mapped[str | None] = mapped_column(String(32))
    product_sku: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    priority: Mapped[str | None] = mapped_column(String(16))
    assigned_team: Mapped[str | None] = mapped_column(String(64), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(32), index=True)
    transfers: Mapped[int | None] = mapped_column(Integer)
    csat_score: Mapped[float | None] = mapped_column(Float)
    refund_amount_inr: Mapped[float | None] = mapped_column(Float)
    refund_reason_code: Mapped[str | None] = mapped_column(String(32))
    replacement_issued: Mapped[str | None] = mapped_column(String(1))
    customer_message: Mapped[str | None] = mapped_column(Text)
    agent_notes: Mapped[str | None] = mapped_column(Text)
    source_system: Mapped[str | None] = mapped_column(String(32), index=True)

Index("ix_tickets_created_channel", Ticket.created_at, Ticket.channel)

class Classification(Base):
    __tablename__ = "classifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_team: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requested_limit: Mapped[int | None] = mapped_column(Integer)
    force: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

class ReviewLabel(Base):
    __tablename__ = "review_labels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    gold_category: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
