import pandas as pd
from app.services.ticket_logic import normalize_timestamps, apply_analysis_window

def test_real_csv_window():
    df=pd.read_csv('data/tickets.csv')
    cleaned=apply_analysis_window(normalize_timestamps(df))
    assert len(cleaned)==11641
    assert cleaned.created_at.min()==pd.Timestamp('2025-01-01 08:17')
    assert cleaned.created_at.max()==pd.Timestamp('2026-06-30 23:22')
