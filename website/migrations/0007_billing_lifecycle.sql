-- Quotes never grant entitlement. Only the signed canonical subscription webhook
-- updates subscriptions. Provider mutations retain their durable operation record.
CREATE TABLE billing_plan_quotes (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  subscription_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  subscription_item_id TEXT NOT NULL,
  current_plan TEXT NOT NULL CHECK (current_plan IN ('starter','advanced','unlimited')),
  target_plan TEXT NOT NULL CHECK (target_plan IN ('starter','advanced','unlimited')),
  current_price_id TEXT NOT NULL,
  target_price_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('upgrade','downgrade')),
  subscription_fingerprint TEXT NOT NULL,
  period_start INTEGER NOT NULL,
  period_end INTEGER NOT NULL,
  trial_end INTEGER,
  proration_date INTEGER NOT NULL,
  amount_due_now_cents INTEGER NOT NULL CHECK (amount_due_now_cents >= 0),
  renewal_amount_cents INTEGER NOT NULL CHECK (renewal_amount_cents > 0),
  effective_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX billing_plan_quotes_owner ON billing_plan_quotes(user_id,created_at);

CREATE TABLE billing_quote_rate (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  window_start INTEGER NOT NULL,
  requests INTEGER NOT NULL CHECK (requests > 0)
);

CREATE TABLE billing_lifecycle_operations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  quote_id TEXT UNIQUE REFERENCES billing_plan_quotes(id),
  parent_id TEXT REFERENCES billing_lifecycle_operations(id),
  kind TEXT NOT NULL CHECK (kind IN ('plan_change','undo_plan_change','cancel_subscription','undo_subscription_cancel')),
  idempotency_key TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  subscription_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('committing','applied','scheduled','pending_payment','unknown','failed','canceled')),
  stage TEXT NOT NULL,
  current_plan TEXT,
  target_plan TEXT,
  effective_at INTEGER,
  amount_due_now_cents INTEGER,
  provider_schedule_id TEXT,
  pending_expires_at INTEGER,
  requested_cancel INTEGER CHECK (requested_cancel IN (0,1)),
  last_error TEXT,
  revision INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  UNIQUE(user_id,idempotency_key)
);
CREATE INDEX billing_lifecycle_owner ON billing_lifecycle_operations(user_id,created_at);
CREATE INDEX billing_lifecycle_subscription ON billing_lifecycle_operations(subscription_id,state);

-- Expiry fences a late request owner. It does not make an unknown provider write
-- safe to repeat: the lock remains until canonical reconciliation proves outcome.
CREATE TABLE billing_lifecycle_locks (
  subscription_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL UNIQUE REFERENCES billing_lifecycle_operations(id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL
);
