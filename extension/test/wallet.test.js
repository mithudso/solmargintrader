import test from 'node:test';
import assert from 'node:assert/strict';

import {
  base58Encode,
  base58Decode,
  bytesToBase64,
  base64ToBytes,
  encodeShortVec,
  decodeShortVec,
  parseTransaction,
  messageSigners,
  withSignature,
} from '../src/wallet/solana.js';

import { sealSeed, openSeed, createSessionKey, makeSigner, PendingApproval } from '../src/wallet/signer.js';

const SOL_MINT = 'So11111111111111111111111111111111111111112';
const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const SYSTEM_PROGRAM = '11111111111111111111111111111111';

/* ---------------------------------------------------------------- base58 -- */

test('base58 encodes known small values', () => {
  assert.equal(base58Encode(Uint8Array.from([0])), '1');
  assert.equal(base58Encode(Uint8Array.from([1])), '2');
  assert.equal(base58Encode(Uint8Array.from([58])), '21');
  assert.equal(base58Encode(Uint8Array.from([])), '');
});

test('leading zero bytes survive as leading ones', () => {
  // The system program is 32 zero bytes and must encode to 32 '1' characters.
  const zeros = new Uint8Array(32);
  assert.equal(base58Encode(zeros), SYSTEM_PROGRAM);
  assert.equal(base58Decode(SYSTEM_PROGRAM).length, 32);
  assert.ok(base58Decode(SYSTEM_PROGRAM).every((b) => b === 0));
});

test('real Solana mints round-trip to 32 bytes', () => {
  for (const mint of [SOL_MINT, USDC_MINT]) {
    const bytes = base58Decode(mint);
    assert.equal(bytes.length, 32, `${mint} should decode to 32 bytes`);
    assert.equal(base58Encode(bytes), mint);
  }
});

test('base58 round-trips random bytes', () => {
  for (let i = 0; i < 50; i++) {
    const bytes = crypto.getRandomValues(new Uint8Array(1 + (i % 40)));
    assert.deepEqual(base58Decode(base58Encode(bytes)), bytes);
  }
});

test('invalid base58 characters are rejected', () => {
  // '0', 'O', 'I', 'l' are excluded from the alphabet precisely to avoid confusion.
  assert.throws(() => base58Decode('0OIl'), RangeError);
});

test('base64 round-trips a buffer larger than the chunk size', () => {
  // getRandomValues caps at 65536 bytes per call; that is still twice the
  // 0x8000 chunk in bytesToBase64, so the chunking path is exercised.
  const bytes = crypto.getRandomValues(new Uint8Array(65_536));
  assert.deepEqual(base64ToBytes(bytesToBase64(bytes)), bytes);
});

/* -------------------------------------------------------------- shortvec -- */

test('shortvec round-trips across its byte boundaries', () => {
  for (const n of [0, 1, 127, 128, 255, 256, 16383, 16384]) {
    const encoded = encodeShortVec(n);
    const { value, size } = decodeShortVec(encoded, 0);
    assert.equal(value, n, `value ${n}`);
    assert.equal(size, encoded.length, `size for ${n}`);
  }
});

test('shortvec uses one byte under 128 and two at 128', () => {
  assert.equal(encodeShortVec(127).length, 1);
  assert.equal(encodeShortVec(128).length, 2);
});

test('a truncated shortvec throws instead of returning garbage', () => {
  assert.throws(() => decodeShortVec(Uint8Array.from([0x80]), 0), RangeError);
});

/* ---------------------------------------------------- transaction surgery -- */

/**
 * Build a minimal transaction with `numSigners` signature slots.
 * Only the parts this code reads are realistic; instructions are empty.
 */
function fakeTx({ versioned = true, numSigners = 1, keys }) {
  const accountKeys = keys ?? [
    crypto.getRandomValues(new Uint8Array(32)),
    crypto.getRandomValues(new Uint8Array(32)),
  ];
  const parts = [];
  if (versioned) parts.push(Uint8Array.from([0x80])); // v0
  parts.push(Uint8Array.from([numSigners, 0, 1])); // header
  parts.push(encodeShortVec(accountKeys.length));
  parts.push(...accountKeys);
  parts.push(new Uint8Array(32)); // recent blockhash
  parts.push(encodeShortVec(0)); // no instructions
  if (versioned) parts.push(encodeShortVec(0)); // no address table lookups

  const message = concat(parts);
  const tx = concat([encodeShortVec(numSigners), new Uint8Array(64 * numSigners), message]);
  return { tx, message, accountKeys };
}

function concat(chunks) {
  const total = chunks.reduce((a, c) => a + c.length, 0);
  const out = new Uint8Array(total);
  let o = 0;
  for (const c of chunks) {
    out.set(c, o);
    o += c.length;
  }
  return out;
}

test('a transaction splits into signature slots and a message', () => {
  const { tx, message } = fakeTx({});
  const parsed = parseTransaction(tx);
  assert.equal(parsed.sigCount, 1);
  assert.equal(parsed.signatures.length, 1);
  assert.deepEqual(parsed.message, message);
});

test('signers are read from a v0 message', () => {
  const { tx, accountKeys } = fakeTx({ versioned: true });
  const { signers, versioned } = messageSigners(parseTransaction(tx).message);
  assert.equal(versioned, true);
  assert.deepEqual(signers, [base58Encode(accountKeys[0])]);
});

test('signers are read from a legacy message too', () => {
  const { tx, accountKeys } = fakeTx({ versioned: false });
  const { signers, versioned } = messageSigners(parseTransaction(tx).message);
  assert.equal(versioned, false);
  assert.deepEqual(signers, [base58Encode(accountKeys[0])]);
});

test('a signature lands in the slot belonging to its pubkey', () => {
  const { tx, accountKeys } = fakeTx({ numSigners: 2 });
  const pubkey = base58Encode(accountKeys[1]);
  const sig = crypto.getRandomValues(new Uint8Array(64));
  const signed = withSignature({ txBytes: tx, pubkeyBs58: pubkey, signature: sig });

  const parsed = parseTransaction(signed);
  // Second slot filled, first still empty.
  assert.deepEqual(parsed.signatures[1], sig);
  assert.ok(parsed.signatures[0].every((b) => b === 0));
  // Input untouched: a failed sign cannot leave a half-signed transaction.
  assert.ok(parseTransaction(tx).signatures[1].every((b) => b === 0));
});

test('signing for a non-signer pubkey is refused', () => {
  const { tx } = fakeTx({});
  assert.throws(
    () =>
      withSignature({
        txBytes: tx,
        pubkeyBs58: SOL_MINT, // valid base58, not a signer of this tx
        signature: new Uint8Array(64),
      }),
    /not a required signer/,
  );
});

test('a wrong-length signature is refused', () => {
  const { tx, accountKeys } = fakeTx({});
  assert.throws(
    () =>
      withSignature({
        txBytes: tx,
        pubkeyBs58: base58Encode(accountKeys[0]),
        signature: new Uint8Array(32),
      }),
    RangeError,
  );
});

/* -------------------------------------------------------------- key vault -- */

test('a sealed seed round-trips under the right passphrase', async () => {
  const seed = crypto.getRandomValues(new Uint8Array(32));
  const vault = await sealSeed({ seed, passphrase: 'correct horse battery staple' });

  // The stored record must not contain the plaintext in any field.
  const serialised = JSON.stringify(vault);
  assert.ok(!serialised.includes(bytesToBase64(seed)));
  assert.equal(vault.kdf.iterations, 600_000);

  const opened = await openSeed({ vault, passphrase: 'correct horse battery staple' });
  assert.deepEqual(opened, seed);
});

test('a wrong passphrase fails closed without saying why', async () => {
  const seed = crypto.getRandomValues(new Uint8Array(32));
  const vault = await sealSeed({ seed, passphrase: 'right' });
  await assert.rejects(() => openSeed({ vault, passphrase: 'wrong' }), /could not unseal/);
});

test('each seal uses a fresh salt and IV', async () => {
  const seed = crypto.getRandomValues(new Uint8Array(32));
  const a = await sealSeed({ seed, passphrase: 'pw' });
  const b = await sealSeed({ seed, passphrase: 'pw' });
  assert.notEqual(a.salt, b.salt);
  assert.notEqual(a.iv, b.iv);
  assert.notEqual(a.ct, b.ct); // same plaintext must not produce the same ciphertext
});

test('a short seed is refused', async () => {
  await assert.rejects(
    () => sealSeed({ seed: new Uint8Array(16), passphrase: 'pw' }),
    RangeError,
  );
});

test('a generated session key yields a 32-byte pubkey and signs', async () => {
  const { pubkeyBs58, vault } = await createSessionKey({ passphrase: 'pw' });
  assert.equal(base58Decode(pubkeyBs58).length, 32);

  const area = {
    store: { sessionKeyVault: { pubkeyBs58, vault } },
    async get(keys) {
      const list = Array.isArray(keys) ? keys : [keys];
      return Object.fromEntries(list.map((k) => [k, this.store[k]]));
    },
    async set(obj) {
      Object.assign(this.store, obj);
    },
  };

  const signer = await makeSigner({ mode: 'full-auto', passphrase: 'pw', area });
  const sigBs58 = await signer.signMessageBs58('challenge-string');
  assert.equal(base58Decode(sigBs58).length, 64);
});

test('dry-run refuses to sign anything', async () => {
  const signer = await makeSigner({ mode: 'dry-run' });
  await assert.rejects(() => signer.signMessageBs58('x'), /never signs/);
  await assert.rejects(() => signer.signTransactionBase64('x'), /never signs/);
});

test('full-auto without an unsealed vault degrades to approval, not silent failure', async () => {
  const area = { async get() { return {}; }, async set() {} };
  const signer = await makeSigner({ mode: 'full-auto', area });
  await assert.rejects(() => signer.signMessageBs58('x'), PendingApproval);
});
