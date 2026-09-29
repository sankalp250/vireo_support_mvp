from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session
from app.db.models import Ticket
from app.services.ticket_logic import normalize_timestamps, apply_analysis_window

TICKET_COLUMNS = [
    "ticket_id","created_at","first_response_at","resolved_at","status","channel","customer_id","order_id",
    "product_sku","category","priority","assigned_team","agent_id","transfers","csat_score","refund_amount_inr",
    "refund_reason_code","replacement_issued","customer_message","agent_notes","source_system"
]

def load_csv(session: Session, csv_path: str, replace: bool = True) -> int:
    df = pd.read_csv(csv_path)
    missing = [c for c in TICKET_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"tickets.csv missing columns: {missing}")
    df = normalize_timestamps(df[TICKET_COLUMNS])
    df = apply_analysis_window(df)
    if replace:
        session.query(Ticket).delete()
    session.bulk_save_objects([
        Ticket(**{k: (None if pd.isna(v) else v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for k,v in row.items()})
        for row in df.to_dict(orient="records")
    ])
    session.commit()
    return len(df)
