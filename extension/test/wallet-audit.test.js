import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SessionKeySigner, PendingApprovalSigner, sealSeed, openSeed, pubkeyForSeed, makeSigner,
} from '../src/wallet/signer.js';
import {
  encodeShortVec, decodeShortVec, withSignature, base58Encode, base58Decode,
  parseTransaction, messageSigners, bytesToBase64,
} from '../src/wallet/solana.js';

function transaction({ sigCount = 1, required = 1, version = 0, keys } = {}) {
  const accounts = keys ?? [new Uint8Array(32).fill(5), new Uint8Array(32).fill(6)];
  const message = Uint8Array.from([
    ...(version === null ? [] : [0x80 | version]),
    required, 0, 0, accounts.length, ...accounts.flatMap((a) => [...a]),
    ...new Uint8Array(32), 0, ...(version === null ? [] : [0]),
  ]);
  return { bytes: Uint8Array.from([sigCount, ...new Uint8Array(64 * sigCount), ...message]), message, accounts };
}

test('session signer owns immutable key material independent of caller buffer', async () => {
  const seed = new Uint8Array(32).fill(7);
  const pubkeyBs58 = await pubkeyForSeed(seed);
  const signer = new SessionKeySigner({ seed, pubkeyBs58 });
  // Mutate immediately, before asynchronous key initialization can finish.
  seed.fill(8);
  const signature = base58Decode(await signer.signMessageBs58('audit identity'));
  const publicKey = await crypto.subtle.importKey('raw', base58Decode(pubkeyBs58), 'Ed25519', false, ['verify']);
  assert.equal(await crypto.subtle.verify('Ed25519', publicKey, signature, new TextEncoder().encode('audit identity')), true);
  assert.throws(() => { signer.pubkeyBs58 = base58Encode(new Uint8Array(32)); }, TypeError);
});

test('session signer rejects short seeds and a public key that does not bind to the seed', async () => {
  assert.throws(() => new SessionKeySigner({ seed: new Uint8Array(16), pubkeyBs58: 'x' }), /32 bytes/);
  const signer = new SessionKeySigner({ seed: new Uint8Array(32).fill(7), pubkeyBs58: base58Encode(new Uint8Array(32).fill(8)) });
  await assert.rejects(() => signer.signMessageBs58('audit'), /public key.*match|does not match/i);
});

test('unseal rejects unsupported envelope metadata and invalid field lengths', async () => {
  const vault = await sealSeed({ seed: new Uint8Array(32).fill(9), passphrase: 'synthetic test' });
  for (const changed of [
    { ...vault, v: 999 },
    { ...vault, kdf: { ...vault.kdf, name: 'unsupported' } },
    { ...vault, kdf: { ...vault.kdf, hash: 'SHA-1' } },
    { ...vault, kdf: { ...vault.kdf, iterations: 1 } },
    { ...vault, salt: bytesToBase64(new Uint8Array(1)) },
    { ...vault, iv: bytesToBase64(new Uint8Array(1)) },
    { ...vault, ct: bytesToBase64(new Uint8Array(1)) },
    { ...vault, salt: 'not base64!' },
  ]) await assert.rejects(() => openSeed({ vault: changed, passphrase: 'synthetic test' }), /vault|unseal|record/i);
});

test('makeSigner refuses an unbound persisted public key', async () => {
  const vault = await sealSeed({ seed: new Uint8Array(32).fill(9), passphrase: 'synthetic test' });
  const area = { async get() { return { sessionKeyVault: { vault, pubkeyBs58: base58Encode(new Uint8Array(32).fill(8)) } }; } };
  await assert.rejects(() => makeSigner({ mode: 'full-auto', passphrase: 'synthetic test', area }), /public key.*match|does not match/i);
});

test('missing approval storage reports unavailable rather than claiming a queued request', async () => {
  const signer = new PendingApprovalSigner({ area: null });
  await assert.rejects(() => signer.signMessageBs58('audit'), (err) => {
    assert.notEqual(err.name, 'PendingApproval');
    assert.match(err.message, /storage.*unavailable|approval.*unavailable/i);
    return true;
  });
});

test('failed approval persistence never reports a pending request or mutates the old queue', async () => {
  const queue = [];
  const signer = new PendingApprovalSigner({ area: {
    async get() { return { pendingSignatures: queue }; },
    async set() { throw new Error('storage refused'); },
  } });
  await assert.rejects(() => signer.signMessageBs58('audit'), /storage refused/);
  assert.deepEqual(queue, []);
});

test('signature insertion refuses physical and message signer-count mismatch', () => {
  for (const [sigCount, required] of [[0, 1], [1, 2], [2, 1]]) {
    const { bytes, accounts } = transaction({ sigCount, required });
    const original = Uint8Array.from(bytes);
    assert.throws(() => withSignature({ txBytes: bytes, pubkeyBs58: base58Encode(accounts[0]), signature: new Uint8Array(64).fill(4) }), /signature.*count|count.*signature/i);
    assert.deepEqual(bytes, original);
  }
});

test('valid signature insertion preserves message and other signature slots', () => {
  const { bytes, message, accounts } = transaction({ sigCount: 2, required: 2 });
  bytes.fill(3, 1, 65);
  const signed = withSignature({ txBytes: bytes, pubkeyBs58: base58Encode(accounts[1]), signature: new Uint8Array(64).fill(4) });
  const parsed = parseTransaction(signed);
  assert.deepEqual(parsed.message, message);
  assert.deepEqual(parsed.signatures[0], new Uint8Array(64).fill(3));
  assert.deepEqual(parsed.signatures[1], new Uint8Array(64).fill(4));
});

test('compact-u16 encoder rejects invalid values before entering the bit-shift loop', () => {
  // Nonnegative failures first keep the unfixed baseline from reaching its negative infinite loop.
  for (const value of [NaN, Infinity, 1.5, 65536, -1, -2147483648, '1', null]) {
    assert.throws(() => encodeShortVec(value), RangeError, String(value));
  }
  assert.deepEqual(decodeShortVec(encodeShortVec(65535)), { value: 65535, size: 3 });
});

test('compact-u16 decoder rejects overflow, overlong aliases, bad offsets and truncation', () => {
  for (const bytes of [[255, 255, 127], [128, 0], [129, 0], [128, 128, 128, 0], [128]]) {
    assert.throws(() => decodeShortVec(Uint8Array.from(bytes)), RangeError, JSON.stringify(bytes));
  }
  for (const offset of [-1, 0.5, NaN, 1]) assert.throws(() => decodeShortVec(Uint8Array.of(0), offset), RangeError);
});

test('message signer parser refuses unsupported versions and truncated account tables', () => {
  for (const version of [1, 7, 127]) assert.throws(() => messageSigners(transaction({ version }).message), /version/i);
  const { message } = transaction();
  assert.throws(() => messageSigners(message.subarray(0, 20)), /truncated/i);
  assert.equal(messageSigners(transaction({ version: null }).message).versioned, false);
  assert.equal(messageSigners(message).versioned, true);
});

test('signer imports one nonextractable operational key and clears import buffers', async (t) => {
  const seed = new Uint8Array(32).fill(7);
  const pubkeyBs58 = await pubkeyForSeed(seed);
  const original = crypto.subtle.importKey;
  const buffers = [];
  const privateKeys = [];
  crypto.subtle.importKey = async function (format, data, ...rest) {
    const key = await original.call(this, format, data, ...rest);
    if (format === 'pkcs8') {
      buffers.push(data);
      privateKeys.push(key);
    }
    return key;
  };
  t.after(() => { crypto.subtle.importKey = original; });
  const signer = new SessionKeySigner({ seed, pubkeyBs58 });
  await signer.ready();
  await signer.signMessageBs58('first synthetic message');
  await signer.signMessageBs58('second synthetic message');
  assert.equal(privateKeys.length, 1);
  assert.equal(privateKeys[0].extractable, false);
  assert.ok(buffers.every((buffer) => buffer.every((byte) => byte === 0)));
});

test('makeSigner clears the actual decrypted buffer after importing its key', async (t) => {
  const seed = new Uint8Array(32).fill(7);
  const pubkeyBs58 = await pubkeyForSeed(seed);
  const vault = await sealSeed({ seed, passphrase: 'synthetic test' });
  const original = crypto.subtle.decrypt;
  const importKey = crypto.subtle.importKey;
  const passwordBuffers = [];
  let decrypted;
  crypto.subtle.importKey = function (format, data, algorithm, ...rest) {
    if (algorithm === 'PBKDF2') passwordBuffers.push(data);
    return importKey.call(this, format, data, algorithm, ...rest);
  };
  crypto.subtle.decrypt = async function (...args) {
    const buffer = await original.apply(this, args);
    decrypted = new Uint8Array(buffer);
    return buffer;
  };
  t.after(() => { crypto.subtle.decrypt = original; crypto.subtle.importKey = importKey; });
  const area = { async get() { return { sessionKeyVault: { vault, pubkeyBs58 } }; } };
  const signer = await makeSigner({ mode: 'full-auto', passphrase: 'synthetic test', area });
  assert.equal(decrypted.length, 32);
  assert.ok(decrypted.every((byte) => byte === 0));
  assert.equal(passwordBuffers.length, 1);
  assert.ok(passwordBuffers[0].every((byte) => byte === 0));
  assert.equal(base58Decode(await signer.signMessageBs58('synthetic test')).length, 64);
});

test('private-key import failure still clears transient PKCS8 buffers', async (t) => {
  const seed = new Uint8Array(32).fill(7);
  const pubkeyBs58 = await pubkeyForSeed(seed);
  const original = crypto.subtle.importKey;
  const buffers = [];
  crypto.subtle.importKey = function (format, data, ...rest) {
    if (format === 'pkcs8') {
      buffers.push(data);
      return Promise.reject(new Error('synthetic import failure'));
    }
    return original.call(this, format, data, ...rest);
  };
  t.after(() => { crypto.subtle.importKey = original; });
  const signer = new SessionKeySigner({ seed, pubkeyBs58 });
  await assert.rejects(() => signer.ready(), /unavailable/);
  await assert.rejects(() => pubkeyForSeed(seed), /synthetic import failure/);
  assert.equal(buffers.length, 2);
  assert.ok(buffers.every((buffer) => buffer.every((byte) => byte === 0)));
});

test('malformed transaction is refused before any signing operation', async (t) => {
  const seed = new Uint8Array(32).fill(7);
  const pubkeyBs58 = await pubkeyForSeed(seed);
  const signer = new SessionKeySigner({ seed, pubkeyBs58 });
  await signer.ready();
  const original = crypto.subtle.sign;
  let calls = 0;
  crypto.subtle.sign = function (...args) { calls += 1; return original.apply(this, args); };
  t.after(() => { crypto.subtle.sign = original; });
  const { bytes } = transaction({ sigCount: 0, required: 1, keys: [base58Decode(pubkeyBs58)] });
  await assert.rejects(() => signer.signTransactionBase64(bytesToBase64(bytes)), /signature.*count/);
  assert.equal(calls, 0);
});
