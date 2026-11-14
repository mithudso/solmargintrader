import { at, base64url, decode64, exact, refuse } from './common.js';

function currentKey(env) {
  const id = env.EXECUTOR_VAULT_KEY_ID || 'v1';
  if (!/^[a-zA-Z0-9_-]{1,32}$/.test(id)) refuse('credential_vault_unavailable', 503);
  return { id, raw: env.EXECUTOR_VAULT_KEY };
}
export function vaultReady(env) {
  try { return decode64(currentKey(env).raw).length === 32; } catch { return false; }
}
async function key(env, wanted) {
  const current = currentKey(env); let raw = current.id === wanted ? current.raw : null;
  if (!raw && env.EXECUTOR_PREVIOUS_VAULT_KEYS) {
    let previous; try { previous = JSON.parse(env.EXECUTOR_PREVIOUS_VAULT_KEYS); } catch { refuse('credential_vault_unavailable', 503); }
    if (previous && Object.hasOwn(previous, wanted)) raw = previous[wanted];
  }
  let bytes; try { bytes = decode64(raw); } catch { refuse('credential_vault_unavailable', 503); }
  if (bytes.length !== 32) refuse('credential_vault_unavailable', 503);
  return crypto.subtle.importKey('raw', bytes, 'AES-GCM', false, ['encrypt', 'decrypt']);
}
function binding(owner, connectionId) {
  return new TextEncoder().encode(JSON.stringify({ userId: owner.userId, wallet: owner.wallet, connectionId, venue: 'coinbase', version: 1 }));
}
export async function seal(env, owner, connectionId, credentials) {
  const selected = currentKey(env); const nonce = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce, additionalData: binding(owner, connectionId) }, await key(env, selected.id), new TextEncoder().encode(JSON.stringify(credentials)));
  return { version: 1, keyId: selected.id, nonce: base64url(nonce), ciphertext: base64url(ciphertext), encryptedAt: at() };
}
export async function open(env, owner, connectionId, envelope) {
  if (!exact(envelope, ['version', 'keyId', 'nonce', 'ciphertext', 'encryptedAt']) || envelope.version !== 1) refuse('credential_vault_unavailable', 503);
  try {
    const plaintext = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: decode64(envelope.nonce), additionalData: binding(owner, connectionId) }, await key(env, envelope.keyId), decode64(envelope.ciphertext));
    const value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(plaintext));
    if (!exact(value, ['apiKeyName', 'privateKey'])) refuse('credential_vault_unavailable', 503);
    return value;
  } catch { refuse('credential_vault_unavailable', 503); }
}
