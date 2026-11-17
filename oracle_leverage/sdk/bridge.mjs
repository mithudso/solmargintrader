/** Pinned SDK instruction construction and checked official keeper service. */
import { randomBytes } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { Connection, PublicKey, SystemProgram, TransactionMessage, VersionedTransaction } from '@solana/web3.js';
import * as sdk from 'jupiter-sdk/yolo/web3js';
import { serviceHandle } from './service.mjs';

export const PROGRAM = 'yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA';
export const USD_MINT = 'JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD';
const TOKEN = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const ASSOCIATED_TOKEN = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');
const program = new PublicKey(PROGRAM);

function refuse(message) { throw new Error(message); }
function key(value) {
  try { return new PublicKey(value); } catch { return refuse('invalid_public_account'); }
}
function integer(value, name, minimum = 0n) {
  if (!/^[0-9]+$/.test(String(value))) refuse(`invalid_${name}`);
  const result = BigInt(value);
  if (result < minimum || result > (1n << 64n) - 1n) refuse(`invalid_${name}`);
  return result;
}
function noSecrets(value) {
  if (value && typeof value === 'object') {
    for (const [name, item] of Object.entries(value)) {
      if (/private.?key|secret|mnemonic|seed|authorization|api.?key|bearer/i.test(name)) refuse('secret_input_refused');
      noSecrets(item);
    }
  }
}
function instructionJSON(instruction) {
  return { programId: instruction.programId.toBase58(), dataBase64: instruction.data.toString('base64'),
    accounts: instruction.keys.map(k => ({ address: k.pubkey.toBase58(), signer: k.isSigner, writable: k.isWritable })) };
}
function rpcFor(payload, injected) {
  if (injected) return injected;
  const url = new URL(payload.rpcUrl || 'https://api.mainnet-beta.solana.com');
  if (url.protocol !== 'https:' || url.username || url.password) refuse('invalid_rpc_url');
  return new Connection(url.toString(), { commitment: 'confirmed', disableRetryOnRateLimit: true,
    fetch: async (url, init) => fetch(url, { ...init, signal: AbortSignal.timeout(8000) }) });
}
async function ownedAccount(connection, address, decoder) {
  const account = await connection.getAccountInfo(address, 'confirmed');
  if (!account || !account.owner.equals(program) || account.executable) refuse('unverified_program_account');
  return decoder(account.data);
}

export async function handle(payload, { connection: injected } = {}) {
  noSecrets(payload);
  if (sdk.WINNING_PROGRAM_ID.toBase58() !== PROGRAM) refuse('sdk_program_pin_mismatch');
  const action = payload.action;
  if (typeof action === 'string' && action.startsWith('service-')) return serviceHandle(payload, { connection: injected });
  if (!['status', 'build-open', 'build-close', 'simulate'].includes(action)) refuse('funded_submission_not_supported');
  const [config] = await sdk.findConfigPda(program);
  const [pool] = await sdk.findPoolPda(program);
  const [vault] = await sdk.findVaultPda(program);
  const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from('__event_authority')], program);
  if (action === 'status') {
    return { status: 'ready', sdkVersion: '0.6.0', program: PROGRAM, config: config.toBase58(),
      pool: pool.toBase58(), vault: vault.toBase58(), usdMint: USD_MINT,
      requiredSignatures: ['owner', 'keeper'], fundedSubmitAvailable: false,
      serviceSubmitAvailable: true, service: 'https://yolo-api.jup.ag',
      message: 'Pinned community SDK loaded; official app program and keeper service matched. Raw builders remain unsigned.' };
  }
  if (!['ZEC', 'BTC'].includes(payload.asset)) refuse('unsupported_asset');
  const owner = key(payload.owner);
  const mapping = payload.markets?.[payload.asset] || payload.market;
  if (!mapping) return { status: 'blocked', message: 'A verified public market/account mapping is required; no asset address is guessed.' };
  const market = key(mapping);
  let keeper, oracle;
  if (payload.accounts) {
    // Offline, unsigned construction for independently checked account mappings.
    keeper = key(payload.accounts.keeper);
    oracle = key(payload.accounts.oracle);
  } else {
    const connection = rpcFor(payload, injected);
    const settings = await ownedAccount(connection, config, sdk.deserializeConfigAccount);
    if (settings.paused) refuse('program_paused');
    keeper = settings.keeper;
    const marketData = await ownedAccount(connection, market, sdk.deserializeMarketAccount);
    oracle = marketData.oracle;
  }
  if (keeper.equals(owner)) refuse('owner_cannot_substitute_for_keeper');
  const usdMint = new PublicKey(USD_MINT);
  const [funding] = PublicKey.findProgramAddressSync([owner.toBuffer(), TOKEN.toBuffer(), usdMint.toBuffer()], ASSOCIATED_TOKEN);
  const common = { owner, keeper, config, market, pool, vault, usdMint, oracle,
    tokenProgram: TOKEN, systemProgram: SystemProgram.programId, eventAuthority, program };
  const requestTime = integer(payload.requestTime ?? Math.floor(Date.now() / 1000), 'request_time');
  let instruction, position;
  if (action === 'build-close' || payload.operation === 'close') {
    position = key(payload.position);
    if (!payload.claim) return { status: 'blocked', message: 'Close requires a verified claim PDA; no queue sequence is guessed.' };
    instruction = await sdk.createClosePositionInstruction({ ...common, position,
      claim: key(payload.claim), destination: funding }, { requestTime }, program);
  } else {
    if (!['long', 'short'].includes(payload.side) || payload.leverage !== 1000) refuse('invalid_1000x_direction_or_leverage');
    const margin = integer(payload.margin, 'margin', 5000000n);
    const id = integer(payload.id ?? randomBytes(8).readBigUInt64LE(), 'position_id');
    [position] = await sdk.findPositionPda({ owner, id }, program);
    instruction = await sdk.createOpenPositionInstruction({ ...common, fundingAccount: funding, position },
      { id, requestTime, margin, leverage: 1000, long: payload.side === 'long' }, program);
    const decoded = sdk.parseOpenPositionInstruction(instruction);
    if (decoded.data.margin !== margin || decoded.data.leverage !== 1000 || decoded.data.long !== (payload.side === 'long')) refuse('instruction_intent_mismatch');
  }
  const result = { status: 'dry-run', asset: payload.asset, leverage: 1000, position: position.toBase58(),
    instruction: instructionJSON(instruction), requiredSignatures: [owner.toBase58(), keeper.toBase58()],
    fundedSubmitAvailable: false, message: 'Unsigned SDK instruction. Both owner and keeper signatures are required; nothing sent.' };
  if (action !== 'simulate') return result;
  const connection = rpcFor(payload, injected);
  const latest = await connection.getLatestBlockhash('confirmed');
  const transaction = new VersionedTransaction(new TransactionMessage({ payerKey: owner,
    recentBlockhash: latest.blockhash, instructions: [instruction] }).compileToV0Message());
  // RPC simulation skips signature verification only; it neither signs nor sends.
  const response = await connection.simulateTransaction(transaction,
    { sigVerify: false, replaceRecentBlockhash: true, commitment: 'confirmed' });
  return { ...result, simulation: response.value ?? null,
    status: response.value?.err ? 'blocked' : 'dry-run', message: 'Unsigned RPC simulation only; no signature or funded transaction submitted.' };
}

async function main() {
  const chunks = []; let bytes = 0;
  for await (const chunk of process.stdin) {
    bytes += chunk.length;
    if (bytes > 65536) refuse('request_too_large');
    chunks.push(chunk);
  }
  const result = await handle(JSON.parse(Buffer.concat(chunks).toString('utf8')));
  process.stdout.write(JSON.stringify(result, (_, value) => typeof value === 'bigint' ? value.toString() : value) + '\n');
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    const safe = /^[a-z_0-9]+$/.test(error.message) ? error.message : 'sdk_request_failed';
    process.stdout.write(JSON.stringify({ status: 'error', message: safe }) + '\n');
    process.exitCode = 1;
  });
}
