import test from 'node:test';
import assert from 'node:assert/strict';
import { ComputeBudgetProgram, Keypair, PublicKey, SystemProgram, TransactionInstruction, TransactionMessage, VersionedTransaction } from '@solana/web3.js';
import * as sdk from 'jupiter-sdk/yolo/web3js';
import { apiRequest, inspectOpenBuild, MARKETS, PROGRAM, USD_MINT, serviceHandle, verifyBuild, verifySigned } from '../service.mjs';

const key = n => new PublicKey(Buffer.alloc(32, n));
const owner = Keypair.fromSeed(Buffer.alloc(32, 1)); // Deterministic test-only signer.
const keeper = key(2), now = 1794800000;
const settings = { keeper, paused: false, settings: { maxRequestExecutionSec: 30 } };
const connection = { async getBlockHeight() { return 100; } };
const readAccount = async (_connection, _key, decoder) => decoder === sdk.deserializeConfigAccount ? settings :
  decoder === sdk.deserializeMarketAccount ? { oracle: key(4), mint: key(5) } :
    { owner: owner.publicKey, market: new PublicKey(MARKETS.ZEC), isOpen: true, updateTime: BigInt(now - 20) };
const options = { connection, now, readAccount };
const markets = () => ({ paused: false, minMargin: '5000000', fees: { closeFeePpm: 20, winFeePpm: 30000 }, markets:
  Object.entries(MARKETS).map(([symbol, address]) => ({ symbol, address, closed: false, closeOnly: false })) });
const intent = () => ({ operation: 'open', owner: owner.publicKey.toBase58(), asset: 'ZEC', side: 'short', margin: '5000000', leverage: 1000 });
async function fixture({ operation = 'open', margin = 5000000n, extra = [], side = false, oracle = key(4) } = {}) {
  const program = new PublicKey(PROGRAM), usdMint = new PublicKey(USD_MINT);
  const [config] = await sdk.findConfigPda(program), [pool] = await sdk.findPoolPda(program), [vault] = await sdk.findVaultPda(program);
  const [position] = await sdk.findPositionPda({ owner: owner.publicKey, id: 17n }, program);
  const token = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
  const associated = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');
  const [funding] = PublicKey.findProgramAddressSync([owner.publicKey.toBuffer(), token.toBuffer(), usdMint.toBuffer()], associated);
  const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from('__event_authority')], program);
  const common = { owner: owner.publicKey, keeper, config, market: new PublicKey(MARKETS.ZEC), pool, vault, usdMint,
    oracle, tokenProgram: token, systemProgram: SystemProgram.programId, eventAuthority, program, position };
  const ix = operation === 'open' ? await sdk.createOpenPositionInstruction({ ...common, fundingAccount: funding },
    { id: 17n, margin, leverage: 1000, long: side, requestTime: BigInt(now) }, program) :
    await sdk.createClosePositionInstruction({ ...common, destination: funding, claim: key(9) }, { requestTime: BigInt(now) }, program);
  const tx = new VersionedTransaction(new TransactionMessage({ payerKey: owner.publicKey, recentBlockhash: key(7).toBase58(),
    instructions: [...extra, ix] }).compileToV0Message());
  return { build: { serializedTxBase64: Buffer.from(tx.serialize()).toString('base64'), buildToken: 'fixture-bound-build',
    positionId: '17', txMetadata: { blockhash: key(7).toBase58(), lastValidBlockHeight: '200' } }, tx, position };
}

async function inspectionFixture() {
  const program = new PublicKey(PROGRAM), [config] = await sdk.findConfigPda(program);
  const [oracle] = PublicKey.findProgramAddressSync([Buffer.from('price'), key(5).toBuffer()], program);
  const update = new TransactionInstruction({ programId: program, data: Buffer.concat([Buffer.from('3d22759b4b227bd0', 'hex'), Buffer.alloc(125)]), keys: [
    { pubkey: keeper, isSigner: true, isWritable: true },
    { pubkey: config, isSigner: false, isWritable: false },
    { pubkey: new PublicKey('3rdJbqfnagQ4yx9HXJViD4zc4xpiSqmFsKpPuSCQVyQL'), isSigner: false, isWritable: false },
    { pubkey: new PublicKey('Gx4MBPb1vqZLJajZmsKLg8fGw9ErhoKsR8LeKcCKFyak'), isSigner: false, isWritable: true },
    { pubkey: new PublicKey('pytd2yyk641x7ak7mkaasSJVXh6YYZnC7wTmtgAyxPt'), isSigner: false, isWritable: false },
    { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
    { pubkey: oracle, isSigner: false, isWritable: true },
  ] });
  return { ...(await fixture({ extra: [update], oracle })), update, oracle };
}

test('inspection validates intent and simulates unsigned without producing executable preview', async () => {
  const { build, oracle } = await inspectionFixture(); let simulations = 0;
  const [, bump] = PublicKey.findProgramAddressSync([Buffer.from('price'), key(5).toBuffer()], new PublicKey(PROGRAM));
  const data = Buffer.concat([Buffer.from('47a6e51536f70822', 'hex'), key(5).toBuffer(), Buffer.alloc(20), Buffer.from([bump])]);
  const connection = { async getBlockHeight() { return 100; }, async getAccountInfo(address) { assert.ok(address.equals(oracle)); return { owner: new PublicKey(PROGRAM), executable: false, data }; },
    async simulateTransaction(tx, opts) { simulations++; assert.equal(opts.sigVerify, false); assert.equal(opts.replaceRecentBlockhash, true); assert.ok(tx.signatures.every(s => s.every(b => b === 0))); return { value: { err: null, unitsConsumed: 1234 } }; } };
  const deps = { connection, now, readAccount };
  const result = await inspectOpenBuild(build, intent(), deps);
  assert.equal(result.status, 'inspection'); assert.equal(result.simulation.status, 'passed'); assert.equal(simulations, 1);
  assert.equal(result.checked.margin, '5000000'); assert.equal(result.checked.owner, owner.publicKey.toBase58());
  assert.equal(result.build, undefined); assert.equal(result.preview_id, undefined);
  await assert.rejects(inspectOpenBuild(build, { ...intent(), margin: '6000000' }, deps), /intent_mismatch/);
  await assert.rejects(inspectOpenBuild(build, { ...intent(), asset: 'BTC' }, deps), /account_or_instruction/);
  await assert.rejects(inspectOpenBuild(build, { ...intent(), owner: key(8).toBase58() }, deps), /signers/);
  const { update } = await inspectionFixture();
  update.keys[2].pubkey = key(9);
  await assert.rejects(inspectOpenBuild((await fixture({ extra: [update], oracle })).build, intent(), deps), /unexpected_price_update_accounts/);
  const { update: validUpdate } = await inspectionFixture();
  const unknown = new TransactionInstruction({ programId: key(11), keys: [], data: Buffer.alloc(0) });
  await assert.rejects(inspectOpenBuild((await fixture({ extra: [validUpdate, unknown], oracle })).build, intent(), deps), /unexpected_service_instruction/);
  const expensive = ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 10000001 });
  await assert.rejects(inspectOpenBuild((await fixture({ extra: [validUpdate, expensive], oracle })).build, intent(), deps), /priority_fee/);
  await assert.rejects(inspectOpenBuild((await fixture({ extra: [validUpdate] })).build, intent(), deps), /oracle_market_mismatch/);
  data[8] ^= 1;
  await assert.rejects(inspectOpenBuild(build, intent(), deps), /invalid_oracle_account/);
  data[8] ^= 1;
  data[60] ^= 1;
  await assert.rejects(inspectOpenBuild(build, intent(), deps), /invalid_oracle_account/);
  data[60] ^= 1;
  assert.equal(simulations, 1);
  connection.simulateTransaction = async () => ({ value: { err: { InstructionError: [1, { Custom: 17 }] } } });
  const failed = await inspectOpenBuild(build, intent(), deps);
  assert.equal(failed.status, 'blocked'); assert.equal(failed.code, 'unsigned_simulation_failed'); assert.equal(failed.simulation.programCode, 17);
});

test('actual SDK validates exact public-service margin, side, owner, keeper and v0 bytes', async () => {
  const { build } = await fixture();
  const result = await verifyBuild(build, intent(), options);
  assert.equal(result.margin, '5000000'); assert.equal(result.leverage, 1000);
  assert.equal(result.owner, owner.publicKey.toBase58()); assert.equal(result.side, 'short');
  assert.match(result.messageSha256, /^[a-f0-9]{64}$/);
});

test('rejects altered intent, fee payer, market, keeper, expiry and preexisting signature', async () => {
  const { build, tx } = await fixture();
  await assert.rejects(verifyBuild(build, { ...intent(), margin: '6000000' }, options), /intent_mismatch/);
  await assert.rejects(verifyBuild(build, { ...intent(), side: 'long' }, options), /intent_mismatch/);
  await assert.rejects(verifyBuild(build, { ...intent(), owner: key(8).toBase58() }, options), /signers/);
  await assert.rejects(verifyBuild(build, { ...intent(), asset: 'BTC' }, options), /account_or_instruction/);
  await assert.rejects(verifyBuild(build, intent(), { ...options, readAccount: async (...args) => {
    const result = await readAccount(...args); return result.keeper ? { ...result, keeper: key(6) } : result;
  } }), /keeper/);
  await assert.rejects(verifyBuild(build, intent(), { ...options, now: now + 31 }), /window_elapsed/);
  await assert.rejects(verifyBuild(build, intent(), { ...options, connection: { async getBlockHeight() { return 201; } } }), /blockhash_expired/);
  tx.sign([owner]);
  await assert.rejects(verifyBuild({ ...build, serializedTxBase64: Buffer.from(tx.serialize()).toString('base64') }, intent(), options), /preexisting_signature/);
});

test('rejects paused program and owner keeper as separate diagnostics', async () => {
  const { build } = await fixture();
  await assert.rejects(verifyBuild(build, intent(), { ...options, readAccount: async (...args) => {
    const result = await readAccount(...args); return result.keeper ? { ...result, paused: true } : result;
  } }), /service_program_paused/);
  await assert.rejects(verifyBuild(build, intent(), { ...options, readAccount: async (...args) => {
    const result = await readAccount(...args); return result.keeper ? { ...result, keeper: owner.publicKey } : result;
  } }), /service_owner_is_keeper/);
});

test('unknown instructions and priority fees above0.01SOL fail before owner signing', async () => {
  const unknown = new TransactionInstruction({ programId: key(11), keys: [], data: Buffer.alloc(0) });
  await assert.rejects(verifyBuild((await fixture({ extra: [unknown] })).build, intent(), options), /unexpected_service_instruction/);
  const extra = [ComputeBudgetProgram.setComputeUnitLimit({ units: 1000000 }), ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 10000001 })];
  await assert.rejects(verifyBuild((await fixture({ extra })).build, intent(), options), /priority_fee/);
});

test('implicit compute limit uses the runtime ceiling and duplicate budgets are rejected', async () => {
  const extra = [ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 8000000 })];
  await assert.rejects(verifyBuild((await fixture({ extra })).build, intent(), options), /priority_fee/);
  const duplicate = [ComputeBudgetProgram.setComputeUnitLimit({ units: 100000 }), ComputeBudgetProgram.setComputeUnitLimit({ units: 100000 })];
  await assert.rejects(verifyBuild((await fixture({ extra: duplicate })).build, intent(), options), /duplicate_compute/);
});

test('cryptographically verifies owner signature and preserves message and keeper slot', async () => {
  const { build, tx } = await fixture();
  tx.sign([owner]);
  const signed = Buffer.from(tx.serialize()).toString('base64');
  assert.match(verifySigned(build, signed, owner.publicKey.toBase58()), /^[1-9A-HJ-NP-Za-km-z]{64,100}$/);
  tx.signatures[0][0] ^= 1;
  assert.throws(() => verifySigned(build, Buffer.from(tx.serialize()).toString('base64'), owner.publicKey.toBase58()), /invalid_owner_signature/);
  tx.signatures[1][0] = 1;
  assert.throws(() => verifySigned(build, Buffer.from(tx.serialize()).toString('base64'), owner.publicKey.toBase58()), /other_signature_changed/);
});

test('official build and keeper execute routes bind exact buildToken and signed txid', async () => {
  const { build, tx } = await fixture(); let executed = 0;
  const api = async (path, body) => {
    if (path === 'markets') return markets();
    if (path === 'transactions/build') {
      assert.deepEqual(body, { action: 'open', owner: owner.publicKey.toBase58(), market: 'ZEC', leverage: 1000, long: false, margin: '5000000', transactionVersion: 0 });
      return build;
    }
    assert.equal(path, 'transactions/execute'); executed++;
    assert.equal(body.buildToken, build.buildToken);
    return { status: 'Processing', txid: verifySigned(build, body.serializedTxBase64, owner.publicKey.toBase58()), error: null, queuePosition: 2 };
  };
  const deps = { ...options, api };
  const preview = await serviceHandle({ ...intent(), action: 'service-build-open' }, deps);
  assert.equal(executed, 0);
  tx.sign([owner]); const signed = Buffer.from(tx.serialize()).toString('base64');
  const payload = { owner: intent().owner, preview, serializedTxBase64: signed };
  const checked = await serviceHandle({ ...payload, action: 'service-signed' }, deps);
  assert.equal(executed, 0);
  const result = await serviceHandle({ ...payload, action: 'service-execute' }, deps);
  assert.equal(executed, 1); assert.equal(result.signature, checked.signature); assert.equal(result.status, 'submitted');
});

test('close checks the owned open position and minimum15second guard before building', async () => {
  const { build, position } = await fixture({ operation: 'close' }); let builds = 0;
  const row = { address: position.toBase58(), owner: intent().owner, market: MARKETS.ZEC, id: '17', isLong: false,
    margin: '5000000', notional: '5000000000', entryPrice: '1000000', updateTime: String(now - 20) };
  const api = async path => {
    if (path === 'markets') return markets();
    if (path.startsWith('users/')) return { queued: '0', positions: [row], claims: [] };
    builds++; return build;
  };
  const payload = { action: 'service-build-close', owner: intent().owner, asset: 'ZEC', position: position.toBase58() };
  assert.equal((await serviceHandle(payload, { ...options, api })).status, 'ready');
  assert.equal(builds, 1);
  row.updateTime = String(now - 14);
  await assert.rejects(serviceHandle(payload, { ...options, api }), /minimum_15_seconds/);
  assert.equal(builds, 1);
});

test('public transport uses official HTTPS route and bounded JSON without auth headers', async () => {
  const saved = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'https://yolo-api.jup.ag/transactions/build');
    assert.equal(options.redirect, 'error'); assert.deepEqual(options.headers, { 'Content-Type': 'application/json' });
    return new Response(JSON.stringify({ error: 'insufficient_funds' }), { status: 400 });
  };
  try { await assert.rejects(apiRequest('transactions/build', { fixture: true }), /service_400_insufficient_funds/); }
  finally { globalThis.fetch = saved; }
});

test('known live insufficient balance is actionable and stops before signing', async () => {
  const api = async path => { if (path === 'markets') return markets(); throw new Error('service_400_insufficient_balance'); };
  const result = await serviceHandle({ ...intent(), action: 'service-build-open' }, { ...options, api });
  assert.equal(result.status, 'blocked'); assert.match(result.message, /JupUSD/);
});
