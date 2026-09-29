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


def monthly(session: Session, dimension: str, exclude_unclassified: bool = False) -> list[dict]:
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
            if exclude_unclassified and not r.ai_category:
                continue
            label=r.ai_category or "Unclassified"
        elif dimension == "team":
            label=r.assigned_team or "Unknown"
        elif dimension == "recommended_team":
            if exclude_unclassified and not r.ai_team:
                continue
            label=r.ai_team or "Unclassified"
        else:
            raise ValueError("Unsupported dimension")
        records.append({"month": dt.strftime("%Y-%m"), "label": label})
    if not records:
        return []
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
    rows = session.execute(
        select(ReviewLabel.gold_category, Classification.category)
        .join(Classification, Classification.ticket_id == ReviewLabel.ticket_id)
    ).all()
    if not rows:
        return {"labels": 0, "accuracy": None, "macro_f1": None}

    y_true = [r[0] for r in rows]
    y_pred = [r[1] for r in rows]
    n = len(y_true)
    if n == 0:
        return {"labels": 0, "accuracy": None, "macro_f1": None}

    # Pure Python accuracy
    acc = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp) / n

    # Macro F1 across all present categories
    categories = sorted(set(y_true) | set(y_pred))
    f1_scores = []
    for c in categories:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1_scores.append(f1)

    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    # Confusion matrix
    conf_matrix = [
        [sum(1 for yt, yp in zip(y_true, y_pred) if yt == c_true and yp == c_pred) for c_pred in categories]
        for c_true in categories
    ]

    return {
        "labels": n,
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "categories": categories,
        "confusion_matrix": conf_matrix,
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
