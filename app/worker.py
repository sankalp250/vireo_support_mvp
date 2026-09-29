import time
from datetime import datetime
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.db.models import Job, Ticket
from app.ai.factory import build_provider
from app.services.classify import classify_tickets

configure_logging(); settings=get_settings()

def run_once():
    db=SessionLocal()
    try:
        job=db.query(Job).filter(Job.status=="queued").order_by(Job.created_at).first()
        if not job: return False
        job.status="running"; job.started_at=datetime.utcnow(); db.commit()
        provider=build_provider(settings)
        done,failed=classify_tickets(db,provider,force=job.force,limit=job.requested_limit,concurrency=settings.ai_max_concurrency)
        job=db.get(Job,job.id); job.completed=done; job.failed=failed; job.status="completed" if failed==0 else "completed_with_errors"; job.finished_at=datetime.utcnow(); db.commit(); return True
    finally: db.close()

if __name__=="__main__":
    init_db()
    while True:
        worked=run_once()
        if not worked: time.sleep(2)
