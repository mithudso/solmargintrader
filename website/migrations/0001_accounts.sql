PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  wallet TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  stripe_customer_id TEXT UNIQUE,
  trial_used INTEGER NOT NULL DEFAULT 0,
  checkout_pending_at INTEGER
);
CREATE TABLE IF NOT EXISTS challenges (
  id TEXT PRIMARY KEY,
  wallet TEXT NOT NULL,
  message TEXT NOT NULL,
  origin TEXT NOT NULL,
  ip_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS challenges_rate ON challenges(ip_hash, created_at);
CREATE INDEX IF NOT EXISTS challenges_wallet_rate ON challenges(wallet, created_at);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS subscriptions (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  stripe_subscription_id TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  period_end INTEGER NOT NULL DEFAULT 0,
  trial_end INTEGER NOT NULL DEFAULT 0,
  stripe_created INTEGER NOT NULL DEFAULT 0,
  event_created INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS stripe_events (
  id TEXT PRIMARY KEY,
  handled_at INTEGER NOT NULL
);
-- Retain only a wallet hash after deletion to prevent recycling a used trial.
CREATE TABLE IF NOT EXISTS trial_history (
  wallet_hash TEXT PRIMARY KEY,
  used_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS bots (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  coin TEXT NOT NULL,
  strategy TEXT NOT NULL,
  venue TEXT NOT NULL CHECK (venue IN ('coinbase', 'jupiter')),
  leverage REAL NOT NULL,
  budget REAL NOT NULL,
  mode TEXT NOT NULL CHECK (mode = 'paper'),
  status TEXT NOT NULL CHECK (status IN ('configured', 'paused', 'archived')),
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS bots_owner ON bots(user_id, created_at);
