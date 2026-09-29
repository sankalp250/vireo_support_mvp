# Vireo Audio - Support Analytics MVP

Production-style MVP for the Vireo support-ticket assignment. It ingests the supplied ticket export, normalizes legacy timestamps, classifies ticket intent with a structured-output AI provider, maps intent to a deterministic owner team, and serves metrics through a FastAPI API plus a small web UI.

## Quick start

### 1. Create a virtualenv
```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Configure
```bash
copy .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
```

Default is `AI_PROVIDER=mock`, so the app works without an API key.
For the real AI run, set `AI_PROVIDER=groq` and `GROQ_API_KEY`, or set `AI_PROVIDER=gemini` and `GEMINI_API_KEY`.

### 3. Start
```bash
.venv/bin/python scripts/ingest.py
.venv/bin/python -m uvicorn app.main:app --reload
```
Open http://localhost:8000.

### 4. Run classification
Use the UI's **Run analysis** button, or:
```bash
curl -X POST http://localhost:8000/api/v1/jobs/classify/run -H "Content-Type: application/json" -d '{"limit":500}'
```
For the full dataset, omit `limit`.

### 5. Create a human-review sample
```bash
python scripts/create_review_sample.py
```
Manually verify `gold_category` for the sampled tickets, then run:
```bash
python scripts/evaluate.py
```

## Architecture

- FastAPI API is stateless and horizontally scalable.
- PostgreSQL is the production database; SQLite is supported for local development/tests.
- AI provider is abstracted behind `AIProvider`; Groq is the default production choice and Gemini is supported as a fallback.
- Classification output is schema-constrained and validated again with Pydantic.
- Owner-team routing is deterministic and comes from the Vireo policy, not from the LLM.
- A database-backed jobs table allows a separate worker process. In production, this worker can be replicated horizontally; a managed queue can replace the DB queue without changing the classifier contract.
- The current frontend is intentionally dependency-light static HTML/JS. It can later be replaced by React/Next.js without changing API contracts.

## Important data decisions

1. Headline analysis uses 2025-01-01 through 2026-06-30 because that is the stated assignment window.
2. Legacy `resolved_at` values are shifted +05:30 before duration analysis because policy says legacy resolution timestamps are UTC while standard reports are IST.
3. Missing legacy `transfers` values remain null and are not converted to zero.
4. Tier-2 Escalations & Warranty is kept out of direct Tier-1 volume comparisons because policy explicitly says not to compare Tier 2 with Tier 1 on volume.
5. AI category is distinct from the original intake tag. The original tag remains available for before/after analysis.
6. A human-reviewed sample is required for a defensible accuracy claim; existing intake tags should be treated as weak labels, not ground truth.

## API

- `GET /api/v1/health`
- `GET /api/v1/meta`
- `POST /api/v1/import`
- `POST /api/v1/jobs/classify`
- `POST /api/v1/jobs/classify/run`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/metrics/summary`
- `GET /api/v1/metrics/monthly?dimension=category|ai_category|team|recommended_team`
- `GET /api/v1/metrics/headcount`
- `GET /api/v1/tickets`
- `POST /api/v1/reviews`

## Production deployment

Use PostgreSQL, a managed Redis/queue if desired, secret management for API keys, a reverse proxy, TLS, structured logs, metrics, and multiple stateless API/worker replicas. Keep PII out of logs.

## Data exploration and profiling

The project uses Pandas for CSV ingestion/cleaning/aggregation, NumPy for numeric profiling, and Matplotlib for diagnostic charts. Seaborn is intentionally not a core dependency because the MVP only requires a small number of lightweight plots.

Run:

```bash
python scripts/profile_data.py
```

Generated artifacts are written to `artifacts/data_profile/`.

See `ANTIGRAVITY_PROJECT_GUIDE.md` for the complete engineering handoff, data decisions, troubleshooting guide, and production-scaling notes.
