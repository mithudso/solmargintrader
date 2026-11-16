import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { PublicKey } from '@solana/web3.js';
import { secp256k1 } from '@noble/curves/secp256k1';
import { keccak_256 } from '@noble/hashes/sha3';
import { parseCurrentPrice, verifyPythSignature, checkCurrentTime, verifyEconomicDeltas, verifyProgramPins } from '../current-open.mjs';

const PYTH = new PublicKey('pytd2yyk641x7ak7mkaasSJVXh6YYZnC7wTmtgAyxPt');
const TREASURY = new PublicKey('Gx4MBPb1vqZLJajZmsKLg8fGw9ErhoKsR8LeKcCKFyak');
const now = 1794840000;
const privateKey = Buffer.alloc(32, 7); // Synthetic test signer; never a wallet key.
function fixture(feed = 1) {
  const data = Buffer.alloc(133);
  Buffer.from('3d22759b4b227bd0', 'hex').copy(data);
  data.writeUInt32LE(121, 8); data.writeUInt32LE(1296547300, 12);
  data.writeUInt16LE(50, 81); data.writeUInt32LE(2479346549, 83);
  data.writeBigUInt64LE(BigInt(now) * 1000000n, 87); data[95] = 3; data[96] = 1;
  data.writeUInt32LE(feed, 97); data[101] = 4; data[102] = 0;
  data.writeBigInt64LE(6500000000000n, 103); data[111] = 4; data.writeInt16LE(-8, 112);
  data[114] = 5; data.writeBigInt64LE(10000n, 115); data[123] = 12; data[124] = 1;
  data.writeBigUInt64LE(BigInt(now) * 1000000n, 125);
  const sig = secp256k1.sign(keccak_256(data.subarray(83)), privateKey);
  Buffer.from(sig.toCompactRawBytes()).copy(data, 16); data[80] = sig.recovery;
  const storage = Buffer.alloc(381);
  createHash('sha256').update('account:Storage').digest().subarray(0, 8).copy(storage);
  TREASURY.toBuffer().copy(storage, 40); storage.writeBigUInt64LE(1n, 72); storage[281] = 1;
  const pub = secp256k1.getPublicKey(privateKey, false);
  Buffer.from(keccak_256(pub.subarray(1))).subarray(12).copy(storage, 282);
  storage.writeBigInt64LE(BigInt(now + 30), 302);
  return { data, storage: { owner: PYTH, executable: false, data: storage } };
}

test('parses and cryptographically authenticates the exact supported Lazer feed', () => {
  const { data, storage } = fixture(); const p = parseCurrentPrice(data, 'BTC', now);
  assert.equal(p.feed, 1); assert.equal(p.oraclePrice, 65000000000000000n);
  assert.equal(verifyPythSignature(p, storage, now), 1n);
  checkCurrentTime(p, { maxOracleAgeSecs: 10, maxOracleFutureSecs: 3 }, now);
});

test('rejects an authentic signed payload for the wrong market', () => {
  const { data, storage } = fixture(66);
  assert.equal(verifyPythSignature(parseCurrentPrice(data, 'ZEC', now), storage, now), 1n);
  assert.throws(() => parseCurrentPrice(data, 'BTC', now), /invalid_price_feed/);
});

test('rejects malformed lengths, magic, property order and price constraints', () => {
  for (const [offset, value] of [[0, 0], [8, 120], [12, 0], [81, 49], [83, 0], [95, 1], [96, 2], [101, 3], [102, 4], [111, 0], [114, 0], [123, 0], [124, 0]]) {
    const { data } = fixture(); data[offset] = value;
    assert.throws(() => parseCurrentPrice(data, 'BTC', now), /current_invalid_price/);
  }
  for (const change of [d => d.writeBigInt64LE(0n, 103), d => d.writeInt16LE(-7, 112), d => d.writeBigInt64LE(-1n, 115), d => d.writeBigUInt64LE(1n, 125)]) {
    const { data } = fixture(); change(data);
    assert.throws(() => parseCurrentPrice(data, 'BTC', now), /current_invalid_price_value/);
  }
});

test('rejects modified signatures, untrusted or expired signers and altered storage', () => {
  for (const change of [
    (d, _s) => { d[25] ^= 1; },
    (_d, s) => { s.data[282] ^= 1; },
    (_d, s) => { s.data.writeBigInt64LE(BigInt(now), 302); },
    (_d, s) => { s.data[40] ^= 1; },
    (_d, s) => { s.owner = new PublicKey(Buffer.alloc(32, 2)); },
    (_d, s) => { s.data[281] = 3; },
  ]) {
    const { data, storage } = fixture(); change(data, storage);
    assert.throws(() => verifyPythSignature(parseCurrentPrice(data, 'BTC', now), storage, now), /current_(invalid_pyth|untrusted_pyth)/);
  }
});

test('enforces stale and future feed limits and malformed settings', () => {
  const p = parseCurrentPrice(fixture().data, 'BTC', now), settings = { maxOracleAgeSecs: 10, maxOracleFutureSecs: 3 };
  assert.doesNotThrow(() => checkCurrentTime(p, settings, now + 10));
  assert.throws(() => checkCurrentTime(p, settings, now + 11), /price_stale_or_future/);
  assert.throws(() => checkCurrentTime(p, settings, now - 4), /price_stale_or_future/);
  assert.throws(() => checkCurrentTime(p, { ...settings, maxOracleAgeSecs: NaN }, now), /invalid_clock_settings/);
});

function economicFixture() {
  const owner = new PublicKey(Buffer.alloc(32, 6)), pool = new PublicKey(Buffer.alloc(32, 9));
  const token = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
  const mint = new PublicKey('JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD');
  const yolo = new PublicKey('yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA');
  function account(authority, amount) { const data = Buffer.alloc(165); mint.toBuffer().copy(data); authority.toBuffer().copy(data, 32); data.writeBigUInt64LE(amount, 64); data[108] = 1; return { owner: token, data, executable: false, lamports: 1488440 }; }
  const before = [{ lamports: 10000000 }, { lamports: 1000 }, account(owner, 6000000n), account(pool, 9000000n), null];
  const after = [{ lamports: 8730160 }, { lamports: 999 }, account(owner, 1000000n), account(pool, 14000000n), { owner: yolo, lamports: 1259840 }];
  return { before, after, owner, pool, margin: 5000000n, networkFee: 10000, rent: 1259840, pythFee: 1n };
}

test('requires exact collateral, rent, network fee and keeper fee deltas', () => {
  assert.doesNotThrow(() => verifyEconomicDeltas(economicFixture()));
  const cases = [
    x => x.after[2].data.writeBigUInt64LE(999999n, 64),
    x => x.after[3].data.writeBigUInt64LE(14000001n, 64),
    x => { x.after[0].lamports--; },
    x => { x.after[1].lamports--; },
    x => { x.after[4].lamports++; },
    x => { x.before[4] = { lamports: 1 }; },
    x => { x.before[0].lamports = Number.MAX_SAFE_INTEGER + 1; },
    x => { x.networkFee = 10000001; },
    x => { x.after[2].data[0] ^= 1; },
    x => { x.after[2].data[32] ^= 1; },
    x => { x.after[3].data[108] = 2; },
  ];
  for (const change of cases) { const x = economicFixture(); change(x); assert.throws(() => verifyEconomicDeltas(x), /current_(invalid|token|lamport)/); }
});


test('rejects changed or unavailable upgradeable program data', async () => {
  await assert.rejects(verifyProgramPins({ async getMultipleAccountsInfo() { return [null, null, null, null]; } }), /current_program_changed/);
  const loader = new PublicKey('BPFLoaderUpgradeab1e11111111111111111111111');
  const bad = { executable: true, owner: loader, data: Buffer.alloc(36) };
  await assert.rejects(verifyProgramPins({ async getMultipleAccountsInfo() { return [bad, bad, bad, bad]; } }), /current_program_changed/);
});
