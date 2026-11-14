-- Existing subscriptions fail closed until a canonical Stripe webhook maps their Price.
ALTER TABLE subscriptions ADD COLUMN plan_id TEXT CHECK (plan_id IN ('starter','advanced','unlimited'));
CREATE TABLE backtest_usage (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('reserved','complete')),
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX backtest_usage_owner_day ON backtest_usage(user_id,day,state,expires_at);
-- Lease keys are SHA-256 subscription identifiers; no wallet/customer data.
CREATE TABLE subscription_webhook_leases (
  subscription_key TEXT PRIMARY KEY,
  owner_token TEXT NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX subscription_webhook_leases_expiry ON subscription_webhook_leases(expires_at);
