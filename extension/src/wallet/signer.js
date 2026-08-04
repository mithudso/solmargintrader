/**
 * Signing.
 *
 * Three honest modes, because "unattended bot" and "wallet popup per trade" are
 * mutually exclusive and pretending otherwise ships a broken default:
 *
 *   DRY_RUN    nothing is ever signed. The signer throws if asked.
 *   SEMI_AUTO  the worker prepares the transaction and queues it; a human
 *              approves each one in the dashboard. Safe, not unattended.
 *   FULL_AUTO  a dedicated session keypair signs without asking. Unattended,
 *              and the only mode where a key lives in the browser.
 *
 * FULL_AUTO key custody rules, enforced below:
 *   - the key is a DEDICATED keypair holding only grid working capital, never
 *     your main wallet
 *   - at rest it is AES-GCM encrypted under a passphrase-derived key (PBKDF2,
 *     600k iterations), with a fresh 12-byte IV per encryption
 *   - it lives in chrome.storage.local only. `.sync` would upload it
 *   - the decrypted key exists only inside a call, is never logged, never
 *     stringified, and never crosses a message boundary
 */

import {
  base58Encode,
  base58Decode,
  base64ToBytes,
  bytesToBase64,
  parseTransaction,
  withSignature,
} from './solana.js';

export const SIGNER_KIND = { NULL: 'null', PENDING: 'pending-approval', SESSION: 'session-key' };

const KDF_ITERATIONS = 600_000;
const SALT_BYTES = 16;
const IV_BYTES = 12;
const VAULT_KEY = 'sessionKeyVault';
const PENDING_KEY = 'pendingSignatures';

/** Ed25519 PKCS#8 prefix: WebCrypto will not import a bare 32-byte seed. */
const PKCS8_ED25519_PREFIX = Uint8Array.from([
  0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20,
]);

/* --------------------------------------------------------------- key vault -- */

async function deriveWrapKey(passphrase, salt) {
  const material = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(passphrase),
    'PBKDF2',
    false,
    ['deriveKey'],
  );
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: KDF_ITERATIONS, hash: 'SHA-256' },
    material,
    { name: 'AES-GCM', length: 256 },
    false, // non-extractable: the wrap key itself can never be read back out
    ['encrypt', 'decrypt'],
  );
}

/**
 * Encrypt a 32-byte Ed25519 seed for storage.
 * @returns {Promise<object>} the storable vault record — contains no plaintext
 */
export async function sealSeed({ seed, passphrase }) {
  if (seed.length !== 32) throw new RangeError(`seed must be 32 bytes, got ${seed.length}`);
  const salt = crypto.getRandomValues(new Uint8Array(SALT_BYTES));
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const key = await deriveWrapKey(passphrase, salt);
  const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, seed);
  return {
    v: 1,
    kdf: { name: 'PBKDF2', hash: 'SHA-256', iterations: KDF_ITERATIONS },
    salt: bytesToBase64(salt),
    iv: bytesToBase64(iv),
    ct: bytesToBase64(new Uint8Array(ct)),
  };
}

export async function openSeed({ vault, passphrase }) {
  const salt = base64ToBytes(vault.salt);
  const iv = base64ToBytes(vault.iv);
  const key = await deriveWrapKey(passphrase, salt);
  try {
    const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, base64ToBytes(vault.ct));
    return new Uint8Array(pt);
  } catch {
    // AES-GCM authentication failed: wrong passphrase, or the record was
    // tampered with. Do not distinguish the two.
    throw new Error('could not unseal the session key (wrong passphrase or corrupt record)');
  }
}

/* ------------------------------------------------------------------ signers -- */

class NullSigner {
  constructor() {
    this.kind = SIGNER_KIND.NULL;
  }

  async signMessageBs58() {
    throw new Error('dry-run mode never signs. Switch to semi-auto or full-auto to place real orders.');
  }

  async signTransactionBase64() {
    throw new Error('dry-run mode never signs. Switch to semi-auto or full-auto to place real orders.');
  }
}

/**
 * Queues transactions for human approval.
 *
 * The tick that hits this will fail with PendingApproval, which is correct: the
 * order is not placed, the intent is journalled as FAILED, and the next tick
 * re-plans it. Nothing is left ambiguous.
 */
class PendingApprovalSigner {
  constructor({ area = globalThis.chrome?.storage?.local } = {}) {
    this.kind = SIGNER_KIND.PENDING;
    this.area = area;
  }

  async #enqueue(payload) {
    const res = (await this.area?.get(PENDING_KEY)) ?? {};
    const queue = res[PENDING_KEY] ?? [];
    queue.push({ id: crypto.randomUUID(), createdAtMs: Date.now(), ...payload });
    await this.area?.set({ [PENDING_KEY]: queue.slice(-50) });
  }

  async signMessageBs58(challenge) {
    await this.#enqueue({ type: 'message', challenge });
    throw new PendingApproval('an authentication challenge is waiting for approval in the dashboard');
  }

  async signTransactionBase64(txBase64) {
    await this.#enqueue({ type: 'transaction', txBase64 });
    throw new PendingApproval('a transaction is waiting for approval in the dashboard');
  }
}

export class PendingApproval extends Error {
  constructor(msg) {
    super(msg);
    this.name = 'PendingApproval';
  }
}

/** Signs with a dedicated session keypair. */
class SessionKeySigner {
  /**
   * @param {Uint8Array} seed 32-byte Ed25519 seed, held only for this instance's lifetime
   */
  constructor({ seed, pubkeyBs58 }) {
    this.kind = SIGNER_KIND.SESSION;
    this.pubkeyBs58 = pubkeyBs58;
    this.#seed = seed;
  }

  #seed;

  async #privateKey() {
    const pkcs8 = new Uint8Array(PKCS8_ED25519_PREFIX.length + 32);
    pkcs8.set(PKCS8_ED25519_PREFIX, 0);
    pkcs8.set(this.#seed, PKCS8_ED25519_PREFIX.length);
    try {
      return await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'Ed25519' }, false, ['sign']);
    } catch (err) {
      throw new Error(
        `Ed25519 is unavailable in this browser's WebCrypto (${err.message}). Chrome 137+ is required for full-auto signing; use semi-auto until then.`,
      );
    } finally {
      pkcs8.fill(0);
    }
  }

  async signMessageBs58(message) {
    const key = await this.#privateKey();
    const sig = await crypto.subtle.sign('Ed25519', key, new TextEncoder().encode(message));
    return base58Encode(new Uint8Array(sig));
  }

  async signTransactionBase64(txBase64) {
    const txBytes = base64ToBytes(txBase64);
    // Statically imported: a dynamic import inside a signing call can fail in a
    // service worker that is mid-termination, leaving the order half-issued.
    const { message } = parseTransaction(txBytes);
    const key = await this.#privateKey();
    const sig = new Uint8Array(await crypto.subtle.sign('Ed25519', key, message));
    const signed = withSignature({ txBytes, pubkeyBs58: this.pubkeyBs58, signature: sig });
    return bytesToBase64(signed);
  }
}

/**
 * Derive the base58 public key for a seed.
 * Ed25519 public keys are not recoverable from the seed by arithmetic here, so
 * this round-trips through WebCrypto's JWK export.
 */
export async function pubkeyForSeed(seed) {
  const pkcs8 = new Uint8Array(PKCS8_ED25519_PREFIX.length + 32);
  pkcs8.set(PKCS8_ED25519_PREFIX, 0);
  pkcs8.set(seed, PKCS8_ED25519_PREFIX.length);
  const priv = await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'Ed25519' }, true, ['sign']);
  pkcs8.fill(0);
  const jwk = await crypto.subtle.exportKey('jwk', priv);
  // JWK 'x' is the base64url public key.
  return base58Encode(base64UrlToBytes(jwk.x));
}

function base64UrlToBytes(b64url) {
  const b64 = b64url.replaceAll('-', '+').replaceAll('_', '/');
  return base64ToBytes(b64.padEnd(Math.ceil(b64.length / 4) * 4, '='));
}

/** Generate a fresh session keypair and seal it. Returns the pubkey + vault. */
export async function createSessionKey({ passphrase }) {
  const seed = crypto.getRandomValues(new Uint8Array(32));
  try {
    const pubkeyBs58 = await pubkeyForSeed(seed);
    const vault = await sealSeed({ seed, passphrase });
    return { pubkeyBs58, vault };
  } finally {
    seed.fill(0); // do not leave the seed sitting in a heap buffer
  }
}

/**
 * Build the signer for a mode.
 *
 * FULL_AUTO needs an unsealed vault, which needs a passphrase — so it can only
 * be constructed while the user is present. Without one it degrades to
 * SEMI_AUTO rather than silently failing every tick.
 */
export async function makeSigner({ mode, passphrase, area = globalThis.chrome?.storage?.local }) {
  if (mode === 'dry-run' || !mode) return new NullSigner();

  if (mode === 'full-auto') {
    const res = (await area?.get([VAULT_KEY])) ?? {};
    const record = res[VAULT_KEY];
    if (!record?.vault || !passphrase) return new PendingApprovalSigner({ area });
    const seed = await openSeed({ vault: record.vault, passphrase });
    return new SessionKeySigner({ seed, pubkeyBs58: record.pubkeyBs58 });
  }

  return new PendingApprovalSigner({ area });
}

export { NullSigner, PendingApprovalSigner, SessionKeySigner, base58Encode, base58Decode };
