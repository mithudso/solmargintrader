/** Observed current YOLO subset; this is not verified source for the deployed program. */
import { createHash } from 'node:crypto';
import { PublicKey, TransactionMessage, VersionedTransaction } from '@solana/web3.js';
import { secp256k1 } from '@noble/curves/secp256k1';
import { keccak_256 } from '@noble/hashes/sha3';
import * as sdk from 'jupiter-sdk/yolo/web3js';

const fail = code => { throw new Error('current_' + code); };
const sha = data => createHash('sha256').update(data).digest('hex');
const YOLO = new PublicKey('yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA');
const PYTH = new PublicKey('pytd2yyk641x7ak7mkaasSJVXh6YYZnC7wTmtgAyxPt');
const LOADER = new PublicKey('BPFLoaderUpgradeab1e11111111111111111111111');
const STORAGE = new PublicKey('3rdJbqfnagQ4yx9HXJViD4zc4xpiSqmFsKpPuSCQVyQL');
const TREASURY = new PublicKey('Gx4MBPb1vqZLJajZmsKLg8fGw9ErhoKsR8LeKcCKFyak');
const TOKEN = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const SYSTEM = new PublicKey('11111111111111111111111111111111');
const USD = new PublicKey('JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD');
const SERVICE_SIGNER = new PublicKey('2BcxBiR3KiUwnSwM8eViGj9hp7s9JRi4QqiWuVU8Eve7');
const PINNED = [
  [YOLO, new PublicKey('86FJSZxQwcyUdWBzVknsfwm3qCVwK3Z7ocBXLVoSxA7z'), 468172111n, 'ee5fca1c7a4380b06fd5c89b5234b401868da67b53f675a33465560c3b7cbda7'],
  [PYTH, new PublicKey('Bvr6VWREUEvwef1VoFJm6sjL4tXmg35N9rbW3YttkMhb'), 330575503n, '33438249200aa130bd7f3e060aaf45cd8bce9987237f21470c6c7093af02fbaa'],
];
const MAX_OWNER_LAMPORTS = 12000000n;
const discriminator = name => createHash('sha256').update('account:' + name).digest().subarray(0, 8);

// Pyth Lazer public protocol, pinned reference f8c8a9565c77953124369c73b9195a10449a2075:
// sdk/rust/protocol/src/{message.rs,payload/standard.rs}. Strictly accept the observed subset.
export function parseCurrentPrice(data, asset, chainTime) {
  if (!Buffer.isBuffer(data) || data.length !== 133 || !data.subarray(0, 8).equals(Buffer.from('3d22759b4b227bd0', 'hex')) || data.readUInt32LE(8) !== 121 || data.readUInt32LE(12) !== 1296547300 || data[80] > 1 || data.readUInt16LE(81) !== 50 || data.readUInt32LE(83) !== 2479346549) fail('invalid_price_envelope');
  const time = data.readBigUInt64LE(87), channel = data[95], feed = data.readUInt32LE(97);
  if (channel !== 3 || data[96] !== 1 || feed !== ({ BTC: 1, ZEC: 66 })[asset] || data[101] !== 4 || data[102] !== 0 || data[111] !== 4 || data[114] !== 5 || data[123] !== 12 || data[124] !== 1) fail('invalid_price_feed');
  const price = data.readBigInt64LE(103), exponent = data.readInt16LE(112), confidence = data.readBigInt64LE(115), feedTime = data.readBigUInt64LE(125);
  if (price <= 0n || exponent !== -8 || confidence <= 0n || confidence > price || feedTime !== time || !Number.isSafeInteger(chainTime)) fail('invalid_price_value');
  // The on-chain configuration currently permits age 10s and future 3s; caller applies it.
  return { feed, time, price, confidence, oraclePrice: price * 10000n, signature: data.subarray(16, 80), recovery: data[80], payload: data.subarray(83) };
}

export function checkCurrentTime(price, settings, chainTime) {
  if (!Number.isSafeInteger(chainTime) || !Number.isSafeInteger(settings.maxOracleFutureSecs) || !Number.isSafeInteger(settings.maxOracleAgeSecs) || settings.maxOracleFutureSecs < 0 || settings.maxOracleAgeSecs < 0) fail('invalid_clock_settings');
  const nowUs = BigInt(chainTime) * 1000000n;
  if (price.time > nowUs + BigInt(settings.maxOracleFutureSecs) * 1000000n || price.time + BigInt(settings.maxOracleAgeSecs) * 1000000n < nowUs) fail('price_stale_or_future');
}

export function verifyPythSignature(price, storage, chainTime) {
  if (!storage || storage.executable || !storage.owner.equals(PYTH) || storage.data.length !== 381 || !storage.data.subarray(0, 8).equals(discriminator('Storage')) || !storage.data.subarray(40, 72).equals(TREASURY.toBuffer())) fail('invalid_pyth_storage');
  const n = storage.data[281];
  if (n > 2) fail('invalid_pyth_storage');
  let pub, valid;
  try {
    const digest = keccak_256(price.payload);
    pub = secp256k1.Signature.fromCompact(price.signature).addRecoveryBit(price.recovery).recoverPublicKey(digest).toRawBytes(false);
    valid = secp256k1.verify(price.signature, digest, pub, { lowS: false });
  } catch { fail('invalid_pyth_signature'); }
  const recovered = Buffer.from(keccak_256(pub.subarray(1))).subarray(12);
  let trusted = false;
  for (let i = 0; i < n; i++) {
    const offset = 282 + i * 28;
    if (storage.data.subarray(offset, offset + 20).equals(recovered) && storage.data.readBigInt64LE(offset + 20) > BigInt(chainTime)) trusted = true;
  }
  if (!valid || !trusted) fail('untrusted_pyth_signature');
  return storage.data.readBigUInt64LE(72);
}

export async function verifyProgramPins(connection) {
  const accounts = await connection.getMultipleAccountsInfo(PINNED.flatMap(([p, d]) => [p, d]), 'confirmed');
  for (const [index, [program, dataKey, slot, digest]] of PINNED.entries()) {
    const p = accounts[index * 2], d = accounts[index * 2 + 1];
    if (!p || !p.executable || !p.owner.equals(LOADER) || p.data.length !== 36 || p.data.readUInt32LE(0) !== 2 || !p.data.subarray(4, 36).equals(dataKey.toBuffer()) || !d || d.executable || !d.owner.equals(LOADER) || d.data.length < 45 || d.data.readUInt32LE(0) !== 3 || d.data.readBigUInt64LE(4) !== slot || sha(d.data) !== digest) fail('program_changed');
  }
}
function tokenBalance(account, expectedOwner) {
  if (!account || !account.owner.equals(TOKEN) || account.executable !== false || account.data.length !== 165 || !account.data.subarray(0, 32).equals(USD.toBuffer()) || !account.data.subarray(32, 64).equals(expectedOwner.toBuffer()) || account.data[108] !== 1) fail('invalid_token_account');
  if (account.data.readUInt32LE(72) !== 0 || account.data.readUInt32LE(109) !== 0 || account.data.readBigUInt64LE(121) !== 0n || account.data.readUInt32LE(129) !== 0) fail('unsafe_token_authority');
  return account.data.readBigUInt64LE(64);
}
function sameMetadata(before, after, lamportsUnchanged = true) {
  if (!before || !after || !Number.isSafeInteger(before.lamports) || before.lamports < 0 || !Number.isSafeInteger(after.lamports) || after.lamports < 0 || !Buffer.isBuffer(before.data) || !Buffer.isBuffer(after.data) || !before.owner.equals(after.owner) || before.executable !== after.executable || typeof before.rentEpoch !== 'string' || !/^[0-9]+$/.test(before.rentEpoch) || before.rentEpoch !== after.rentEpoch || (lamportsUnchanged && before.lamports !== after.lamports)) fail('account_metadata_changed');
}
function tokenUnchangedExceptAmount(before, after) {
  sameMetadata(before, after);
  if (!before.data.subarray(0, 64).equals(after.data.subarray(0, 64)) || !before.data.subarray(72).equals(after.data.subarray(72))) fail('token_authority_changed');
}
// web3.js parses u64 rentEpoch as Number and rounds the common u64-max value.
// Preserve its original JSON lexeme so pre/post metadata comparison is exact.
export function parseLosslessRpc(text) {
  let result;
  try {
    result = JSON.parse(text, (key, value, context) => {
      if (key !== 'rentEpoch') return value;
      if (typeof value !== 'number' || !context || !/^[0-9]+$/.test(context.source)) fail('invalid_rent_epoch');
      return context.source;
    });
  } catch { fail('invalid_rpc_response'); }
  if (!result || result.jsonrpc !== '2.0' || result.error || !result.result) fail('invalid_rpc_response');
  return result.result;
}
async function exactRpc(connection, method, params) {
  const url = new URL(connection.rpcEndpoint);
  if (url.protocol !== 'https:' || url.username || url.password) fail('invalid_rpc_url');
  const response = await fetch(url.toString(), { method: 'POST', redirect: 'error', signal: AbortSignal.timeout(8000), headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) });
  if (!response.ok || !response.body) fail('rpc_unavailable');
  const chunks = []; let size = 0;
  for await (const chunk of response.body) { size += chunk.length; if (size > 262144) fail('rpc_response_too_large'); chunks.push(chunk); }
  return parseLosslessRpc(Buffer.concat(chunks).toString('utf8'));
}
function simAccount(raw) {
  if (!raw) return null;
  if (!Array.isArray(raw.data) || raw.data[1] !== 'base64' || typeof raw.data[0] !== 'string') fail('invalid_simulation_account');
  const data = Buffer.from(raw.data[0], 'base64');
  if (data.toString('base64') !== raw.data[0] || (raw.space !== undefined && raw.space !== data.length)) fail('invalid_simulation_account');
  return { ...raw, owner: new PublicKey(raw.owner), data };
}

export function verifyOraclePost({ before, after, mint, feedPrice, settings, chainTime }) {
  const [, bump] = PublicKey.findProgramAddressSync([Buffer.from('price'), mint.toBuffer()], YOLO);
  function decode(account) {
    if (!account || account.executable !== false || !account.owner.equals(YOLO) || !Buffer.isBuffer(account.data) || account.data.length !== 61 || !account.data.subarray(0, 8).equals(discriminator('OraclePrice')) || !account.data.subarray(8, 40).equals(mint.toBuffer()) || account.data[60] !== bump || account.data.readUInt32LE(40) !== feedPrice.feed) fail('oracle_poststate_mismatch');
    return { value: account.data.readBigUInt64LE(44), time: account.data.readBigUInt64LE(52) };
  }
  const old = decode(before), next = decode(after);
  if (next.value === 0n || next.time < feedPrice.time || next.time < old.time || (next.time === old.time && next.value !== old.value) || (next.time === feedPrice.time && next.value !== feedPrice.oraclePrice)) fail('oracle_poststate_mismatch');
  checkCurrentTime(next, settings, chainTime);
  return next;
}

export function verifyEconomicDeltas({ before, after, owner, pool, margin, networkFee, rent, pythFee }) {
  const [ownerBefore, keeperBefore, fundingBefore, vaultBefore, positionBefore] = before;
  const [ownerAfter, keeperAfter, fundingAfter, vaultAfter, positionAfter] = after;
  if (!ownerBefore || !keeperBefore || positionBefore || !ownerAfter || !keeperAfter || !positionAfter || !positionAfter.owner.equals(YOLO) || [ownerBefore, keeperBefore, ownerAfter, keeperAfter, positionAfter].some(a => !Number.isSafeInteger(a.lamports) || a.lamports < 0)) fail('invalid_poststate');
  for (const [a, b] of [[ownerBefore, ownerAfter], [keeperBefore, keeperAfter]]) {
    sameMetadata(a, b, false);
    if (!a.owner.equals(SYSTEM) || a.executable || a.data.length !== 0 || !a.data.equals(b.data)) fail('invalid_system_account');
  }
  const funding = tokenBalance(fundingBefore, owner), vault = tokenBalance(vaultBefore, pool);
  tokenUnchangedExceptAmount(fundingBefore, fundingAfter);
  tokenUnchangedExceptAmount(vaultBefore, vaultAfter);
  if (funding < margin || tokenBalance(fundingAfter, owner) !== funding - margin || tokenBalance(vaultAfter, pool) !== vault + margin) fail('token_delta_mismatch');
  if (!Number.isSafeInteger(networkFee) || networkFee < 0 || BigInt(networkFee) > 10000000n || !Number.isSafeInteger(rent) || rent < 0 || positionAfter.lamports !== rent || BigInt(networkFee) + BigInt(rent) > MAX_OWNER_LAMPORTS || BigInt(ownerBefore.lamports) - BigInt(ownerAfter.lamports) !== BigInt(networkFee) + BigInt(rent) || BigInt(keeperBefore.lamports) - BigInt(keeperAfter.lamports) !== pythFee) fail('lamport_delta_mismatch');
}

/** This repeats all checks when preparing a build and after signing; it never signs or sends. */
export async function verifyCurrentOpen(build, intent, options, inspectOpenBuild, checkPins = verifyProgramPins) {
  const { connection } = options;
  if (typeof build.buildToken !== 'string' || build.buildToken.length < 1 || build.buildToken.length > 88) fail('invalid_build_token');
  const inspection = await inspectOpenBuild(build, intent, { ...options, skipSimulation: true });
  if (inspection.status !== 'structural') fail('simulation_failed');
  await checkPins(connection);
  const slot = await connection.getSlot('confirmed'), chainTime = await connection.getBlockTime(slot);
  if (!Number.isSafeInteger(chainTime) || Math.abs(Math.floor(Date.now() / 1000) - chainTime) > 30) fail('rpc_clock_unavailable');
  const tx = VersionedTransaction.deserialize(Buffer.from(build.serializedTxBase64, 'base64'));
  const alts = [];
  for (const lookup of tx.message.addressTableLookups) {
    const value = (await connection.getAddressLookupTable(lookup.accountKey)).value;
    if (!value) fail('lookup_unavailable');
    alts.push(value);
  }
  const msg = TransactionMessage.decompile(tx.message, { addressLookupTableAccounts: alts });
  const [update, open] = msg.instructions.filter(ix => ix.programId.equals(YOLO));
  const parsed = sdk.parseOpenPositionInstruction(open);
  const [config] = await sdk.findConfigPda(YOLO);
  const cfg = await connection.getAccountInfo(config, 'confirmed');
  if (!cfg || cfg.executable || !cfg.owner.equals(YOLO)) fail('config_unavailable');
  const settings = sdk.deserializeConfigAccount(cfg.data);
  if (settings.paused || parsed.data.margin < settings.settings.minMargin) fail('config_not_tradeable');
  const keeper = tx.message.staticAccountKeys[1];
  if (!keeper.equals(SERVICE_SIGNER) && !keeper.equals(settings.keeper)) fail('unknown_keeper');
  const request = Number(parsed.data.requestTime);
  if (!Number.isSafeInteger(request) || request > chainTime + 2 || chainTime - request > Math.min(30, settings.settings.maxRequestExecutionSec)) fail('request_expired');
  const price = parseCurrentPrice(update.data, intent.asset, chainTime);
  checkCurrentTime(price, settings.settings, chainTime);
  const fee = verifyPythSignature(price, await connection.getAccountInfo(STORAGE, 'confirmed'), chainTime);
  if (fee > 10000n) fail('pyth_fee_excessive');
  const names = ['owner', 'keeper', 'fundingAccount', 'vault', 'position', 'oracle'];
  const keys = names.map(name => parsed.accounts[name].pubkey);
  const rawBefore = await exactRpc(connection, 'getMultipleAccounts', [keys.map(k => k.toBase58()), { encoding: 'base64', commitment: 'confirmed' }]);
  if (!rawBefore.context || !Number.isSafeInteger(rawBefore.context.slot) || !Array.isArray(rawBefore.value) || rawBefore.value.length !== keys.length) fail('invalid_prestate');
  const before = { context: rawBefore.context, value: rawBefore.value.map(simAccount) };
  const [ownerBefore, keeperBefore, , , positionBefore, oracleBefore] = before.value;
  if (!ownerBefore || !keeperBefore || positionBefore) fail('invalid_prestate');
  const networkFee = (await connection.getFeeForMessage(tx.message, 'confirmed')).value;
  if (!Number.isSafeInteger(networkFee) || networkFee < 0 || BigInt(networkFee) > 10000000n) fail('network_fee_excessive');
  const result = await exactRpc(connection, 'simulateTransaction', [Buffer.from(tx.serialize()).toString('base64'), { encoding: 'base64', sigVerify: false, replaceRecentBlockhash: false, commitment: 'confirmed', minContextSlot: before.context.slot, accounts: { encoding: 'base64', addresses: keys.map(k => k.toBase58()) } }]);
  if (!result.value || result.value.err || !Array.isArray(result.value.accounts) || result.value.accounts.length !== keys.length) fail('simulation_failed');
  const [ownerAfter, keeperAfter, fundingAfter, vaultAfter, positionAfter, oracleAfter] = result.value.accounts.map(simAccount);
  if (!ownerAfter || !keeperAfter || !positionAfter || !oracleAfter || !positionAfter.owner.equals(YOLO) || !oracleAfter.owner.equals(YOLO)) fail('invalid_poststate');
  const margin = BigInt(intent.margin);
  const marketMint = (await options.readAccount(connection, parsed.accounts.market.pubkey, sdk.deserializeMarketAccount)).mint;
  const simulatedOracle = verifyOraclePost({ before: oracleBefore, after: oracleAfter, mint: marketMint, feedPrice: price, settings: settings.settings, chainTime });
  const [, positionBump] = await sdk.findPositionPda({ owner: keys[0], id: parsed.data.id }, YOLO);
  if (positionAfter.executable !== false || positionAfter.data.length !== 120) fail('position_poststate_mismatch');
  const position = sdk.deserializePositionAccount(positionAfter.data);
  if (position.bump !== positionBump || !position.owner.equals(keys[0]) || !position.market.equals(parsed.accounts.market.pubkey) || position.id !== parsed.data.id || !position.isOpen || position.isLong !== (intent.side === 'long') || position.margin !== margin || position.notional !== margin * 1000n || position.entryPrice !== simulatedOracle.value || BigInt(position.updateTime) < simulatedOracle.time / 1000000n - 1n || BigInt(position.updateTime) > BigInt(chainTime) + 3n) fail('position_poststate_mismatch');
  const rent = await connection.getMinimumBalanceForRentExemption(positionAfter.data.length, 'confirmed');
  verifyEconomicDeltas({ before: before.value, after: [ownerAfter, keeperAfter, fundingAfter, vaultAfter, positionAfter], owner: keys[0], pool: parsed.accounts.pool.pubkey, margin, networkFee, rent, pythFee: fee });
  await checkPins(connection);
  return { ...inspection.checked, operation: 'open', keeper: keeper.toBase58(), requestTime: request, simulatedEntryPrice: simulatedOracle.value.toString(), simulatedOracleTimestampUs: simulatedOracle.time.toString(), signedFeedPrice: price.oraclePrice.toString(), priceScale: '1000000000000', networkFeeLamports: String(networkFee), positionRentLamports: String(rent), verification: 'current_observed_subset' };
}
