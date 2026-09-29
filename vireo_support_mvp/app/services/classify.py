from datetime import datetime
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.ai.base import AIProvider
from app.ai.prompts import PROMPT_VERSION
from app.db.models import Ticket, Classification
from app.services.ticket_logic import build_classification_text, recommended_team

logger = logging.getLogger(__name__)


def classify_one(ticket: Ticket, provider: AIProvider) -> Classification:
    start=perf_counter()
    result=provider.classify(build_classification_text(ticket.__dict__), ticket.channel)
    latency=int((perf_counter()-start)*1000)
    return Classification(
        ticket_id=ticket.ticket_id,
        provider=provider.name,
        model=provider.model,
        prompt_version=PROMPT_VERSION,
        category=result.category,
        confidence=result.confidence,
        rationale=result.rationale,
        recommended_team=recommended_team(result.category, ticket.channel),
        needs_review=result.needs_review,
        latency_ms=latency,
    )

def classify_tickets(session: Session, provider: AIProvider, force: bool=False, limit: int|None=None, concurrency: int=1) -> tuple[int,int]:
    import time
    # Prioritize tickets needing review or baseline classifications first
    if not force:
        # Upgrade baseline/unreviewed tickets first
        candidate_ids = [
            r[0] for r in session.execute(
                select(Classification.ticket_id)
                .where(Classification.provider.in_(["baseline", "mock"]) | (Classification.needs_review == True))
            ).all()
        ]
        if candidate_ids:
            stmt = select(Ticket).where(Ticket.ticket_id.in_(candidate_ids)).order_by(Ticket.created_at)
        else:
            stmt = select(Ticket).order_by(Ticket.created_at)
    else:
        stmt = select(Ticket).order_by(Ticket.created_at)

    tickets = session.execute(stmt).scalars().all()
    if limit:
        tickets = tickets[:limit]

    done = failed = 0
    # Sequential execution with rate-pacing to honor Groq / Gemini free tier limits
    for idx, t in enumerate(tickets):
        try:
            c = classify_one(t, provider)
            session.execute(delete(Classification).where(Classification.ticket_id == t.ticket_id))
            session.add(c)
            done += 1
            if done % 10 == 0:
                session.commit()
            # Pacing delay between calls to stay below Groq's 30 RPM limit
            time.sleep(1.8)
        except Exception as exc:
            failed += 1
            logger.warning(f"Classification failed for {t.ticket_id}: {exc}")
            # If rate limited, pause a little longer before next ticket
            if "429" in str(exc):
                time.sleep(3.0)

    session.commit()
    return done, failed
