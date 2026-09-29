# Senior review + optimization notes

### Reviewer findings fixed
- Mock/local execution previously imported live-provider-only dependencies; imports are now lazy so the default path works without API SDKs.
- Monthly analytics had an ambiguous SQLAlchemy row key; explicit labels now distinguish original ticket category from AI category/team.
- The AI schema did not initially enforce `additionalProperties=false` or the category enum; the final provider schema is strict and closed.
- Review evaluation initially treated existing intake tags as ground truth; the final workflow requires a manually verified `gold_category`.
- Job totals now respect the requested classification limit.

### Remaining production hardening
- Put authentication/authorization in front of write endpoints.
- Replace the DB-backed polling queue with a managed queue (SQS/PubSub/Redis) when throughput requires it.
- Add OpenTelemetry traces, metrics, and alerting.
- Store raw source files in object storage and use idempotent ingestion manifests.
- Add model cost/usage accounting per job.
- Add rate limits and circuit breakers for external AI providers.
