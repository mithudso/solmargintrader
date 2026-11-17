import test from 'node:test';
import assert from 'node:assert/strict';
import { PublicKey } from '@solana/web3.js';
import * as sdk from 'jupiter-sdk/yolo/web3js';
import { handle, PROGRAM, USD_MINT } from '../bridge.mjs';

const address = n => new PublicKey(Buffer.alloc(32, n)).toBase58();
const request = () => ({ action: 'build-open', asset: 'ZEC', side: 'short', owner: address(1),
  market: address(3), accounts: { keeper: address(2), oracle: address(4) },
  margin: '5000000', leverage: 1000, requestTime: 1794800000, id: '17' });

test('loads pinned real SDK and exposes both required signatures without a send path', async () => {
  const result = await handle({ action: 'status' });
  assert.equal(result.program, PROGRAM);
  assert.equal(result.sdkVersion, '0.6.0');
  assert.equal(result.fundedSubmitAvailable, false);
  assert.deepEqual(result.requiredSignatures, ['owner', 'keeper']);
});

test('real SDK encodes1000x, exact margin/direction and owner plus keeper signers', async () => {
  const result = await handle(request());
  assert.equal(result.status, 'dry-run');
  assert.equal(result.instruction.programId, PROGRAM);
  const instruction = { programId: new PublicKey(PROGRAM),
    data: Buffer.from(result.instruction.dataBase64, 'base64'),
    keys: result.instruction.accounts.map(k => ({ pubkey: new PublicKey(k.address), isSigner: k.signer, isWritable: k.writable })) };
  const parsed = sdk.parseOpenPositionInstruction(instruction);
  assert.equal(parsed.data.margin, 5000000n);
  assert.equal(parsed.data.leverage, 1000);
  assert.equal(parsed.data.long, false);
  assert.equal(parsed.data.id, 17n);
  assert.equal(parsed.accounts.usdMint.pubkey.toBase58(), USD_MINT);
  assert.deepEqual(result.instruction.accounts.filter(a => a.signer).map(a => a.address), [address(1), address(2)]);
});

test('does not invent a market, queue claim, margin or keeper signature', async () => {
  const missing = request(); delete missing.market;
  assert.equal((await handle(missing)).status, 'blocked');
  assert.equal((await handle({ ...request(), action: 'build-close', position: address(5) })).status, 'blocked');
  await assert.rejects(handle({ ...request(), margin: '4999999' }), /invalid_margin/);
  await assert.rejects(handle({ ...request(), margin: '5000000.00' }), /invalid_margin/);
  await assert.rejects(handle({ ...request(), leverage: 10 }), /invalid_1000x/);
  await assert.rejects(handle({ ...request(), accounts: { keeper: address(1), oracle: address(4) } }), /owner_cannot/);
});

test('real SDK builds close requiring the owner and keeper', async () => {
  const result = await handle({ ...request(), action: 'build-close', position: address(5), claim: address(6) });
  assert.equal(result.status, 'dry-run');
  assert.deepEqual(result.instruction.accounts.filter(a => a.signer).map(a => a.address), [address(1), address(2)]);
});

test('simulation invokes only unsigned read-only RPC simulation and reports program failure', async () => {
  const calls = [];
  const connection = {
    async getLatestBlockhash() { calls.push('blockhash'); return { blockhash: address(7), lastValidBlockHeight: 1 }; },
    async simulateTransaction(transaction, options) {
      calls.push('simulate');
      assert.ok(transaction.signatures.every(s => s.every(b => b === 0)));
      assert.equal(options.sigVerify, false);
      assert.equal(options.replaceRecentBlockhash, true);
      return { value: { err: 'InsufficientFundsForRent', logs: [], unitsConsumed: 0 } };
    },
  };
  const result = await handle({ ...request(), action: 'simulate' }, { connection });
  assert.deepEqual(calls, ['blockhash', 'simulate']);
  assert.equal(result.status, 'blocked');
  assert.equal(result.fundedSubmitAvailable, false);
});

test('rejects funded commands and secret input even when nested', async () => {
  await assert.rejects(handle({ action: 'send' }), /funded_submission_not_supported/);
  await assert.rejects(handle({ ...request(), config: { privateKey: 'fixture-not-a-key' } }), /secret_input_refused/);
});
