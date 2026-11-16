import test from 'node:test';
import assert from 'node:assert/strict';
import { PublicKey } from '@solana/web3.js';
import { verifyEconomicDeltas } from '../current-open.mjs';
const SYSTEM = new PublicKey('11111111111111111111111111111111');
const YOLO = new PublicKey('yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA');
const TOKEN = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const USD = new PublicKey('JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD');
const owner = new PublicKey(Buffer.alloc(32, 6)), pool = new PublicKey(Buffer.alloc(32, 9));
const system = lamports => ({ owner: SYSTEM, executable: false, rentEpoch: '18446744073709551615', data: Buffer.alloc(0), lamports });
function account(authority, amount) { const data = Buffer.alloc(165); USD.toBuffer().copy(data); authority.toBuffer().copy(data, 32); data.writeBigUInt64LE(amount, 64); data[108] = 1; return { owner: TOKEN, executable: false, rentEpoch: '18446744073709551615', data, lamports: 1488440 }; }
function scenario(margin) { return { owner, pool, margin, networkFee: 10000, rent: 1259840, pythFee: 1n,
  before: [system(10000000), system(1000), account(owner, margin + 1n), account(pool, 1n), null],
  after: [system(8730160), system(999), account(owner, 1n), account(pool, margin + 1n), { owner: YOLO, lamports: 1259840 }] }; }
test('collateral accounting uses exact u64 integers at minimum and high notional', () => {
  for (const margin of [5000000n, 18446744073709550n]) {
    const x = scenario(margin); assert.doesNotThrow(() => verifyEconomicDeltas(x));
    x.after[2].data.writeBigUInt64LE(2n, 64);
    assert.throws(() => verifyEconomicDeltas(x), /current_token_delta_mismatch/);
  }
});
