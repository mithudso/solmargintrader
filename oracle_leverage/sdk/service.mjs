/** Official public 1000x service, with generated-SDK checks before owner signing. */
import { createHash, createPublicKey, verify } from 'node:crypto';
import { Connection, PublicKey, TransactionMessage, VersionedTransaction } from '@solana/web3.js';
import * as sdk from 'jupiter-sdk/yolo/web3js';
import { verifyCurrentOpen } from './current-open.mjs';

export const SERVICE = 'https://yolo-api.jup.ag';
export const PROGRAM = 'yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA';
export const USD_MINT = 'JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD';
export const MARKETS = Object.freeze({
  BTC: 'BXQQo2VTJV2upjdA6qFMGBY3uMyTMnRmaZjPCB5ZVmr7',
  ZEC: '4ohWGDrmqdiEHinL5Kf2BYzM9UVSe3RJ1bzoveHehiwj',
});
const program = new PublicKey(PROGRAM);
const token = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const associated = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');
const compute = 'ComputeBudget111111111111111111111111111111';
const system = new PublicKey('11111111111111111111111111111111');
const fail = message => { throw new Error(message); };
const address = value => new PublicKey(value).toBase58();
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
function u64(value, minimum = 0n) {
  if (typeof value !== 'string' || !/^[0-9]+$/.test(value)) fail('invalid_service_integer');
  const n = BigInt(value);
  if (n < minimum || n > (1n << 64n) - 1n) fail('invalid_service_integer');
  return n;
}
function base64(value) {
  if (typeof value !== 'string' || value.length > 1644 || !/^[A-Za-z0-9+/]+={0,2}$/.test(value)) fail('invalid_service_transaction');
  const bytes = Buffer.from(value, 'base64');
  if (bytes.length > 1232 || bytes.toString('base64') !== value) fail('invalid_service_transaction');
  return bytes;
}
function base58(bytes) {
  const alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
  let n = BigInt('0x' + Buffer.from(bytes).toString('hex')), result = '';
  while (n) { result = alphabet[Number(n % 58n)] + result; n /= 58n; }
  for (const byte of bytes) { if (byte) break; result = '1' + result; }
  return result;
}
export async function apiRequest(path, body) {
  if (!/^(markets|users\/[1-9A-HJ-NP-Za-km-z]{32,44}|requests\/[1-9A-HJ-NP-Za-km-z]{64,100}|transactions\/(build|execute))$/.test(path)) fail('invalid_service_route');
  const response = await fetch(SERVICE + '/' + path, {
    method: body === undefined ? 'GET' : 'POST', redirect: 'error',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(8000),
  });
  let size = 0; const chunks = [];
  for await (const chunk of response.body) {
    size += chunk.length;
    if (size > 262144) fail('service_response_too_large');
    chunks.push(chunk);
  }
  let result;
  try { result = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { fail('invalid_service_json'); }
  if (!response.ok) {
    const code = typeof result?.error === 'string' && /^[a-z_]{1,80}$/.test(result.error) ? result.error : 'request_rejected';
    fail('service_' + response.status + '_' + code);
  }
  if (!result || typeof result !== 'object' || Array.isArray(result)) fail('invalid_service_response');
  return result;
}
function rpc(payload, injected) {
  if (injected) return injected;
  const url = new URL(payload.rpcUrl || 'https://api.mainnet-beta.solana.com');
  if (url.protocol !== 'https:' || url.username || url.password) fail('invalid_rpc_url');
  return new Connection(url.toString(), { commitment: 'confirmed', disableRetryOnRateLimit: true,
    fetch: (url, init) => fetch(url, { ...init, redirect: 'error', signal: AbortSignal.timeout(8000) }) });
}
async function owned(connection, key, decoder) {
  const account = await connection.getAccountInfo(key, 'confirmed');
  if (!account || account.executable || !account.owner.equals(program)) fail('unverified_program_account');
  return decoder(account.data);
}
function marketList(data) {
  if (typeof data.paused !== 'boolean' || !Array.isArray(data.markets)) fail('invalid_service_markets');
  u64(data.minMargin, 1n);
  for (const [asset, pinned] of Object.entries(MARKETS)) {
    const rows = data.markets.filter(m => m.symbol === asset);
    if (rows.length !== 1 || rows[0].address !== pinned || typeof rows[0].closed !== 'boolean' || typeof rows[0].closeOnly !== 'boolean') fail('service_market_pin_mismatch');
  }
  if (!Number.isSafeInteger(data.fees?.closeFeePpm) || !Number.isSafeInteger(data.fees?.winFeePpm) || data.fees.closeFeePpm < 0 || data.fees.winFeePpm < 0) fail('invalid_service_fees');
  return data;
}
function userPositions(data, owner) {
  if (!Array.isArray(data.positions) || !Array.isArray(data.claims)) fail('invalid_service_user');
  u64(data.queued);
  return data.positions.map(p => {
    if (address(p.owner) !== owner || typeof p.isLong !== 'boolean') fail('invalid_service_position');
    address(p.address); address(p.market); u64(p.id); u64(p.margin, 1n); u64(p.notional, 1n); u64(p.entryPrice, 1n); u64(p.updateTime);
    return p;
  });
}
function closePosition(rows, intent, now) {
  const p = rows.find(p => p.address === intent.position && p.market === MARKETS[intent.asset]);
  if (!p) fail('service_position_not_owned_or_open');
  if (now - Number(p.updateTime) < 15) fail('position_updated_recently_minimum_15_seconds');
  if (p.triggerOrder || p.closeTimer) fail('position_has_trigger_order_or_close_timer');
  return p;
}

// Observed public service layout; inspection never authorizes signing or submission.
const UPDATE_PRICE_DISCRIMINATOR = Buffer.from('3d22759b4b227bd0', 'hex');
const ORACLE_PRICE_DISCRIMINATOR = createHash('sha256').update('account:OraclePrice').digest().subarray(0, 8);
const PYTH_CONFIG = new PublicKey('3rdJbqfnagQ4yx9HXJViD4zc4xpiSqmFsKpPuSCQVyQL');
const PYTH_TREASURY = new PublicKey('Gx4MBPb1vqZLJajZmsKLg8fGw9ErhoKsR8LeKcCKFyak');
const PYTH_PROGRAM = new PublicKey('pytd2yyk641x7ak7mkaasSJVXh6YYZnC7wTmtgAyxPt');

/** Inspect and simulate only. This result is never accepted by the execution verifier. */
export async function inspectOpenBuild(build, intent, { connection, now = Math.floor(Date.now() / 1000), readAccount = owned, skipSimulation = false } = {}) {
  if (sdk.WINNING_PROGRAM_ID.toBase58() !== PROGRAM || !MARKETS[intent.asset]) fail('invalid_service_intent');
  const owner = new PublicKey(intent.owner), market = new PublicKey(MARKETS[intent.asset]);
  const tx = VersionedTransaction.deserialize(base64(build.serializedTxBase64));
  if (tx.version !== 0 || tx.message.header.numRequiredSignatures !== 2 || !tx.message.staticAccountKeys[0].equals(owner)) fail('invalid_service_signers_or_version');
  const keeper = tx.message.staticAccountKeys[1];
  if (keeper.equals(owner) || tx.signatures.some(s => s.some(b => b !== 0))) fail('unexpected_preexisting_signature');
  if (!build.txMetadata || tx.message.recentBlockhash !== address(build.txMetadata.blockhash)) fail('service_blockhash_mismatch');
  if (BigInt(await connection.getBlockHeight('confirmed')) > u64(build.txMetadata.lastValidBlockHeight)) fail('service_blockhash_expired');
  const [config] = await sdk.findConfigPda(program), [pool] = await sdk.findPoolPda(program), [vault] = await sdk.findVaultPda(program);
  const settings = await readAccount(connection, config, sdk.deserializeConfigAccount);
  if (settings.paused) fail('service_program_paused');
  const lookups = [];
  for (const item of tx.message.addressTableLookups) {
    const result = await connection.getAddressLookupTable(item.accountKey);
    if (!result.value) fail('unavailable_address_lookup_table');
    lookups.push(result.value);
  }
  const message = TransactionMessage.decompile(tx.message, { addressLookupTableAccounts: lookups });
  const trades = message.instructions.filter(ix => ix.programId.equals(program));
  if (trades.length !== 2 || message.instructions.indexOf(trades[0]) > message.instructions.indexOf(trades[1])) fail('unexpected_service_instruction');
  const [update, open] = trades;
  if (update.data.length !== 133 || !update.data.subarray(0, 8).equals(UPDATE_PRICE_DISCRIMINATOR) || sdk.identifyWinningInstruction(open) !== sdk.WinningInstruction.OpenPosition) fail('unexpected_service_instruction');
  const parsed = sdk.parseOpenPositionInstruction(open), margin = u64(intent.margin, 5000000n);
  if (intent.operation !== 'open' || intent.leverage !== 1000 || !['long', 'short'].includes(intent.side) || BigInt(parsed.data.margin) !== margin || parsed.data.leverage !== 1000 || parsed.data.long !== (intent.side === 'long')) fail('sdk_trade_intent_mismatch');
  const [position] = await sdk.findPositionPda({ owner, id: parsed.data.id }, program);
  if (build.positionId !== undefined && BigInt(build.positionId) !== BigInt(parsed.data.id)) fail('service_position_id_mismatch');
  const [funding] = PublicKey.findProgramAddressSync([owner.toBuffer(), token.toBuffer(), new PublicKey(USD_MINT).toBuffer()], associated);
  const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from('__event_authority')], program);
  // Current on-chain price accounts derive from the selected market mint. The old
  // SDK's market.oracle field is not reliable for all current markets (BTC differs).
  // This relationship constrains inspection; it does not establish update authority.
  const marketData = await readAccount(connection, market, sdk.deserializeMarketAccount);
  const [oracle, oracleBump] = PublicKey.findProgramAddressSync([Buffer.from('price'), marketData.mint.toBuffer()], program);
  if (!parsed.accounts.oracle.pubkey.equals(oracle)) fail('inspection_oracle_market_mismatch');
  const oracleAccount = await connection.getAccountInfo(oracle, 'confirmed');
  if (!oracleAccount || oracleAccount.executable || !oracleAccount.owner.equals(program)) fail('unverified_program_account');
  const oracleBytes = oracleAccount.data;
  if (!Buffer.isBuffer(oracleBytes) || oracleBytes.length !== 61 || !oracleBytes.subarray(0, 8).equals(ORACLE_PRICE_DISCRIMINATOR) || !oracleBytes.subarray(8, 40).equals(marketData.mint.toBuffer()) || oracleBytes[60] !== oracleBump) fail('inspection_invalid_oracle_account');
  const expectedOpen = await sdk.createOpenPositionInstruction({ owner, keeper, config, market, pool, vault, usdMint: new PublicKey(USD_MINT), oracle, tokenProgram: token, systemProgram: system, eventAuthority, program, position, fundingAccount: funding }, parsed.data, program);
  // v0 message privileges are global: UpdatePrice legitimately upgrades its shared keeper and oracle to writable.
  if (!open.data.equals(expectedOpen.data) || open.keys.length !== expectedOpen.keys.length || open.keys.some((k, i) => !k.pubkey.equals(expectedOpen.keys[i].pubkey) || k.isSigner !== expectedOpen.keys[i].isSigner || k.isWritable !== (expectedOpen.keys[i].isWritable || i === 1 || i === 9))) fail('sdk_account_or_instruction_mismatch');
  const expectedUpdate = [keeper, config, PYTH_CONFIG, PYTH_TREASURY, PYTH_PROGRAM, system, oracle];
  const flags = [[true,true],[false,false],[false,false],[false,true],[false,false],[false,false],[false,true]];
  if (update.keys.length !== expectedUpdate.length || update.keys.some((k,i) => !k.pubkey.equals(expectedUpdate[i]) || k.isSigner !== flags[i][0] || k.isWritable !== flags[i][1])) fail('unexpected_price_update_accounts');
  const requestTime = Number(parsed.data.requestTime), maxAge = Math.min(30, settings.settings.maxRequestExecutionSec);
  if (!Number.isSafeInteger(requestTime) || requestTime > now + 2 || now - requestTime > maxAge) fail('service_execution_window_elapsed');
  let price = 0n, units = 1400000n; const computeKinds = new Set();
  for (const ix of message.instructions) {
    if (ix === update || ix === open) continue;
    if (ix.programId.toBase58() !== compute || ix.keys.length || ![2,3].includes(ix.data[0]) || computeKinds.has(ix.data[0])) fail('unexpected_service_instruction');
    computeKinds.add(ix.data[0]);
    if (ix.data[0] === 2 && ix.data.length === 5) { units = BigInt(ix.data.readUInt32LE(1)); if (units > 1400000n) fail('compute_unit_limit'); }
    else if (ix.data[0] === 3 && ix.data.length === 9) price = ix.data.readBigUInt64LE(1);
    else fail('unsupported_compute_instruction');
  }
  if (price * units > 10000000n * 1000000n) fail('priority_fee_over_001_sol');
  const checked = { owner: owner.toBase58(), asset: intent.asset, side: intent.side, margin: margin.toString(), leverage: 1000, position: position.toBase58(), program: PROGRAM, messageSha256: hash(tx.message.serialize()) };
  if (skipSimulation) return { status: 'structural', checked };
  const simulated = await connection.simulateTransaction(tx, { sigVerify: false, replaceRecentBlockhash: true, commitment: 'confirmed' });
  if (!simulated?.value || simulated.value.err) {
    const failure = simulated?.value?.err?.InstructionError;
    const instruction = Array.isArray(failure) && Number.isSafeInteger(failure[0]) && failure[0] >= 0 ? failure[0] : null;
    const custom = failure?.[1]?.Custom;
    const programCode = Number.isSafeInteger(custom) && custom >= 0 ? custom : null;
    const detail = instruction === null ? '' : ` at instruction ${instruction}${programCode === null ? '' : ` (program code ${programCode})`}`;
    return { status: 'blocked', code: 'unsigned_simulation_failed', simulation: { instruction, programCode }, message: `The unsigned 1000x simulation failed${detail}. No signature or order was sent.` };
  }
  return { status: 'inspection', checked, simulation: { status: 'passed', unitsConsumed: simulated.value.unitsConsumed ?? null }, message: 'Unsigned simulation passed. Inspection only: the current verifier cannot establish the service keeper authorization; Submit is disabled. No signature or order was sent.' };
}

/** No secret or signing operation. Validate the exact bytes the wallet would sign. */
async function verifyLegacyBuild(build, intent, { connection, now = Math.floor(Date.now() / 1000), readAccount = owned } = {}) {
  if (sdk.WINNING_PROGRAM_ID.toBase58() !== PROGRAM) fail('sdk_program_pin_mismatch');
  if (!MARKETS[intent.asset] || !['open', 'close'].includes(intent.operation)) fail('invalid_service_intent');
  const owner = new PublicKey(intent.owner), market = new PublicKey(MARKETS[intent.asset]);
  if (typeof build.buildToken !== 'string' || build.buildToken.length < 1 || build.buildToken.length > 88) fail('invalid_build_token');
  const tx = VersionedTransaction.deserialize(base64(build.serializedTxBase64));
  if (tx.version !== 0 || tx.message.header.numRequiredSignatures !== 2 || !tx.message.staticAccountKeys[0].equals(owner)) fail('invalid_service_signers_or_version');
  if (!build.txMetadata || tx.message.recentBlockhash !== address(build.txMetadata.blockhash)) fail('service_blockhash_mismatch');
  const lastValid = u64(build.txMetadata.lastValidBlockHeight);
  if (BigInt(await connection.getBlockHeight('confirmed')) > lastValid) fail('service_blockhash_expired');
  if (tx.signatures.some(s => s.some(b => b !== 0))) fail('unexpected_preexisting_signature');
  const [config] = await sdk.findConfigPda(program), [pool] = await sdk.findPoolPda(program), [vault] = await sdk.findVaultPda(program);
  const settings = await readAccount(connection, config, sdk.deserializeConfigAccount);
  if (settings.paused) fail('service_program_paused');
  if (settings.keeper.equals(owner)) fail('service_owner_is_keeper');
  if (!tx.message.staticAccountKeys[1].equals(settings.keeper)) fail('service_keeper_mismatch');
  const marketData = await readAccount(connection, market, sdk.deserializeMarketAccount);
  const lookupAccounts = [];
  for (const lookup of tx.message.addressTableLookups) {
    const resolved = await connection.getAddressLookupTable(lookup.accountKey);
    if (!resolved.value) fail('unavailable_address_lookup_table');
    lookupAccounts.push(resolved.value);
  }
  const message = TransactionMessage.decompile(tx.message, { addressLookupTableAccounts: lookupAccounts });
  const [funding] = PublicKey.findProgramAddressSync([owner.toBuffer(), token.toBuffer(), new PublicKey(USD_MINT).toBuffer()], associated);
  const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from('__event_authority')], program);
  const common = { owner, keeper: settings.keeper, config, market, pool, vault, usdMint: new PublicKey(USD_MINT),
    oracle: marketData.oracle, tokenProgram: token, systemProgram: system, eventAuthority, program };
  // Without an explicit limit, the runtime default depends on instructions.
  // Price against the transaction ceiling rather than assuming one200k budget.
  let checked, count = 0, price = 0n, units = 1400000n;
  const computeKinds = new Set();
  for (const instruction of message.instructions) {
    const pid = instruction.programId.toBase58();
    if (pid === compute) {
      const data = instruction.data;
      if (instruction.keys.length || ![2, 3].includes(data[0])) fail('unsupported_compute_instruction');
      if (computeKinds.has(data[0])) fail('duplicate_compute_instruction');
      computeKinds.add(data[0]);
      if (data[0] === 2 && data.length === 5) { units = BigInt(data.readUInt32LE(1)); if (units > 1400000n) fail('compute_unit_limit'); }
      else if (data[0] === 3 && data.length === 9) price = data.readBigUInt64LE(1);
      else fail('unsupported_compute_instruction');
      continue;
    }
    if (pid === associated.toBase58()) {
      const keys = instruction.keys.map(k => k.pubkey.toBase58());
      if (instruction.data.length !== 1 || instruction.data[0] !== 1 || keys.length !== 6 || keys.join(',') !== [owner, funding, owner, new PublicKey(USD_MINT), system, token].map(k => k.toBase58()).join(',')) fail('unsupported_associated_account_instruction');
      continue;
    }
    if (pid !== PROGRAM || ++count !== 1) fail('unexpected_service_instruction');
    let parsed, expected;
    if (intent.operation === 'open') {
      if (sdk.identifyWinningInstruction(instruction) !== sdk.WinningInstruction.OpenPosition) fail('unexpected_sdk_operation');
      parsed = sdk.parseOpenPositionInstruction(instruction);
      const margin = u64(intent.margin, 5000000n);
      if (intent.leverage !== 1000 || !['long', 'short'].includes(intent.side) || BigInt(parsed.data.margin) !== margin || parsed.data.leverage !== 1000 || parsed.data.long !== (intent.side === 'long')) fail('sdk_trade_intent_mismatch');
      const [position] = await sdk.findPositionPda({ owner, id: parsed.data.id }, program);
      if (build.positionId !== undefined && BigInt(build.positionId) !== BigInt(parsed.data.id)) fail('service_position_id_mismatch');
      expected = await sdk.createOpenPositionInstruction({ ...common, position, fundingAccount: funding }, parsed.data, program);
      checked = { position: position.toBase58(), margin: margin.toString(), leverage: 1000, side: intent.side };
    } else {
      if (sdk.identifyWinningInstruction(instruction) !== sdk.WinningInstruction.ClosePosition) fail('unexpected_sdk_operation');
      parsed = sdk.parseClosePositionInstruction(instruction);
      const position = new PublicKey(intent.position);
      const data = await readAccount(connection, position, sdk.deserializePositionAccount);
      if (!data.owner.equals(owner) || !data.market.equals(market) || !data.isOpen || now - Number(data.updateTime) < 15) fail('service_position_not_owned_open_or_old_enough');
      expected = await sdk.createClosePositionInstruction({ ...common, position, claim: parsed.accounts.claim.pubkey, destination: funding }, parsed.data, program);
      checked = { position: position.toBase58() };
    }
    const requestTime = Number(parsed.data.requestTime);
    const maxAge = Math.min(30, settings.settings.maxRequestExecutionSec);
    if (!Number.isSafeInteger(requestTime) || requestTime > now + 2 || now - requestTime > maxAge) fail('service_execution_window_elapsed');
    if (!instruction.data.equals(expected.data) || instruction.keys.length !== expected.keys.length || instruction.keys.some((k, i) => !k.pubkey.equals(expected.keys[i].pubkey) || k.isSigner !== expected.keys[i].isSigner || k.isWritable !== expected.keys[i].isWritable)) fail('sdk_account_or_instruction_mismatch');
    checked.requestTime = requestTime;
  }
  if (count !== 1 || price * units > 10000000n * 1000000n) fail('missing_trade_or_priority_fee_over_001_sol');
  return { ...checked, owner: owner.toBase58(), asset: intent.asset, operation: intent.operation, program: PROGRAM,
    keeper: settings.keeper.toBase58(), messageSha256: hash(tx.message.serialize()) };
}
/** Select the observed current format only by its update instruction; legacy remains unchanged. */
export async function verifyBuild(build, intent, options = {}) {
  const tx = VersionedTransaction.deserialize(base64(build.serializedTxBase64));
  const lookups = [];
  for (const item of tx.message.addressTableLookups) {
    let value;
    try { value = (await options.connection.getAddressLookupTable(item.accountKey)).value; } catch { fail('current_rpc_unavailable'); }
    if (!value) fail('unavailable_address_lookup_table');
    lookups.push(value);
  }
  const msg = TransactionMessage.decompile(tx.message, { addressLookupTableAccounts: lookups });
  const trade = msg.instructions.filter(ix => ix.programId.equals(program));
  if (trade[0]?.data.subarray(0, 8).equals(UPDATE_PRICE_DISCRIMINATOR)) {
    if (intent.operation !== 'open') fail('current_close_unverified');
    try { return await verifyCurrentOpen(build, intent, { ...options, readAccount: options.readAccount || owned }, inspectOpenBuild); }
    catch (error) { if (error.message.startsWith('current_')) throw error; if (/^[a-z_0-9]+$/.test(error.message)) fail('current_' + error.message); fail('current_rpc_unavailable'); }
  }
  return verifyLegacyBuild(build, intent, options);
}
export function verifySigned(build, signed, ownerAddress) {
  const original = VersionedTransaction.deserialize(base64(build.serializedTxBase64));
  const tx = VersionedTransaction.deserialize(base64(signed));
  const owner = new PublicKey(ownerAddress);
  if (tx.version !== 0 || original.version !== 0 || tx.message.header.numRequiredSignatures !== 2 || !tx.message.staticAccountKeys[0].equals(owner) || !Buffer.from(tx.message.serialize()).equals(Buffer.from(original.message.serialize()))) fail('signed_transaction_message_changed');
  if (tx.signatures.length !== original.signatures.length || tx.signatures.slice(1).some((s, i) => !Buffer.from(s).equals(Buffer.from(original.signatures[i + 1])))) fail('other_signature_changed');
  const publicKey = createPublicKey({ key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), owner.toBuffer()]), format: 'der', type: 'spki' });
  if (!verify(null, tx.message.serialize(), publicKey, tx.signatures[0])) fail('invalid_owner_signature');
  return base58(tx.signatures[0]);
}

export async function serviceHandle(payload, dependencies = {}) {
  const api = dependencies.api || apiRequest, connection = rpc(payload, dependencies.connection);
  const now = dependencies.now ?? Math.floor(Date.now() / 1000);
  const options = { connection, now, readAccount: dependencies.readAccount || owned };
  if (payload.action === 'service-markets') return { status: 'ready', service: SERVICE, program: PROGRAM, ...marketList(await api('markets')) };
  const owner = address(payload.owner);
  if (payload.action === 'service-positions') {
    const data = await api('users/' + owner), rows = userPositions(data, owner);
    return { status: 'ready', queued: data.queued, claims: data.claims, positions: rows.filter(p => Object.values(MARKETS).includes(p.market)).map(p => ({ ...p, asset: Object.keys(MARKETS).find(a => MARKETS[a] === p.market) })) };
  }
  if (payload.action === 'service-request') {
    if (typeof payload.signature !== 'string' || !/^[1-9A-HJ-NP-Za-km-z]{64,100}$/.test(payload.signature)) fail('invalid_request_signature');
    return { status: 'ready', request: await api('requests/' + payload.signature) };
  }
  if (['service-build-open', 'service-build-close', 'service-inspect-open'].includes(payload.action)) {
    const markets = marketList(await api('markets'));
    const row = markets.markets.find(m => m.symbol === payload.asset);
    if (!row || markets.paused || row.closed || (payload.action !== 'service-build-close' && row.closeOnly)) fail('service_market_unavailable');
    const intent = { owner, asset: payload.asset, operation: payload.action !== 'service-build-close' ? 'open' : 'close' };
    let request;
    if (intent.operation === 'open') {
      if (payload.leverage !== 1000 || !['long', 'short'].includes(payload.side)) fail('invalid_1000x_direction_or_leverage');
      u64(payload.margin, u64(markets.minMargin, 1n));
      Object.assign(intent, { side: payload.side, margin: payload.margin, leverage: 1000 });
      request = { action: 'open', owner, market: payload.asset, leverage: 1000, long: payload.side === 'long', margin: payload.margin, transactionVersion: 0 };
    } else {
      intent.position = address(payload.position);
      closePosition(userPositions(await api('users/' + owner), owner), intent, now);
      request = { action: 'close', owner, market: payload.asset, position: intent.position, transactionVersion: 0 };
    }
    let build;
    try { build = await api('transactions/build', request); }
    catch (error) {
      if (error.message === 'service_400_insufficient_balance') return { status: 'blocked', code: error.message,
        message: 'The 1000x service build requires enough JupUSD collateral and SOL network balance in the existing wallet. No transaction was signed or submitted.' };
      const code = /^service_[0-9]{3}_[a-z_]{1,80}$/.test(error.message) ? error.message : 'current_service_unavailable';
      return { status: 'blocked', code, message: 'The 1000x service build is unavailable. No signature or order was sent.' };
    }
    const verificationOptions = { ...options, now: dependencies.now ?? Math.floor(Date.now() / 1000) };
    if (payload.action === 'service-inspect-open') {
      const inspection = await inspectOpenBuild(build, intent, verificationOptions);
      return { ...inspection, fees: markets.fees, collateralMint: USD_MINT };
    }
    let checked;
    try { checked = await verifyBuild(build, intent, verificationOptions); }
    catch (error) { if (!error.message.startsWith('current_')) throw error; return { status: 'blocked', code: error.message, message: 'The current 1000x build could not pass transaction verification. No signature or order was sent.' }; }
    return { status: 'ready', build, intent, checked, fees: markets.fees, collateralMint: USD_MINT,
      message: 'Official service transaction checked with the pinned SDK. No owner signature or execution yet.' };
  }
  if (['service-signed', 'service-execute'].includes(payload.action)) {
    const preview = payload.preview;
    if (!preview || preview.intent?.owner !== owner) fail('preview_owner_mismatch');
    let checked;
    try { checked = await verifyBuild(preview.build, preview.intent, options); }
    catch (error) { if (!error.message.startsWith('current_')) throw error; return { status: 'blocked', code: error.message, message: 'The current 1000x build could not pass transaction verification. No order was sent.' }; }
    if (checked.messageSha256 !== preview.checked?.messageSha256) fail('preview_message_binding_mismatch');
    const signature = verifySigned(preview.build, payload.serializedTxBase64, owner);
    if (payload.action === 'service-signed') return { status: 'ready', signature };
    if (preview.intent.operation === 'close') closePosition(userPositions(await api('users/' + owner), owner), preview.intent, now);
    const result = await api('transactions/execute', { serializedTxBase64: payload.serializedTxBase64, buildToken: preview.build.buildToken });
    if (result.txid !== signature || !['Processing', 'Completed', 'Failed'].includes(result.status) || ![null, 'execution_failed', 'execution_window_elapsed'].includes(result.error)) fail('invalid_service_execute_response');
    return { status: result.status === 'Failed' ? 'failed' : 'submitted', signature, service_status: result.status,
      queue_position: result.queuePosition ?? null, error: result.error };
  }
  fail('unsupported_service_action');
}
