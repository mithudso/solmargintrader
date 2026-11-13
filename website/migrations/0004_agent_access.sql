-- Public OAuth clients never receive or store a client secret. All bearer
-- credentials and authorization codes are stored only as SHA-256 hashes.
CREATE TABLE agent_clients (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  redirect_uris TEXT NOT NULL CHECK (json_valid(redirect_uris)),
  created_at INTEGER NOT NULL
);
CREATE TABLE agent_authorization_requests (
  id TEXT PRIMARY KEY,
  client_id TEXT NOT NULL REFERENCES agent_clients(id) ON DELETE CASCADE,
  redirect_uri TEXT NOT NULL,
  resource TEXT NOT NULL,
  scope TEXT NOT NULL,
  state TEXT,
  code_challenge TEXT NOT NULL,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  consumed_at INTEGER
);
CREATE INDEX agent_authorization_expiry ON agent_authorization_requests(expires_at);
CREATE TABLE agent_grants (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  client_id TEXT NOT NULL REFERENCES agent_clients(id) ON DELETE CASCADE,
  resource TEXT NOT NULL,
  scope TEXT NOT NULL,
  policy_json TEXT CHECK (policy_json IS NULL OR json_valid(policy_json)),
  policy_hash TEXT,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  revoked_at INTEGER,
  CHECK ((policy_json IS NULL) = (policy_hash IS NULL))
);
CREATE INDEX agent_grant_owner ON agent_grants(user_id,created_at);
-- A grant's identity and signed policy cannot be widened after approval.
CREATE TRIGGER agent_grant_immutable BEFORE UPDATE OF user_id,client_id,resource,scope,policy_json,policy_hash,expires_at ON agent_grants
BEGIN SELECT RAISE(ABORT, 'agent grant is immutable'); END;
CREATE TABLE agent_consent_challenges (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL REFERENCES agent_authorization_requests(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet TEXT NOT NULL,
  policy_json TEXT NOT NULL CHECK (json_valid(policy_json)),
  policy_hash TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE INDEX agent_consent_expiry ON agent_consent_challenges(expires_at);
CREATE TABLE agent_codes (
  token_hash TEXT PRIMARY KEY,
  grant_id TEXT NOT NULL REFERENCES agent_grants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  client_id TEXT NOT NULL REFERENCES agent_clients(id) ON DELETE CASCADE,
  resource TEXT NOT NULL,
  redirect_uri TEXT NOT NULL,
  code_challenge TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE INDEX agent_code_grant ON agent_codes(grant_id);
CREATE TABLE agent_access_tokens (
  token_hash TEXT PRIMARY KEY,
  grant_id TEXT NOT NULL REFERENCES agent_grants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX agent_access_grant ON agent_access_tokens(grant_id);
CREATE TABLE agent_refresh_tokens (
  token_hash TEXT PRIMARY KEY,
  grant_id TEXT NOT NULL REFERENCES agent_grants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE INDEX agent_refresh_grant ON agent_refresh_tokens(grant_id);
CREATE TABLE agent_rate_limits (
  key_hash TEXT PRIMARY KEY,
  count INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
