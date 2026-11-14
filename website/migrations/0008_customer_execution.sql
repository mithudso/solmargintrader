-- Terminal venue outcomes carry cumulative consumption separately from open risk.
CREATE TABLE agent_trade_intents_v2 (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet TEXT NOT NULL,
  grant_id TEXT REFERENCES agent_grants(id) ON DELETE SET NULL,
  resource TEXT NOT NULL,
  policy_hash TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('preparing','prepared','submitting','submitted','unknown','failed','expired','filled','canceled')),
  reservation_cents INTEGER NOT NULL CHECK (reservation_cents > 0),
  quote_id TEXT, quote_json TEXT, quote_hash TEXT, quote_expires_at INTEGER,
  expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
  submitted_at INTEGER, backend_order_id TEXT, last_error TEXT,
  consumed_cents INTEGER NOT NULL DEFAULT 0 CHECK (consumed_cents >= 0),
  fill_json TEXT CHECK (fill_json IS NULL OR json_valid(fill_json)),
  reconciled_at INTEGER,
  executor_admission_id TEXT,
  executor_admitted_at INTEGER,
  UNIQUE(user_id,idempotency_key)
);
INSERT INTO agent_trade_intents_v2
  (id,user_id,wallet,grant_id,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,
   quote_id,quote_json,quote_hash,quote_expires_at,expires_at,created_at,updated_at,submitted_at,backend_order_id,last_error)
SELECT id,user_id,wallet,grant_id,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,
   quote_id,quote_json,quote_hash,quote_expires_at,expires_at,created_at,updated_at,submitted_at,backend_order_id,last_error
FROM agent_trade_intents;
DROP TABLE agent_trade_intents;
ALTER TABLE agent_trade_intents_v2 RENAME TO agent_trade_intents;
CREATE INDEX agent_trade_intents_owner_created ON agent_trade_intents(user_id,created_at DESC);
CREATE INDEX agent_trade_intents_grant_budget ON agent_trade_intents(grant_id,state,expires_at);

-- Credentials remain encrypted in the executor's private Durable Object storage.
CREATE TABLE customer_execution_connections (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet TEXT NOT NULL,
  venue TEXT NOT NULL CHECK (venue = 'coinbase'),
  credential_fingerprint TEXT NOT NULL,
  portfolio_id TEXT NOT NULL,
  request_key_hash TEXT,
  request_hash TEXT,
  created_at INTEGER NOT NULL,
  verified_at INTEGER NOT NULL,
  revoked_at INTEGER
);
CREATE INDEX customer_execution_connections_owner ON customer_execution_connections(user_id,venue,created_at DESC);
CREATE UNIQUE INDEX customer_execution_connections_active_credential ON customer_execution_connections(credential_fingerprint) WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX customer_execution_connections_active_venue ON customer_execution_connections(user_id,venue) WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX customer_execution_connections_request ON customer_execution_connections(user_id,request_key_hash) WHERE request_key_hash IS NOT NULL;
