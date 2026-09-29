from datetime import datetime
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.models import Ticket, Classification, ReviewLabel
from app.services.ticket_logic import is_breach


def dataframe_from_tickets(session: Session) -> pd.DataFrame:
    rows = session.execute(select(Ticket)).scalars().all()
    return pd.DataFrame([{c.name: getattr(r, c.name) for c in Ticket.__table__.columns} for r in rows])


def summary(session: Session) -> dict:
    ticket_count = session.scalar(select(func.count(Ticket.ticket_id))) or 0
    classified = session.scalar(select(func.count(Classification.id))) or 0
    reviewed = session.scalar(select(func.count(ReviewLabel.id))) or 0
    avg_conf = session.scalar(select(func.avg(Classification.confidence)))
    return {
        "tickets": ticket_count,
        "classified": classified,
        "review_labels": reviewed,
        "classification_coverage": round(classified / ticket_count, 4) if ticket_count else 0,
        "avg_confidence": round(float(avg_conf), 4) if avg_conf is not None else None,
    }


def monthly(session: Session, dimension: str) -> list[dict]:
    rows = session.execute(
        select(Ticket.created_at, Ticket.assigned_team, Ticket.channel, Ticket.ticket_id, Ticket.category.label("ticket_category"), Classification.category.label("ai_category"), Classification.recommended_team.label("ai_team"))
        .join(Classification, Classification.ticket_id == Ticket.ticket_id, isouter=True)
        .order_by(Ticket.created_at)
    ).all()
    if not rows:
        return []
    records=[]
    for r in rows:
        dt=r.created_at
        if dimension == "category":
            label=r.ticket_category or "Unclassified"
        elif dimension == "ai_category":
            label=r.ai_category or "Unclassified"
        elif dimension == "team":
            label=r.assigned_team or "Unknown"
        elif dimension == "recommended_team":
            label=r.ai_team or "Unclassified"
        else:
            raise ValueError("Unsupported dimension")
        records.append({"month": dt.strftime("%Y-%m"), "label": label})
    df=pd.DataFrame(records).groupby(["month","label"], as_index=False).size().rename(columns={"size":"count"})
    return df.to_dict(orient="records")


def transfer_metrics(session: Session) -> dict:
    rows = session.execute(select(Ticket.transfers, Ticket.source_system)).all()
    total_current = 0
    events = 0
    touched = 0
    for transfers, source in rows:
        if source != "helpdesk":
            continue
        total_current += 1
        if transfers is not None and transfers > 0:
            touched += 1
            events += int(transfers)
    return {
        "current_helpdesk_tickets": total_current,
        "tickets_with_transfer": touched,
        "transfer_rate": round(touched / total_current, 4) if total_current else 0,
        "transfer_events": events,
        "transfer_cost_inr": events * 305,
    }


def sla_metrics(session: Session) -> dict:
    rows = session.execute(select(Ticket.created_at, Ticket.first_response_at, Ticket.channel)).all()
    breaches = 0
    eligible = 0
    for created, response, channel in rows:
        if created is None or response is None:
            continue
        eligible += 1
        if is_breach(created, response, channel):
            breaches += 1
    return {"eligible": eligible, "breaches": breaches, "breach_rate": round(breaches/eligible,4) if eligible else 0, "breach_cost_inr": breaches * 350}


def evaluation(session: Session) -> dict:
    rows=session.execute(select(ReviewLabel.gold_category, Classification.category).join(Classification, Classification.ticket_id==ReviewLabel.ticket_id)).all()
    if not rows:
        return {"labels":0,"accuracy":None,"macro_f1":None}
    from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
    y_true=[r.gold_category for r in rows]
    y_pred=[r.category for r in rows]
    return {
        "labels": len(rows),
        "accuracy": round(float(accuracy_score(y_true,y_pred)),4),
        "macro_f1": round(float(f1_score(y_true,y_pred, average="macro", labels=sorted(set(y_true) | set(y_pred)), zero_division=0)),4),
        "categories": sorted(set(y_true) | set(y_pred)),
        "confusion_matrix": confusion_matrix(y_true,y_pred,labels=sorted(set(y_true) | set(y_pred))).tolist(),
    }


def headcount_signals(session: Session) -> dict:
    eligible = ["Billing", "Chat Frontline", "Email Frontline", "Logistics", "Returns Desk", "Voice Frontline"]
    raw = session.execute(select(Ticket.assigned_team)).all()
    raw_counts = {team: 0 for team in eligible}
    for (team,) in raw:
        if team in raw_counts:
            raw_counts[team] += 1
    cls = session.execute(select(Classification.recommended_team)).all()
    ai_counts = {team: 0 for team in eligible}
    for (team,) in cls:
        if team in ai_counts:
            ai_counts[team] += 1
    return {
        "eligible_teams": eligible,
        "raw_assignment": sorted(({"team":k,"tickets":v,"share":round(v/max(sum(raw_counts.values()),1),4)} for k,v in raw_counts.items()), key=lambda x:x["tickets"], reverse=True),
        "ai_recommended": sorted(({"team":k,"tickets":v,"share":round(v/max(sum(ai_counts.values()),1),4)} for k,v in ai_counts.items()), key=lambda x:x["tickets"], reverse=True),
        "note": "Escalations & Warranty is excluded from Tier-1 volume comparison per support policy."
    }
