from datetime import datetime, timezone, timedelta
import pandas as pd

ANALYSIS_START = pd.Timestamp("2025-01-01 00:00:00")
ANALYSIS_END_EXCLUSIVE = pd.Timestamp("2026-07-01 00:00:00")


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["created_at", "first_response_at", "resolved_at"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    legacy = out.get("source_system", pd.Series(index=out.index, dtype=object)).eq("legacy_fd")
    # Policy: helpdesk timestamps are IST; migrated legacy resolution timestamps were reconstructed from UTC.
    if "resolved_at" in out.columns:
        out.loc[legacy, "resolved_at"] = out.loc[legacy, "resolved_at"] + pd.Timedelta(hours=5, minutes=30)
    return out


def apply_analysis_window(df: pd.DataFrame) -> pd.DataFrame:
    out = df[(df.created_at >= ANALYSIS_START) & (df.created_at < ANALYSIS_END_EXCLUSIVE)].copy()
    return out.reset_index(drop=True)


def build_classification_text(row: pd.Series) -> str:
    customer = str(row.get("customer_message") or "").strip()
    notes = str(row.get("agent_notes") or "").strip()
    return f"Customer message:\n{customer}\n\nAgent closing note:\n{notes}".strip()


def recommended_team(category: str, channel: str | None) -> str:
    if category == "Delivery & Shipping":
        return "Logistics"
    if category == "Billing & Payments":
        return "Billing"
    if category == "Returns & Refunds":
        return "Returns Desk"
    if category == "Warranty & Repair":
        return "Escalations & Warranty"
    if channel == "social":
        return "Chat Frontline"
    if channel == "email":
        return "Email Frontline"
    if channel == "voice":
        return "Voice Frontline"
    return "Chat Frontline"


def is_breach(created_at, first_response_at, channel: str) -> bool:
    if pd.isna(created_at) or pd.isna(first_response_at):
        return False
    targets = {"chat": 15, "voice": 120, "social": 240, "email": 480}
    mins = (first_response_at - created_at).total_seconds() / 60
    return mins > targets.get(channel, 480)
