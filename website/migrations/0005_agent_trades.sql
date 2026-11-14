-- Intents are budget commitments, not evidence of a venue fill.
CREATE TABLE agent_trade_intents (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet TEXT NOT NULL,
  grant_id TEXT REFERENCES agent_grants(id) ON DELETE SET NULL,
  resource TEXT NOT NULL,
  policy_hash TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('preparing','prepared','submitting','submitted','unknown','failed','expired')),
  reservation_cents INTEGER NOT NULL CHECK (reservation_cents > 0),
  quote_id TEXT,
  quote_json TEXT,
  quote_hash TEXT,
  quote_expires_at INTEGER,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  submitted_at INTEGER,
  backend_order_id TEXT,
  last_error TEXT,
  UNIQUE(user_id, idempotency_key)
);
CREATE INDEX agent_trade_intents_owner_created ON agent_trade_intents(user_id, created_at DESC);
CREATE INDEX agent_trade_intents_grant_budget ON agent_trade_intents(grant_id, state, expires_at);
