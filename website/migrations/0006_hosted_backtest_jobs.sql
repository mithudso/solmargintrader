-- Long-running public-analysis jobs retain their quota reservation until a
-- durable terminal receipt is reconciled. Expiry cleanup must not drop it.
ALTER TABLE backtest_usage ADD COLUMN job_id TEXT;
CREATE TABLE hosted_backtest_jobs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  usage_id TEXT NOT NULL UNIQUE,
  idempotency_hash TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  request_json TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('queued','running','complete','failed')),
  result_hash TEXT,
  error_code TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  UNIQUE(user_id,idempotency_hash)
);
CREATE INDEX hosted_backtest_jobs_owner ON hosted_backtest_jobs(user_id,created_at,id);
CREATE INDEX hosted_backtest_jobs_pending ON hosted_backtest_jobs(state,updated_at,id);
