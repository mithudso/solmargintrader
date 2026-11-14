-- Browser-created definitions remain paper. Only a separately signed, immutable
-- configuration and customer connection can create an automated authority.
CREATE TABLE managed_bot_challenges (
  id TEXT PRIMARY KEY,
  bot_id TEXT NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet TEXT NOT NULL,
  connection_id TEXT NOT NULL REFERENCES customer_execution_connections(id),
  client_id TEXT NOT NULL REFERENCES agent_clients(id),
  grant_id TEXT NOT NULL,
  config_json TEXT NOT NULL CHECK(json_valid(config_json)),
  config_hash TEXT NOT NULL,
  policy_json TEXT NOT NULL CHECK(json_valid(policy_json)),
  policy_hash TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE INDEX managed_challenges_owner ON managed_bot_challenges(user_id,created_at);
CREATE TABLE managed_bots (
  bot_id TEXT PRIMARY KEY REFERENCES bots(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet TEXT NOT NULL,
  connection_id TEXT NOT NULL REFERENCES customer_execution_connections(id),
  client_id TEXT NOT NULL REFERENCES agent_clients(id),
  grant_id TEXT NOT NULL REFERENCES agent_grants(id),
  config_json TEXT NOT NULL CHECK(json_valid(config_json)),
  config_hash TEXT NOT NULL,
  binding_hash TEXT NOT NULL,
  enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
  allocation_quantity TEXT NOT NULL DEFAULT '0',
  pending_intent_id TEXT REFERENCES agent_trade_intents(id),
  lease_token TEXT,
  lease_until INTEGER,
  last_reason TEXT NOT NULL DEFAULT 'awaiting_signal',
  next_tick_at INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX managed_due ON managed_bots(next_tick_at,bot_id);
CREATE TABLE managed_bot_signals (
  bot_id TEXT NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
  binding_hash TEXT NOT NULL,
  signal_id TEXT NOT NULL,
  decision_hash TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('claimed','prepared','submitted','held','complete')),
  intent_id TEXT REFERENCES agent_trade_intents(id),
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(bot_id,binding_hash,signal_id)
);
CREATE TABLE managed_bot_settlements (
  intent_id TEXT PRIMARY KEY REFERENCES agent_trade_intents(id),
  bot_id TEXT NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
  binding_hash TEXT NOT NULL,
  allocation_before TEXT NOT NULL,
  allocation_after TEXT NOT NULL,
  receipt_json TEXT NOT NULL CHECK(json_valid(receipt_json)),
  settled_at INTEGER NOT NULL
);
