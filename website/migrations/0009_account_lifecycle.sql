-- A deletion fence survives transport failures. It is cleared only by the
-- verified account cascade, not by a timeout that could still erase a new key.
ALTER TABLE users ADD COLUMN deletion_token TEXT CHECK (deletion_token IS NULL OR length(deletion_token) = 36);
ALTER TABLE users ADD COLUMN deletion_requested_at INTEGER CHECK (deletion_requested_at IS NULL OR deletion_requested_at >= 0);
-- Record intent before forwarding the first credential import. A registry row
-- alone cannot reveal an interrupted import with ciphertext already persisted.
ALTER TABLE users ADD COLUMN execution_initialized_at INTEGER CHECK (execution_initialized_at IS NULL OR execution_initialized_at >= 0);
UPDATE users SET execution_initialized_at = (
  SELECT MIN(created_at) FROM customer_execution_connections WHERE user_id = users.id
) WHERE EXISTS (SELECT 1 FROM customer_execution_connections WHERE user_id = users.id);
