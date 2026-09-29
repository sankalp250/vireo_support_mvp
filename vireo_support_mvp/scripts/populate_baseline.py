import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.db.models import Ticket, Classification
from app.ai.mock import MockAIProvider
from app.services.ticket_logic import build_classification_text, recommended_team

def main():
    db = SessionLocal()
    mock = MockAIProvider()
    existing_ids = {x[0] for x in db.query(Classification.ticket_id).all()}
    tickets = db.query(Ticket).filter(~Ticket.ticket_id.in_(existing_ids)).all()
    print(f"Unclassified tickets to baseline: {len(tickets)}")

    t0 = time.time()
    batch_size = 500
    total = len(tickets)
    for i in range(0, total, batch_size):
        chunk = tickets[i:i + batch_size]
        new_cls = []
        for t in chunk:
            res = mock.classify(build_classification_text(t.__dict__), t.channel)
            new_cls.append(Classification(
                ticket_id=t.ticket_id,
                provider="baseline",
                model="keyword-baseline",
                prompt_version="v1.0",
                category=res.category,
                confidence=res.confidence,
                rationale=res.rationale,
                recommended_team=recommended_team(res.category, t.channel),
                needs_review=res.needs_review,
                latency_ms=1
            ))
        db.bulk_save_objects(new_cls)
        db.commit()
        print(f"Committed chunk {min(i + batch_size, total)}/{total}")

    print(f"Done in {round(time.time() - t0, 2)}s!")
    total_cls = db.query(Classification).count()
    print(f"Total classifications now in DB: {total_cls}")
    db.close()

if __name__ == "__main__":
    main()
