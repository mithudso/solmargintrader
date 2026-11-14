/** Durable deletion coordination. No timeout may make a late cleanup harmless. */
export class AccountLifecycleError extends Error {
  constructor(status, code, message) { super(message || code); this.status = status; this.code = code; }
}
const fail = (status, code, message) => { throw new AccountLifecycleError(status, code, message); };
const at = () => Math.floor(Date.now() / 1000);
const query = (env, sql, ...args) => {
  if (!env.DB) fail(503, 'storage_unavailable');
  return env.DB.prepare(sql).bind(...args);
};
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
function owner(user) {
  if (!user || typeof user.id !== 'string' || !UUID.test(user.id) || typeof user.wallet !== 'string' || !user.wallet) fail(401, 'authentication_required');
}
function tokenOf(fence) {
  if (!fence || typeof fence.token !== 'string' || !UUID.test(fence.token)) fail(409, 'deletion_fence_unverified');
  return fence.token;
}
async function fencedUser(env, user, fence) {
  owner(user); const token = tokenOf(fence);
  const row = await query(env, 'SELECT id,wallet,deletion_token,deletion_requested_at,execution_initialized_at FROM users WHERE id=? AND wallet=? AND deletion_token=? AND deletion_requested_at IS NOT NULL', user.id, user.wallet, token).first();
  if (!row) fail(409, 'deletion_fence_unverified', 'Account deletion could not be verified. Refresh your account before continuing.');
  return row;
}

export async function markExecutionInitialized(env, user, options = {}) {
  owner(user); const clock = options.now || at; const timestamp = clock();
  if (!Number.isSafeInteger(timestamp) || timestamp < 0) fail(503, 'account_clock_unavailable');
  const row = await query(env, 'UPDATE users SET execution_initialized_at=COALESCE(execution_initialized_at,?) WHERE id=? AND wallet=? AND deletion_token IS NULL RETURNING id', timestamp, user.id, user.wallet).first();
  if (!row) fail(409, 'account_deleting', 'Account deletion has been requested. New account connections are disabled.');
  return { initialized: true };
}

export async function beginAccountDeletion(env, user, options = {}) {
  owner(user); const timestamp = (options.now || at)(); const checkoutSeconds = options.checkoutSeconds ?? 2100;
  if (!Number.isSafeInteger(timestamp) || timestamp < 0 || !Number.isSafeInteger(checkoutSeconds) || checkoutSeconds < 1 || checkoutSeconds > 86400) fail(503, 'account_clock_unavailable');
  const token = (options.uuid || (() => crypto.randomUUID()))();
  if (!UUID.test(token)) fail(503, 'deletion_fence_unavailable');
  // This conditional mutation is the admission barrier. Every financial/import
  // owner must check deletion_token IS NULL in its own last admission statement.
  const row = await query(env, `UPDATE users SET deletion_token=COALESCE(deletion_token,?),deletion_requested_at=COALESCE(deletion_requested_at,?)
    WHERE id=? AND wallet=? AND (checkout_pending_at IS NULL OR checkout_pending_at<?)
    AND NOT EXISTS(SELECT 1 FROM subscriptions WHERE user_id=users.id AND COALESCE(status,'unknown') NOT IN ('canceled','incomplete_expired'))
    AND NOT EXISTS(SELECT 1 FROM agent_trade_intents WHERE user_id=users.id AND state IN ('submitting','submitted','unknown'))
    AND NOT EXISTS(SELECT 1 FROM billing_lifecycle_operations WHERE user_id=users.id AND state IN ('committing','unknown','pending_payment'))
    RETURNING deletion_token,deletion_requested_at`, token, timestamp, user.id, user.wallet, timestamp - checkoutSeconds).first();
  if (row) return { token: row.deletion_token, requestedAt: row.deletion_requested_at };
  const current = await query(env, 'SELECT id,wallet,checkout_pending_at FROM users WHERE id=? AND wallet=?', user.id, user.wallet).first();
  if (!current) fail(404, 'account_not_found');
  if (await query(env, "SELECT id FROM agent_trade_intents WHERE user_id=? AND state IN ('submitting','submitted','unknown') LIMIT 1", user.id).first()) fail(409, 'trade_reconciliation_required', 'A submitted or unresolved trade must be reconciled before account deletion.');
  if (await query(env, "SELECT id FROM billing_lifecycle_operations WHERE user_id=? AND state IN ('committing','unknown','pending_payment') LIMIT 1", user.id).first()) fail(409, 'billing_reconciliation_required', 'A billing change is unresolved. Reconcile it before deleting your account.');
  if (current.checkout_pending_at !== null && current.checkout_pending_at >= timestamp - checkoutSeconds) fail(409, 'checkout_pending', 'Finish the pending Checkout session or wait for it to expire.');
  fail(409, 'cancel_subscription_first', 'Cancel your subscription before deleting your account.');
}

export async function cleanupAccountExecution(env, user, fence, services = {}) {
  const current = await fencedUser(env, user, fence);
  const exists = await query(env, 'SELECT id FROM customer_execution_connections WHERE user_id=? AND wallet=? LIMIT 1', user.id, user.wallet).first();
  if (services.configured !== true) {
    if (current.execution_initialized_at !== null || exists) fail(503, 'execution_cleanup_unavailable', 'Customer credential cleanup is unavailable. Your account deletion request is saved; retry when the service is available.');
    return { credentialsDeleted: true, executionNeverInitialized: true };
  }
  if (typeof services.revokeAll !== 'function') fail(503, 'execution_cleanup_unavailable');
  let result;
  try { result = await services.revokeAll(user); }
  catch { fail(503, 'execution_cleanup_unconfirmed', 'Credential cleanup could not be confirmed. Your deletion fence is retained; retry this deletion to reconcile it.'); }
  // Even an empty registry must cross this serialized private-owner barrier:
  // a pre-fence import might have been between seal() and its conditional INSERT.
  if (result?.revoked === true && result.pendingReconciliation === true && result.credentialsDeleted === false) fail(409, 'trade_reconciliation_required', 'A trade needs reconciliation before its credential can be erased.');
  if (!result || Object.keys(result).sort().join(',') !== 'credentialsDeleted,pendingReconciliation,revoked' || result.revoked !== true || result.credentialsDeleted !== true || result.pendingReconciliation !== false) {
    fail(503, 'execution_cleanup_unconfirmed', 'Credential cleanup could not be confirmed. Your deletion fence is retained.');
  }
  await fencedUser(env, user, fence);
  return { credentialsDeleted: true, executionNeverInitialized: false };
}

export function deletionFencePredicate(fence) {
  return { sql: 'users.deletion_token = ?', args: [tokenOf(fence)] };
}
