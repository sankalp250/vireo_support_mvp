# Vireo Audio Support Analytics MVP - Antigravity Project Guide

This document is the implementation handoff for an AI coding agent (for example, Antigravity) that needs to understand, run, test, extend, or debug this repository without having to infer the business requirements from scattered files.

It is intentionally separate from `README.md`: the README is the quick-start document; this file explains **what the product is supposed to do, why it is designed this way, what data rules are non-negotiable, where failures can happen, and how to resolve them**.

---

## 1. What this project is

Vireo Audio is evaluating a support-analytics vendor. The source pack contains 18 months of support tickets (Jan 2025-Jun 2026), a roster, customer/order/product reference data, the support operating policy, and the existing email conversation.

The core business problem is:

> The existing intake categories are weak labels. The client wants trustworthy monthly workload by category and team so that a headcount decision can be made using evidence rather than the existing tags alone.

The product therefore does four things:

1. **Ingest and clean the source export.**
2. **Classify the actual issue** using the customer opening message plus the agent closing note.
3. **Map the classified issue to a support owner team deterministically** using the Vireo policy.
4. **Turn the results into operational metrics**: monthly volume, transfer cost, SLA-breach exposure, classification quality, and headcount signals.

This is an MVP for the assignment. It is deliberately small enough to run locally but structured so the API and worker can scale horizontally.

---

## 2. Source files and what each one means

The complete client pack is copied under `client_pack/` unchanged.

| File | Purpose |
|---|---|
| `tickets.csv` | Primary ticket-level dataset |
| `agents.csv` | Agent roster; an agent may have multiple assignment rows |
| `customers.csv` | Customer reference data |
| `orders.csv` | Order reference data |
| `products.csv` | Product/cost/warranty reference data |
| `support-policy.pdf` | SLA, cost, refund, ownership, shift and reporting rules |
| `email-thread.txt` | Client context and competing views about headcount |
| `README.txt` | Field definitions and source-system notes |

`data/` is the application runtime copy of the data. `client_pack/` is the preserved handoff copy.

The assignment also mentions `submission-form.md`, but that file was not included in the uploaded pack used to build this repository. Do not invent one. Add the real file when it is available.

---

## 3. Analysis window and non-negotiable data decisions

### 3.1 Headline analysis window

Use:

- Start: `2025-01-01 00:00:00` inclusive
- End: `2026-07-01 00:00:00` exclusive

The source CSV contains 11,780 rows, of which 11,641 fall inside the requested assignment window. The remaining 139 rows are older than Jan 2025 and are excluded from headline metrics.

Do not silently change this window.

### 3.2 Legacy timestamp normalization

The support policy states that normal helpdesk timestamps are displayed/exported in IST, while migrated legacy resolution timestamps were reconstructed from a UTC legacy event log.

Before handle-time analysis:

```text
legacy resolved_at -> +05:30 -> normalized IST
```

Do not shift `created_at` or `first_response_at` using this rule.

### 3.3 Legacy transfers

`transfers` did not exist in Freshdesk. Blank legacy values mean **unknown/not available**, not zero.

Never convert legacy transfer blanks to `0` merely to make arithmetic easier.

### 3.4 Existing category vs AI category

Keep both fields:

- `category` = original intake tag
- `Classification.category` = AI-derived issue category

The original tag is a weak label and must not be treated as ground truth for model evaluation.

### 3.5 Tier 2 comparison

`Escalations & Warranty` is Tier 2. The policy explicitly says Tier 2 should not be compared with Tier 1 on ticket-volume metrics.

Therefore the headcount signal endpoint excludes Tier 2 from the direct Tier 1 volume comparison.

---

## 4. What the AI is responsible for

The model receives:

```text
Customer message
+
Agent closing note
```

and returns a strict object:

```json
{
  "category": "Delivery & Shipping",
  "confidence": 0.94,
  "rationale": "The customer reports a missing delivery and the agent note confirms a courier issue.",
  "needs_review": false
}
```

Allowed categories:

- `Account & Login`
- `App & Firmware`
- `Audio Quality`
- `Billing & Payments`
- `Charging & Battery`
- `Connectivity`
- `Delivery & Shipping`
- `Other`
- `Product Enquiry`
- `Returns & Refunds`
- `Warranty & Repair`

The schema is constrained at the provider where supported and validated again through Pydantic.

### Important architectural rule

The LLM does **not** decide the final owner team.

After classification, deterministic business logic maps the category/channel to a team. This prevents the model from changing operational ownership based on phrasing.

Examples:

```text
Delivery & Shipping -> Logistics
Billing & Payments -> Billing
Returns & Refunds -> Returns Desk
Warranty & Repair -> Escalations & Warranty
social -> Chat Frontline
email  -> Email Frontline
voice  -> Voice Frontline
other Tier-1 general cases -> Chat Frontline
```

---

## 5. Libraries and why they are used

### Pandas - YES, core dependency

Pandas is used for:

- reading CSV files
- column validation
- timestamp parsing
- date-window filtering
- missing-value handling
- tabular aggregation
- monthly summaries
- exploratory profiling
- evaluation preparation

Main files:

- `app/services/ingest.py`
- `app/services/ticket_logic.py`
- `app/services/analytics.py`
- `scripts/create_review_sample.py`
- `scripts/evaluate.py`
- `scripts/profile_data.py`

### NumPy - YES, used in the profiling layer

NumPy is used directly by `scripts/profile_data.py` for numeric summaries and percentile statistics.

It is not artificially forced into the API layer just to say that NumPy is present.

### Matplotlib - YES, used for data-understanding/QA charts

`matplotlib` is used by `scripts/profile_data.py` to generate:

- category-volume chart
- team-volume chart
- monthly team-volume chart

These charts are diagnostic artifacts for understanding the data and checking the pipeline. They do not make the API depend on plotting code.

### Seaborn - intentionally NOT in the core dependency set

Seaborn is not required for this MVP. Matplotlib provides the small number of diagnostic charts we need, which avoids another runtime dependency.

Do not add Seaborn just for the sake of using it.

### Scikit-learn - evaluation

Used for:

- accuracy
- macro F1
- confusion matrix

This is only used once human-reviewed labels are available.

### FastAPI - API layer

Used for the HTTP service and dashboard backend.

### SQLAlchemy - persistence

Used for PostgreSQL in production and SQLite for local development/tests.

### Pydantic - contracts

Used for:

- environment settings
- request/response models
- AI output validation

---

## 6. Data exploration / cleaning workflow

Run:

```bash
python scripts/profile_data.py
```

This produces:

```text
artifacts/data_profile/
  profile_summary.json
  numeric_summary.csv
  missingness.csv
  category_counts.csv
  team_counts.csv
  monthly_team_volume.csv
  category_volume.png
  team_volume.png
  monthly_team_volume.png
```

The current source profile is:

```text
Tickets:    11,780 source rows
Window:     11,641 analysis rows
Excluded:      139 rows
Customers:   9,500
Orders:     15,000
Products:       14
Agents:         44
```

Before adding a new metric, run this profiling pass and verify that the metric is calculated over the intended rows.

---

## 7. Runtime architecture

```text
Browser
  |
  v
FastAPI API  <-----------------------------+
  |                                         |
  +--> PostgreSQL / SQLite                  |
  |                                         |
  +--> Job table ----------------------> Worker
                                            |
                                            v
                                      AIProvider
                                      /        \
                                   Groq       Gemini
                                            |
                                            v
                                     Classification
                                            |
                                            v
                                  deterministic routing
                                            |
                                            v
                                        Metrics
```

The current UI is static HTML/JS/CSS and calls the API. It intentionally has no React build step, making the assignment easier to run on a clean machine.

For a larger product, the static UI can be replaced by React/Next.js without changing the API contracts.

---

## 8. Repository structure

```text
vireo_support_mvp/
├── app/
│   ├── ai/                    # AI provider abstraction + implementations
│   ├── core/                  # config + logging
│   ├── db/                    # SQLAlchemy models/session
│   ├── schemas/               # Pydantic API/AI contracts
│   ├── services/              # ingest, classification, analytics, routing
│   ├── static/                # lightweight browser UI
│   ├── main.py                # FastAPI app
│   └── worker.py              # background job worker
│
├── scripts/
│   ├── ingest.py
│   ├── profile_data.py
│   ├── create_review_sample.py
│   └── evaluate.py
│
├── tests/
├── data/                      # runtime copy of client pack
├── client_pack/               # preserved original client files
├── artifacts/data_profile/    # generated EDA artifacts
├── docs/
├── ANTIGRAVITY_PROJECT_GUIDE.md
├── README.md
├── schema.sql
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 9. Local startup - exact sequence

### Option A: Python + SQLite (recommended for first run)

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/profile_data.py
python scripts/ingest.py
python -m uvicorn app.main:app --reload
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/profile_data.py
python scripts/ingest.py
python -m uvicorn app.main:app --reload
```

Then open:

```text
http://localhost:8000
```

Health check:

```text
GET http://localhost:8000/api/v1/health
```

### Default AI provider

The default is:

```text
AI_PROVIDER=mock
```

This makes local setup possible without an API key.

### Option B: Docker

```bash
docker compose up --build
```

The Docker compose file starts PostgreSQL, API, and worker containers.

---

## 10. Live AI configuration

### Groq

`.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key
GROQ_MODEL=openai/gpt-oss-20b
```

The implementation uses structured JSON Schema output with strict mode for the supported model.

### Gemini

`.env`:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.8-flash
```

The provider remains interchangeable because both implementations satisfy the same `AIProvider` interface.

Never commit `.env` or API keys.

---

## 11. How the classification job works

There are two routes:

### Queue a job

```http
POST /api/v1/jobs/classify
Content-Type: application/json

{"limit": 500}
```

### Run immediately

```http
POST /api/v1/jobs/classify/run
Content-Type: application/json

{"limit": 500}
```

Omit `limit` for the full analysis set.

The classifier uses bounded concurrency and retries. In production, the DB-backed job table can be replaced with a managed queue without changing the AI provider or classification schema.

---

## 12. Validation workflow

Never claim AI accuracy from the original `category` column.

Instead:

1. Generate a review sample.
2. A human assigns `gold_category`.
3. Store the labels in `review_labels`.
4. Run:

```bash
python scripts/evaluate.py
```

5. Report:

```text
Accuracy
Macro F1
Confusion matrix
Number of reviewed tickets
Review rate / escalation rate
```

### Why this matters

The client explicitly says the intake tags are weak and agents rarely retag. Agreement with those labels would not prove the AI is correct.

---

## 13. Where errors are likely to happen

### Error: `tickets.csv not found`

Check:

```text
DATA_DIR
```

and confirm:

```text
<data-dir>/tickets.csv
```

exists.

### Error: CSV missing columns

`app/services/ingest.py` checks every required ticket column. Do not rename source fields unless the source pack itself changed.

### Error: negative handle time

Check the legacy timestamp normalization. Do not delete rows to hide the issue. The policy explains the UTC/IST difference.

### Error: transfer rate suddenly jumps

Check whether legacy blank `transfers` were converted to zero or whether the current-helpdesk filter was removed.

### Error: AI returns an invalid category

The provider response should be constrained to the allowed enum. Pydantic then validates the response again. Do not silently coerce arbitrary text into a category.

### Error: AI response is malformed JSON

For strict structured-output providers, inspect:

- provider/model ID
- JSON Schema
- `additionalProperties: false`
- all schema fields marked required

If strict structured output is unavailable, keep the parser defensive and retry with the failure reason.

### Error: rate limit / HTTP 429

Do not simply increase concurrency.

Reduce:

```text
AI_MAX_CONCURRENCY
```

and keep retries bounded.

For large-scale operation, add a real queue and provider rate limiter.

### Error: classification is slow

First check:

- concurrency
- token length of ticket text
- retries
- provider latency
- batch size

Then consider request batching where supported.

### Error: the dashboard shows no AI data

Check:

1. `/api/v1/health`
2. `/api/v1/import`
3. classification job status
4. database row count
5. provider configuration
6. API logs

### Error: evaluation returns no metrics

That normally means `review_labels` has not been populated yet.

Create and manually label a review sample first.

---

## 14. Privacy and logging rules

Ticket/customer data can contain personal information.

Do not log:

- customer names
- phone numbers
- email addresses
- full customer messages
- API keys
- raw provider requests/responses in production

Use ticket IDs and aggregate metrics in logs instead.

---

## 15. Production scaling path

The assignment does not need millions of users today, but the code should not block that future.

### Current MVP

```text
FastAPI
SQLite/Postgres
DB-backed jobs
one worker process
```

### Next scale

```text
Load balancer
  |
  +-- API replica 1
  +-- API replica 2
  +-- API replica N
          |
       PostgreSQL
          |
       Redis / managed queue
          |
       worker pool
          |
      provider limiter
          |
      Groq / Gemini
```

Add later, not now:

- Redis/managed queue
- Alembic migrations
- object storage for exports
- authentication/RBAC
- rate limiting at the API gateway
- OpenTelemetry
- metrics/alerts
- dead-letter queue
- provider circuit breaker
- PII redaction

Do not add these just to make the assignment look complicated.

---

## 16. Database model

### `tickets`

Stores normalized source data.

Important indexes:

- `created_at`
- `assigned_team`
- `source_system`

### `classifications`

Stores AI output and routing decision.

Important fields:

```text
ticket_id
provider
model
prompt_version
category
confidence
rationale
needs_review
recommended_team
latency_ms
created_at
```

### `jobs`

Tracks batch execution:

```text
queued
running
completed
completed_with_errors
failed
```

### `review_labels`

Stores human ground truth:

```text
ticket_id
gold_category
reviewer
notes
created_at
```

---

## 17. API contract summary

```text
GET  /api/v1/health
GET  /api/v1/meta
POST /api/v1/import
POST /api/v1/jobs/classify
POST /api/v1/jobs/classify/run
GET  /api/v1/jobs/{job_id}
GET  /api/v1/metrics/summary
GET  /api/v1/metrics/monthly?dimension=...
GET  /api/v1/metrics/headcount
GET  /api/v1/tickets
POST /api/v1/reviews
```

Supported monthly dimensions:

```text
category
ai_category
team
recommended_team
```

---

## 18. Business metrics already wired into the MVP

The policy gives these planning values:

- Chat: Rs 210/contact
- Email: Rs 260/contact
- Voice callback: Rs 520/contact
- Social: Rs 240/contact
- Internal transfer: Rs 305/transfer
- Agent: Rs 165/hour
- SLA breach credit: Rs 350/ticket

The analytics layer exposes:

- ticket count
- AI classification coverage
- average AI confidence
- transfer rate/events/cost
- SLA breach rate/cost
- evaluation metrics once labels exist
- Tier-1 headcount signals

Use these figures for business cases; do not invent different cost assumptions.

---

## 19. Prompt development history

The prompt progression is deliberate.

### V1

Basic one-category classification.

### V2

Added category definitions and instructed the model to use both customer and agent text.

### V3 - current

Added:

- strict schema
- confidence
- rationale
- `needs_review`
- no invented categories

Keep prompt versions in `app/ai/prompts.py` and document changes in `docs/prompt-history.md`.

If the prompt changes, update the version identifier. Do not overwrite history.

---

## 20. Reviewer checklist before submission

Run:

```bash
pytest -q
python scripts/profile_data.py
python scripts/ingest.py
```

Then:

1. Start the API.
2. Check `/api/v1/health`.
3. Import tickets.
4. Run a small mock classification batch.
5. Inspect several classifications manually.
6. Generate a review sample.
7. Label the sample.
8. Run evaluation.
9. Run the full live classification only after the small batch is correct.
10. Export/report the final metrics.

Before recording the demo, make sure the screen shows:

- the prompt
- the classification output
- what changed between prompt versions
- what was discarded
- the dashboard/business result

---

## 21. Known limitations of this handoff

This repository is a strong working MVP, but it is not the final business submission until the live AI run and human-reviewed evaluation are completed.

Specifically:

- The local mock provider is fully testable without an API key.
- A real Groq or Gemini API key is required for the final live classification run.
- The `gold_category` evaluation labels must be created by a human reviewer.
- The actual one-page Priya memo and assignment submission form are not considered complete until the final AI metrics exist.
- A real `submission-form.md` was not included in the source pack received for this build.

Do not fabricate final accuracy, F1, or business savings numbers before those steps are complete.

---

## 22. What Antigravity should do first

When continuing this project, follow this order:

```text
1. Read this file.
2. Read client_pack/README.txt.
3. Read client_pack/email-thread.txt.
4. Read client_pack/support-policy.pdf.
5. Inspect tickets.csv.
6. Run scripts/profile_data.py.
7. Run pytest -q.
8. Run the mock pipeline on a small batch.
9. Verify AI output against the schema.
10. Only then make changes to the production code.
```

If a requested change conflicts with the business rules in the client pack, stop and surface the conflict instead of silently choosing a different rule.
