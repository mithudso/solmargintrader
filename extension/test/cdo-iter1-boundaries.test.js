import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { request } from '../src/jupiter/http.js';
import { checkForUpdate, BUILD_STATE_KEY } from '../src/core/autoreload.js';
import { createRequestHandler } from '../tools/api-server.js';
import { fakeHandle } from '../e2e/fixtures/fake-soltui-registry.js';
import { importSource } from './helpers/import-source.js';
test('CDO-a8597af751 server Retry-After longer than local wait bound refuses instead of retrying early', async () => {
  let reads = 0; const delays = [];
  await assert.rejects(request({url:'https://fixture.invalid/read', maxAttempts:2, log() {}, fetchImpl:async () => { reads++; return {ok:false,status:429,headers:{get:()=> '120'},text:async()=>''}; }, sleepImpl:async ms=>delays.push(ms)}));
  assert.equal(reads, 1); assert.deepEqual(delays, []);
});
test('CDO-866a2685c7 metadata failure preserves the pending reload identity for retry', async () => {
  let saved = {hash:'1'.repeat(64)}, reloads = 0;
  await assert.rejects(checkForUpdate({deps:{soltui:{request:async request=>fakeHandle(request,{hash:'2'.repeat(64)})}},
    state:{get:async()=>saved,set:async (_key,v)=>{saved=v;}}, pending:()=>0, withLock:fn=>fn(),
    reload(){reloads++;}, logEvent:async()=>{}, describe:async()=>{throw new Error('synthetic metadata failure');}, hold:async()=>{}}));
  assert.equal(saved.hash, '1'.repeat(64)); assert.equal(reloads,0);
});
test('CDO-bf1ec832fe oversized synthetic request returns 413 without destroying the response socket', async () => {
  const req = new EventEmitter(); Object.assign(req,{url:'/v1/setConfig',method:'POST',headers:{authorization:'Bearer fixture'}});
  let destroyed = false, payload, status; req.destroy=()=>{destroyed=true;}; req.resume=()=>{};
  const res = {writeHead(code){status=code;},end(body){payload=JSON.parse(body);}};
  const task=createRequestHandler({deps:{},token:'fixture'})(req,res); req.emit('data',Buffer.alloc(256*1024+1)); await task;
  assert.equal(status,413); assert.equal(payload.ok,false); assert.equal(destroyed,false);
});
for (const [id, file, tail, args] of [
  ['CDO-169ad4a348','tools/control-room-e2e.mjs','const report =',[ 'pass' ]],
  ['CDO-80e84a2773','tools/bot-manager-e2e.mjs','const report =',[ '/fixture/home', 'pass' ]],
]) test(`${id} malformed child output rejects through the owned helper promise`, async()=>{
  let callback; globalThis.__jsonFixture = {fs:{realpathSync:p=>p,mkdtempSync:()=>'/fixture',mkdirSync(){},writeFileSync(){}},execFile:(_a,_b,_c,cb)=>{callback=cb;}};
  try {
    const {python}=await importSource(file,{replace:[["import fs from 'node:fs';",'const fs=globalThis.__jsonFixture.fs;'],["import { execFile } from 'node:child_process';",'const execFile=globalThis.__jsonFixture.execFile;']],tail,append:'export {python};'});
    const pending=python(...args); let threw;
    try {callback(null,'not JSON','');} catch(error){threw=error;}
    assert.equal(threw,undefined,'callback exception escaped its Promise'); await assert.rejects(pending,/JSON|output|helper/i);
  }finally{delete globalThis.__jsonFixture;}
});
test('CDO-79434217f6 explicit economics gate rejects a zero-trip successful synthetic engine', async()=>{
  const {main}=await importSource('tools/dryrun.js',{replace:[['const args = parseArgs(process.argv.slice(2));',"const args = {offline:100,ticks:1,'assert-economics':true};"],["import { tick } from '../src/core/engine.js';",'const tick=async()=>({price:100,placed:[],rejected:[],errors:[],skipped:[]});']],tail:'main().catch',append:'export {main};'});
  const log=console.log; console.log=()=>{};
  try {await assert.rejects(main(),/positive closed round trip/);}finally{console.log=log;}
});
