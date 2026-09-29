-- PostgreSQL reference schema. SQLAlchemy is the source of truth in app/db/models.py.
CREATE TABLE tickets (
  ticket_id VARCHAR(32) PRIMARY KEY,
  created_at TIMESTAMP NOT NULL,
  first_response_at TIMESTAMP,
  resolved_at TIMESTAMP,
  status VARCHAR(32) NOT NULL,
  channel VARCHAR(32) NOT NULL,
  customer_id VARCHAR(32), order_id VARCHAR(32), product_sku VARCHAR(64),
  category VARCHAR(64), priority VARCHAR(16), assigned_team VARCHAR(64), agent_id VARCHAR(32),
  transfers INTEGER, csat_score DOUBLE PRECISION, refund_amount_inr DOUBLE PRECISION,
  refund_reason_code VARCHAR(32), replacement_issued VARCHAR(1),
  customer_message TEXT, agent_notes TEXT, source_system VARCHAR(32)
);
CREATE INDEX ix_tickets_created_at ON tickets(created_at);
CREATE INDEX ix_tickets_assigned_team ON tickets(assigned_team);
CREATE TABLE classifications (
  id SERIAL PRIMARY KEY, ticket_id VARCHAR(32) UNIQUE NOT NULL REFERENCES tickets(ticket_id),
  provider VARCHAR(32) NOT NULL, model VARCHAR(128) NOT NULL, prompt_version VARCHAR(16) NOT NULL,
  category VARCHAR(64) NOT NULL, confidence DOUBLE PRECISION NOT NULL,
  rationale TEXT NOT NULL, recommended_team VARCHAR(64) NOT NULL, needs_review BOOLEAN NOT NULL DEFAULT FALSE,
  latency_ms INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_classifications_category ON classifications(category);
CREATE INDEX ix_classifications_recommended_team ON classifications(recommended_team);
CREATE TABLE jobs (
  id VARCHAR(36) PRIMARY KEY, status VARCHAR(24) NOT NULL, job_type VARCHAR(32) NOT NULL,
  total INTEGER NOT NULL DEFAULT 0, requested_limit INTEGER, force BOOLEAN NOT NULL DEFAULT FALSE, completed INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
  error TEXT, created_at TIMESTAMP NOT NULL, started_at TIMESTAMP, finished_at TIMESTAMP
);
CREATE TABLE review_labels (
  id SERIAL PRIMARY KEY, ticket_id VARCHAR(32) NOT NULL REFERENCES tickets(ticket_id),
  gold_category VARCHAR(64) NOT NULL, reviewer VARCHAR(128) NOT NULL, notes TEXT, created_at TIMESTAMP NOT NULL
);
