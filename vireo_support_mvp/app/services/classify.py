from datetime import datetime
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.ai.base import AIProvider
from app.ai.prompts import PROMPT_VERSION
from app.db.models import Ticket, Classification
from app.services.ticket_logic import build_classification_text, recommended_team


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

def classify_tickets(session: Session, provider: AIProvider, force: bool=False, limit: int|None=None, concurrency: int=8) -> tuple[int,int]:
    stmt=select(Ticket).order_by(Ticket.created_at)
    tickets=session.execute(stmt).scalars().all()
    if not force:
        existing={x[0] for x in session.execute(select(Classification.ticket_id)).all()}
        tickets=[t for t in tickets if t.ticket_id not in existing]
    if limit:
        tickets=tickets[:limit]
    done=failed=0
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures={pool.submit(classify_one,t,provider):t for t in tickets}
        for fut in as_completed(futures):
            t=futures[fut]
            try:
                c=fut.result()
                if force:
                    session.execute(delete(Classification).where(Classification.ticket_id==t.ticket_id))
                session.add(c)
                done += 1
            except Exception:
                failed += 1
            if (done + failed) % 25 == 0:
                session.commit()
    session.commit()
    return done, failed
