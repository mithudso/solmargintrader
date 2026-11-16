import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { Keypair, PublicKey, SystemProgram, TransactionInstruction, TransactionMessage, VersionedTransaction } from '@solana/web3.js';
import { secp256k1 } from '@noble/curves/secp256k1';
import { keccak_256 } from '@noble/hashes/sha3';
import * as sdk from 'jupiter-sdk/yolo/web3js';
import { inspectOpenBuild, MARKETS, PROGRAM, USD_MINT, serviceHandle } from '../service.mjs';
import { verifyCurrentOpen } from '../current-open.mjs';

const key = n => new PublicKey(Buffer.alloc(32, n));
const hash8 = s => createHash('sha256').update('account:' + s).digest().subarray(0, 8);
const program = new PublicKey(PROGRAM), token = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const pyth = new PublicKey('pytd2yyk641x7ak7mkaasSJVXh6YYZnC7wTmtgAyxPt');
const storageKey = new PublicKey('3rdJbqfnagQ4yx9HXJViD4zc4xpiSqmFsKpPuSCQVyQL');
const treasury = new PublicKey('Gx4MBPb1vqZLJajZmsKLg8fGw9ErhoKsR8LeKcCKFyak');
const associated = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');
const keeper = new PublicKey('2BcxBiR3KiUwnSwM8eViGj9hp7s9JRi4QqiWuVU8Eve7');
const now = 1794840000;
function rpcAccount(owner, data, lamports) { return { owner: owner.toBase58(), data: [data.toString('base64'), 'base64'], executable: false, lamports, rentEpoch: 99, space: data.length }; }
function tokenData(mint, owner, amount) { const d = Buffer.alloc(165); mint.toBuffer().copy(d); owner.toBuffer().copy(d, 32); d.writeBigUInt64LE(amount, 64); d[108] = 1; return d; }
function signedPrice() {
  const data = Buffer.alloc(133); Buffer.from('3d22759b4b227bd0','hex').copy(data); data.writeUInt32LE(121,8); data.writeUInt32LE(1296547300,12); data.writeUInt16LE(50,81); data.writeUInt32LE(2479346549,83); data.writeBigUInt64LE(BigInt(now)*1000000n,87); data[95]=3;data[96]=1;data.writeUInt32LE(1,97);data[101]=4;data.writeBigInt64LE(6500000000000n,103);data[111]=4;data.writeInt16LE(-8,112);data[114]=5;data.writeBigInt64LE(10000n,115);data[123]=12;data[124]=1;data.writeBigUInt64LE(BigInt(now)*1000000n,125);
  const priv = Buffer.alloc(32,7), signature = secp256k1.sign(keccak_256(data.subarray(83)),priv); Buffer.from(signature.toCompactRawBytes()).copy(data,16);data[80]=signature.recovery;
  const store = Buffer.alloc(381);hash8('Storage').copy(store);treasury.toBuffer().copy(store,40);store.writeBigUInt64LE(1n,72);store[281]=1;const pub=secp256k1.getPublicKey(priv,false);Buffer.from(keccak_256(pub.subarray(1))).subarray(12).copy(store,282);store.writeBigInt64LE(BigInt(now+30),302);
  return { data, storage: { owner: pyth, executable: false, data: store } };
}
async function setup() {
  const owner=Keypair.fromSeed(Buffer.alloc(32,1)).publicKey, mint=key(5), usd=new PublicKey(USD_MINT), market=new PublicKey(MARKETS.BTC);
  const [config]=await sdk.findConfigPda(program), [pool]=await sdk.findPoolPda(program), [vault]=await sdk.findVaultPda(program), [position,bump]=await sdk.findPositionPda({owner,id:17n},program);
  const [funding]=PublicKey.findProgramAddressSync([owner.toBuffer(),token.toBuffer(),usd.toBuffer()],associated), [eventAuthority]=PublicKey.findProgramAddressSync([Buffer.from('__event_authority')],program), [oracle,oracleBump]=PublicKey.findProgramAddressSync([Buffer.from('price'),mint.toBuffer()],program);
  const {data,storage}=signedPrice();
  const update=new TransactionInstruction({programId:program,data,keys:[{pubkey:keeper,isSigner:true,isWritable:true},{pubkey:config,isSigner:false,isWritable:false},{pubkey:storageKey,isSigner:false,isWritable:false},{pubkey:treasury,isSigner:false,isWritable:true},{pubkey:pyth,isSigner:false,isWritable:false},{pubkey:SystemProgram.programId,isSigner:false,isWritable:false},{pubkey:oracle,isSigner:false,isWritable:true}]});
  const open=await sdk.createOpenPositionInstruction({owner,keeper,config,market,pool,vault,usdMint:usd,oracle,tokenProgram:token,systemProgram:SystemProgram.programId,eventAuthority,program,position,fundingAccount:funding},{id:17n,requestTime:BigInt(now),margin:5000000n,leverage:1000,long:true},program);
  const tx=new VersionedTransaction(new TransactionMessage({payerKey:owner,recentBlockhash:key(7).toBase58(),instructions:[update,open]}).compileToV0Message());
  const build={serializedTxBase64:Buffer.from(tx.serialize()).toString('base64'),buildToken:'fixture',positionId:'17',txMetadata:{blockhash:key(7).toBase58(),lastValidBlockHeight:'200'}};
  const cfg=Buffer.alloc(126);Buffer.from(sdk.CONFIG_ACCOUNT_DISCRIMINATOR).copy(cfg);keeper.toBuffer().copy(cfg,40);cfg.writeBigUInt64LE(5000000n,104);cfg.writeUInt32LE(10,112);cfg.writeUInt32LE(3,116);cfg.writeUInt32LE(20,120);
  const settings={keeper,paused:false,settings:{minMargin:5000000n,maxOracleAgeSecs:10,maxOracleFutureSecs:3,maxRequestExecutionSec:20}};
  const oracleData=(time,value)=>{const d=Buffer.alloc(61);hash8('OraclePrice').copy(d);mint.toBuffer().copy(d,8);d.writeUInt32LE(1,40);d.writeBigUInt64LE(value,44);d.writeBigUInt64LE(time,52);d[60]=oracleBump;return d};
  const oldOracle=oracleData(BigInt(now-1)*1000000n,64900000000000000n), newOracle=oracleData(BigInt(now+1)*1000000n,65100000000000000n);
  const pos=Buffer.alloc(120);Buffer.from(sdk.POSITION_ACCOUNT_DISCRIMINATOR).copy(pos);owner.toBuffer().copy(pos,8);market.toBuffer().copy(pos,40);pos.writeBigUInt64LE(17n,72);pos[80]=1;pos.writeBigUInt64LE(5000000n,81);pos.writeBigUInt64LE(5000000000n,89);pos.writeBigUInt64LE(65100000000000000n,97);pos.writeBigInt64LE(BigInt(now+1),105);pos[113]=bump;pos[114]=1;
  const before=[rpcAccount(SystemProgram.programId,Buffer.alloc(0),10000000),rpcAccount(SystemProgram.programId,Buffer.alloc(0),1000),rpcAccount(token,tokenData(usd,owner,6000000n),1488440),rpcAccount(token,tokenData(usd,pool,9000000n),1488440),null,rpcAccount(program,oldOracle,960120)];
  const after=[rpcAccount(SystemProgram.programId,Buffer.alloc(0),8730160),rpcAccount(SystemProgram.programId,Buffer.alloc(0),999),rpcAccount(token,tokenData(usd,owner,1000000n),1488440),rpcAccount(token,tokenData(usd,pool,14000000n),1488440),rpcAccount(program,pos,1259840),rpcAccount(program,newOracle,960120)];
  const connection={rpcEndpoint:'https://rpc.fixture.invalid',async getBlockHeight(){return 100},async getSlot(){return 222},async getBlockTime(){return now},async getFeeForMessage(){return {value:10000}},async getMinimumBalanceForRentExemption(){return 1259840},async getAccountInfo(k){if(k.equals(config))return {owner:program,executable:false,data:cfg};if(k.equals(storageKey))return storage;if(k.equals(oracle))return {owner:program,executable:false,data:oldOracle};throw Error('unexpected_account')}};
  const readAccount=async (_c,_k,decoder)=>decoder===sdk.deserializeConfigAccount?settings:{mint};
  return {build,tx,connection,readAccount,before,after,intent:{operation:'open',owner:owner.toBase58(),asset:'BTC',side:'long',margin:'5000000',leverage:1000}};
}

test('current open checks complete exact-message HTTP simulation including newer oracle', async () => {
  const f=await setup(), savedFetch=globalThis.fetch, savedNow=Date.now; let calls=[],pins=0;
  Date.now=()=>now*1000;
  globalThis.fetch=async (url,opts)=>{const body=JSON.parse(opts.body);calls.push(body.method);assert.equal(String(url),'https://rpc.fixture.invalid/');if(body.method==='getMultipleAccounts')return new Response(JSON.stringify({jsonrpc:'2.0',result:{context:{slot:222},value:f.before}}));assert.equal(body.method,'simulateTransaction');assert.equal(body.params[0],f.build.serializedTxBase64);assert.equal(body.params[1].sigVerify,false);assert.equal(body.params[1].replaceRecentBlockhash,false);assert.equal(body.params[1].minContextSlot,222);return new Response(JSON.stringify({jsonrpc:'2.0',result:{context:{slot:223},value:{err:null,accounts:f.after}}}));};
  try {
    const run=()=>verifyCurrentOpen(f.build,f.intent,{connection:f.connection,readAccount:f.readAccount,now},inspectOpenBuild,async()=>{pins++});
    const result=await run(); assert.equal(result.simulatedEntryPrice,'65100000000000000');assert.equal(result.signedFeedPrice,'65000000000000000');assert.equal(result.verification,'current_observed_subset');assert.equal(pins,2);assert.deepEqual(calls,['getMultipleAccounts','simulateTransaction']);
    const markets={paused:false,minMargin:'5000000',fees:{closeFeePpm:20,winFeePpm:30000},markets:Object.entries(MARKETS).map(([symbol,address])=>({symbol,address,closed:false,closeOnly:false}))};
    const api=async path=>path==='markets'?markets:f.build;
    const ready=await serviceHandle({...f.intent,action:'service-build-open'},{connection:f.connection,readAccount:f.readAccount,now,api,checkPins:async()=>{}});
    assert.equal(ready.status,'ready');assert.equal(ready.checked.simulatedEntryPrice,'65100000000000000');assert.equal(ready.checked.verification,'current_observed_subset');
    f.after[2].data=[Buffer.from(f.after[2].data[0],'base64').fill(1,72,76).toString('base64'),'base64'];
    await assert.rejects(run(),/current_(token_authority_changed|unsafe_token_authority)/);
    globalThis.fetch=async()=>new Response('rate limited', { status: 429 });
    await assert.rejects(run(),/current_rpc_unavailable/);
    globalThis.fetch=async()=>new Response('{not json', { status: 200 });
    await assert.rejects(run(),/current_invalid_rpc_response/);
  } finally { globalThis.fetch=savedFetch;Date.now=savedNow; }
});
