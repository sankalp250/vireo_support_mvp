# Production architecture

```text
                ┌───────────────┐
                │ Browser / UI  │
                └───────┬───────┘
                        │ HTTPS
                ┌───────▼────────┐
                │ FastAPI API    │  stateless, horizontal replicas
                └───┬─────────┬──┘
                    │         │
            ┌───────▼───┐  ┌──▼─────────────┐
            │ PostgreSQL │  │ Job Queue       │
            │ tickets +  │  │ DB-backed now;  │
            │ results    │  │ Redis/SQS later │
            └───────┬────┘  └──────┬─────────┘
                    │              │
                    │        ┌─────▼─────┐
                    │        │ Workers   │ horizontal replicas
                    │        └─────┬─────┘
                    │              │
                    │        ┌─────▼───────────┐
                    │        │ AI Provider      │
                    │        │ Groq / Gemini    │
                    │        └──────────────────┘
                    │
             analytics queries
```

### Why this shape

The workload is asynchronous and batch-oriented, so the API should not hold an HTTP request open while 10k+ tickets are classified. A persistent job record gives the client a stable job ID, while workers can be replicated. The AI contract is provider-neutral, so model/vendor changes do not affect the rest of the system.
