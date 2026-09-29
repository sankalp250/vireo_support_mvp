import pandas as pd
from app.services.ticket_logic import normalize_timestamps, apply_analysis_window, recommended_team

def test_legacy_timestamp_shift():
    df=pd.DataFrame([{"created_at":"2025-01-01 10:00","first_response_at":"2025-01-01 10:10","resolved_at":"2025-01-01 11:00","source_system":"legacy_fd"}])
    out=normalize_timestamps(df)
    assert out.loc[0,'resolved_at']==pd.Timestamp('2025-01-01 16:30')

def test_analysis_window():
    df=pd.DataFrame({'created_at':pd.to_datetime(['2024-12-31','2025-01-01','2026-06-30','2026-07-01'])})
    out=apply_analysis_window(df)
    assert len(out)==2

def test_owner_mapping():
    assert recommended_team('Delivery & Shipping','email')=='Logistics'
    assert recommended_team('Billing & Payments','chat')=='Billing'
    assert recommended_team('Audio Quality','email')=='Email Frontline'
    assert recommended_team('Product Enquiry','social')=='Chat Frontline'
