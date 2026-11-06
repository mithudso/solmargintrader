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
 *   - plaintext seed bytes exist only during bounded initialization; the signer
 *     retains a non-extractable CryptoKey, never raw seed bytes
 */

import {
  base58Encode,
  base58Decode,
  base64ToBytes,
  bytesToBase64,
  transactionSigningContext,
  withSignature,
} from './solana.js';

export const SIGNER_KIND = { NULL: 'null', PENDING: 'pending-approval', SESSION: 'session-key' };

const KDF_ITERATIONS = 600_000;
const SALT_BYTES = 16;
const IV_BYTES = 12;
const VAULT_KEY = 'sessionKeyVault';
const PENDING_KEY = 'pendingSignatures';
const KEY_BINDING_MESSAGE = new TextEncoder().encode('solmargintrader session key binding v1');

/** Ed25519 PKCS#8 prefix: WebCrypto will not import a bare 32-byte seed. */
const PKCS8_ED25519_PREFIX = Uint8Array.from([
  0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20,
]);

/* --------------------------------------------------------------- key vault -- */

function validateSeed(seed) {
  if (!(seed instanceof Uint8Array) || seed.length !== 32) throw new RangeError('seed must be 32 bytes');
}

async function deriveWrapKey(passphrase, salt) {
  const passphraseBytes = new TextEncoder().encode(passphrase);
  let material;
  try {
    material = await crypto.subtle.importKey('raw', passphraseBytes, 'PBKDF2', false, ['deriveKey']);
  } finally {
    passphraseBytes.fill(0);
  }
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
  validateSeed(seed);
  if (typeof passphrase !== 'string') throw new TypeError('passphrase must be a string');
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
  if (!vault || typeof vault !== 'object' || Array.isArray(vault) || vault.v !== 1 ||
      vault.kdf?.name !== 'PBKDF2' || vault.kdf?.hash !== 'SHA-256' ||
      vault.kdf?.iterations !== KDF_ITERATIONS || typeof passphrase !== 'string') {
    throw new Error('unsupported or corrupt session key vault record');
  }
  let salt, iv, ct;
  try {
    const decode = (value, length) => {
      if (typeof value !== 'string' || value.length !== 4 * Math.ceil(length / 3)) throw new Error();
      const bytes = base64ToBytes(value);
      if (bytes.length !== length || bytesToBase64(bytes) !== value) throw new Error();
      return bytes;
    };
    salt = decode(vault.salt, SALT_BYTES);
    iv = decode(vault.iv, IV_BYTES);
    ct = decode(vault.ct, 32 + 16); // 32-byte seed plus the AES-GCM authentication tag.
  } catch {
    throw new Error('unsupported or corrupt session key vault record');
  }
  const key = await deriveWrapKey(passphrase, salt);
  try {
    const seed = new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct));
    if (seed.length !== 32) {
      seed.fill(0);
      throw new Error('invalid seed');
    }
    return seed;
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
    if (!this.area || typeof this.area.get !== 'function' || typeof this.area.set !== 'function') {
      throw new Error('approval storage is unavailable; no request was queued');
    }
    const res = (await this.area.get(PENDING_KEY)) ?? {};
    const existing = res[PENDING_KEY] ?? [];
    if (!Array.isArray(existing)) throw new Error('approval storage is corrupt; no request was queued');
    const queue = [...existing];
    queue.push({ id: crypto.randomUUID(), createdAtMs: Date.now(), ...payload });
    await this.area.set({ [PENDING_KEY]: queue.slice(-50) });
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
   * @param {Uint8Array} seed Borrowed 32-byte seed; captured synchronously into a temporary owned copy.
   */
  constructor({ seed, pubkeyBs58 }) {
    validateSeed(seed);
    if (typeof pubkeyBs58 !== 'string' || base58Decode(pubkeyBs58).length !== 32) {
      throw new RangeError('public key must encode 32 bytes');
    }
    this.kind = SIGNER_KIND.SESSION;
    Object.defineProperty(this, 'pubkeyBs58', { value: pubkeyBs58, enumerable: true });
    this.#keyPromise = this.#importKey(Uint8Array.from(seed));
    // A directly constructed signer may not be used immediately. Keep an init
    // failure handled until ready/sign awaits the original rejected promise.
    this.#keyPromise.catch(() => {});
  }

  #keyPromise;

  async #importKey(seed) {
    const pkcs8 = new Uint8Array(PKCS8_ED25519_PREFIX.length + 32);
    pkcs8.set(PKCS8_ED25519_PREFIX, 0);
    pkcs8.set(seed, PKCS8_ED25519_PREFIX.length);
    seed.fill(0);
    let key;
    try {
      key = await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'Ed25519' }, false, ['sign']);
    } catch (err) {
      throw new Error(
        `Ed25519 is unavailable in this browser's WebCrypto (${err.message}). Chrome 137+ is required for full-auto signing; use semi-auto until then.`,
      );
    } finally {
      pkcs8.fill(0);
    }
    // Validate identity without exporting any private key material. A changed
    // public field beside an intact vault must not produce invalid signatures.
    const publicKey = await crypto.subtle.importKey('raw', base58Decode(this.pubkeyBs58), 'Ed25519', false, ['verify']);
    const proof = await crypto.subtle.sign('Ed25519', key, KEY_BINDING_MESSAGE);
    if (!await crypto.subtle.verify('Ed25519', publicKey, proof, KEY_BINDING_MESSAGE)) {
      throw new Error('session key public key does not match the seed');
    }
    return key;
  }

  async ready() {
    await this.#keyPromise;
    return this;
  }

  async signMessageBs58(message) {
    const key = await this.#keyPromise;
    const sig = await crypto.subtle.sign('Ed25519', key, new TextEncoder().encode(message));
    return base58Encode(new Uint8Array(sig));
  }

  async signTransactionBase64(txBase64) {
    const txBytes = base64ToBytes(txBase64);
    // Statically imported: a dynamic import inside a signing call can fail in a
    // service worker that is mid-termination, leaving the order half-issued.
    const { message } = transactionSigningContext({ txBytes, pubkeyBs58: this.pubkeyBs58 });
    const key = await this.#keyPromise;
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
  validateSeed(seed);
  const pkcs8 = new Uint8Array(PKCS8_ED25519_PREFIX.length + 32);
  pkcs8.set(PKCS8_ED25519_PREFIX, 0);
  pkcs8.set(seed, PKCS8_ED25519_PREFIX.length);
  let jwk;
  try {
    const priv = await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'Ed25519' }, true, ['sign']);
    jwk = await crypto.subtle.exportKey('jwk', priv);
  } finally {
    pkcs8.fill(0);
  }
  // JWK 'x' is the base64url public key.
  const publicPart = jwk.x;
  delete jwk.d;
  return base58Encode(base64UrlToBytes(publicPart));
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
    let signer;
    try {
      signer = new SessionKeySigner({ seed, pubkeyBs58: record.pubkeyBs58 });
    } finally {
      seed.fill(0);
    }
    return signer.ready();
  }

  return new PendingApprovalSigner({ area });
}

export { NullSigner, PendingApprovalSigner, SessionKeySigner, base58Encode, base58Decode };
