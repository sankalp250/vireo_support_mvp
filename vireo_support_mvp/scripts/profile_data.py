"""Exploratory data-quality and visualization pass for the Vireo ticket pack.

Uses pandas for tabular profiling/cleaning, NumPy for numeric summaries, and
Matplotlib for lightweight diagnostic charts. This script is intentionally
separate from the production API so the runtime service does not need a plotting
stack just to serve requests.
"""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "artifacts" / "data_profile"
OUT.mkdir(parents=True, exist_ok=True)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ticket_logic import normalize_timestamps, apply_analysis_window


def profile_csv(path: Path) -> dict:
    df = pd.read_csv(path)
    return {
        "file": path.name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "memory_mb": round(float(df.memory_usage(deep=True).sum() / 1024**2), 3),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def main() -> None:
    tickets_path = DATA / "tickets.csv"
    tickets = pd.read_csv(tickets_path)
    profiles = [profile_csv(DATA / f) for f in [
        "tickets.csv", "agents.csv", "customers.csv", "orders.csv", "products.csv"
    ]]

    cleaned = normalize_timestamps(tickets.copy())
    in_window = apply_analysis_window(cleaned)

    numeric = in_window.select_dtypes(include=[np.number])
    numeric_summary = pd.DataFrame({
        "count": numeric.count(),
        "missing": numeric.isna().sum(),
        "mean": numeric.mean(numeric_only=True),
        "p50": numeric.quantile(0.50),
        "p95": numeric.quantile(0.95),
        "max": numeric.max(),
    }).reset_index().rename(columns={"index": "column"})
    numeric_summary.to_csv(OUT / "numeric_summary.csv", index=False)

    category_counts = in_window["category"].fillna("(missing)").value_counts().rename_axis("category").reset_index(name="tickets")
    category_counts.to_csv(OUT / "category_counts.csv", index=False)

    team_counts = in_window["assigned_team"].fillna("(missing)").value_counts().rename_axis("assigned_team").reset_index(name="tickets")
    team_counts.to_csv(OUT / "team_counts.csv", index=False)

    null_rates = (in_window.isna().mean().sort_values(ascending=False) * 100).rename("missing_pct").reset_index()
    null_rates.columns = ["column", "missing_pct"]
    null_rates.to_csv(OUT / "missingness.csv", index=False)

    monthly = (
        in_window.assign(month=in_window["created_at"].dt.to_period("M").astype(str))
        .groupby(["month", "assigned_team"], dropna=False).size()
        .reset_index(name="tickets")
    )
    monthly.to_csv(OUT / "monthly_team_volume.csv", index=False)

    # Chart 1: category volume
    plt.figure(figsize=(11, 6))
    category_counts.sort_values("tickets").plot.barh(x="category", y="tickets", legend=False)
    plt.title("Vireo ticket volume by intake category (analysis window)")
    plt.xlabel("Tickets")
    plt.ylabel("Category")
    plt.tight_layout()
    plt.savefig(OUT / "category_volume.png", dpi=160)
    plt.close()

    # Chart 2: team volume
    plt.figure(figsize=(11, 6))
    team_counts.sort_values("tickets").plot.barh(x="assigned_team", y="tickets", legend=False)
    plt.title("Vireo ticket volume by first-assigned team (analysis window)")
    plt.xlabel("Tickets")
    plt.ylabel("Team")
    plt.tight_layout()
    plt.savefig(OUT / "team_volume.png", dpi=160)
    plt.close()

    # Chart 3: monthly team volume
    pivot = monthly.pivot_table(index="month", columns="assigned_team", values="tickets", aggfunc="sum", fill_value=0)
    ax = pivot.plot(kind="bar", stacked=True, figsize=(13, 7))
    ax.set_title("Monthly Vireo support volume by first-assigned team")
    ax.set_xlabel("Month")
    ax.set_ylabel("Tickets")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUT / "monthly_team_volume.png", dpi=160)
    plt.close()

    metadata = {
        "source_rows": int(len(tickets)),
        "analysis_rows": int(len(in_window)),
        "excluded_rows": int(len(tickets) - len(in_window)),
        "profiles": profiles,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }
    (OUT / "profile_summary.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(metadata, indent=2))
    print(f"Wrote profiling artifacts to {OUT}")


if __name__ == "__main__":
    main()
