from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.db.models import Ticket, Classification, Job, ReviewLabel
from app.schemas.classification import JobCreate, JobResponse, ReviewLabelInput
from app.services.analytics import summary, monthly, transfer_metrics, sla_metrics, evaluation, headcount_signals
from app.services.ingest import load_csv
from app.ai.factory import build_provider
from app.services.classify import classify_tickets
from uuid import uuid4
from datetime import datetime

configure_logging()
settings=get_settings()
app=FastAPI(title="Vireo Audio Support Analytics", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
static_dir=Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", include_in_schema=False)
def root(): return FileResponse(static_dir / "index.html")

@app.get("/api/v1/health")
def health(db: Session=Depends(get_db)):
    return {"status":"ok","db":"ok"}

@app.get("/api/v1/meta")
def meta():
    return {"provider":settings.ai_provider,"model": settings.groq_model if settings.ai_provider=="groq" else settings.gemini_model if settings.ai_provider=="gemini" else "keyword-baseline","analysis_start":settings.analysis_start,"analysis_end":settings.analysis_end}

@app.post("/api/v1/import")
def import_tickets(db: Session=Depends(get_db)):
    path=Path(settings.data_dir)/"tickets.csv"
    if not path.exists(): raise HTTPException(404,"tickets.csv not found")
    count=load_csv(db,str(path),replace=True)
    return {"imported":count}

@app.post("/api/v1/jobs/classify", response_model=JobResponse)
def create_classification_job(payload: JobCreate, db: Session=Depends(get_db)):
    total=db.query(Ticket).count()
    if payload.limit: total=min(total,payload.limit)
    job=Job(id=str(uuid4()),status="queued",job_type="classify",total=total,requested_limit=payload.limit,force=payload.force)
    db.add(job); db.commit(); db.refresh(job)
    return job

@app.post("/api/v1/jobs/classify/run")
def run_classification_now(payload: JobCreate, db: Session=Depends(get_db)):
    provider=build_provider(settings)
    total=db.query(Ticket).count()
    if payload.limit: total=min(total,payload.limit)
    job=Job(id=str(uuid4()),status="running",job_type="classify",total=total,requested_limit=payload.limit,force=payload.force)
    db.add(job); db.commit()
    job.started_at=datetime.utcnow(); db.commit()
    done,failed=classify_tickets(db,provider,force=payload.force,limit=payload.limit,concurrency=settings.ai_max_concurrency)
    job=db.get(Job,job.id); job.completed=done; job.failed=failed; job.status="completed" if failed==0 else "completed_with_errors"; job.finished_at=datetime.utcnow(); db.commit()
    return {"id":job.id,"status":job.status,"total":job.total,"completed":done,"failed":failed}

@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id:str, db:Session=Depends(get_db)):
    job=db.get(Job,job_id)
    if not job: raise HTTPException(404,"job not found")
    return job

@app.get("/api/v1/metrics/summary")
def metrics_summary(db:Session=Depends(get_db)):
    return {"summary":summary(db),"transfers":transfer_metrics(db),"sla":sla_metrics(db),"evaluation":evaluation(db)}

@app.get("/api/v1/metrics/monthly")
def metrics_monthly(dimension:str=Query("category"), exclude_unclassified:bool=Query(False), db:Session=Depends(get_db)):
    if dimension not in {"category","ai_category","team","recommended_team"}:
        raise HTTPException(400,"dimension must be category, ai_category, team or recommended_team")
    return {"dimension":dimension,"data":monthly(db,dimension,exclude_unclassified=exclude_unclassified)}

@app.get("/api/v1/metrics/headcount")
def metrics_headcount(db:Session=Depends(get_db)):
    return headcount_signals(db)

@app.get("/api/v1/tickets")
def list_tickets(limit:int=100, offset:int=0, search:str|None=None, channel:str|None=None, misrouted_only:bool=False, needs_review:bool|None=None, db:Session=Depends(get_db)):
    stmt=select(
        Ticket.ticket_id,Ticket.created_at,Ticket.channel,Ticket.category,Ticket.assigned_team,
        Ticket.customer_message,Ticket.agent_notes,
        Classification.category.label('ai_category'),Classification.confidence,Classification.needs_review,
        Classification.recommended_team,Classification.rationale
    ).join(Classification,Classification.ticket_id==Ticket.ticket_id,isouter=True).order_by(Ticket.created_at)
    if channel: stmt = stmt.where(Ticket.channel == channel)
    if misrouted_only: stmt = stmt.where(Classification.recommended_team.isnot(None) & (Classification.recommended_team != Ticket.assigned_team))
    if needs_review is not None: stmt = stmt.where(Classification.needs_review == needs_review)
    if search:
        pat = f"%{search}%"
        stmt = stmt.where(Ticket.ticket_id.ilike(pat) | Ticket.customer_message.ilike(pat) | Ticket.agent_notes.ilike(pat) | Ticket.category.ilike(pat) | Classification.category.ilike(pat))
    rows=db.execute(stmt.offset(offset).limit(min(limit,500))).all()
    return [{k:getattr(r,k) for k in r._fields} for r in rows]

@app.post("/api/v1/reviews")
def add_review(payload:ReviewLabelInput, db:Session=Depends(get_db)):
    if payload.gold_category not in __import__('app.schemas.classification',fromlist=['CATEGORIES']).CATEGORIES:
        raise HTTPException(400,"invalid gold category")
    db.add(ReviewLabel(ticket_id=payload.ticket_id,gold_category=payload.gold_category,reviewer=payload.reviewer,notes=payload.notes)); db.commit()
    return {"status":"saved"}
