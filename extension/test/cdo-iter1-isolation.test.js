import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { importSource, sourceText } from './helpers/import-source.js';
import { isolateTargets } from '../e2e/lib/isolation.mjs';

test('CDO-a9af9ac907 target interception exists before initial and replacement startup', async () => {
  const trace = []; let isolated, startupEscaped = false;
  const input = new EventEmitter(), output = new EventEmitter(), proc = new EventEmitter();
  proc.stdio = [null, null, null, input, output];
  output.setEncoding = () => {};
  proc.kill = () => { proc.emit('exit'); };
  const event = value => output.emit('data', JSON.stringify(value) + '\0');
  let autoAttach = false;
  input.write = raw => {
    const message = JSON.parse(raw.slice(0, -1)); trace.push(message);
    queueMicrotask(() => {
      if (message.method === 'Target.setAutoAttach' && !message.sessionId) autoAttach = true;
      if (message.method === 'Extensions.loadUnpacked') {
        if (!autoAttach) startupEscaped = true;
        else event({ method: 'Target.attachedToTarget', params: { sessionId: 'initial', targetInfo: { type: 'service_worker' } } });
      }
      event({ id: message.id, result: message.method === 'Browser.getVersion' ? { product: 'fixture' } : message.method === 'Extensions.loadUnpacked' ? { id: 'fixture' } : {} });
    });
  };
  globalThis.__cdpSpawn = () => proc;
  globalThis.__cdpFS = { existsSync: () => true, mkdtempSync: () => '/owned-fixture', rmSync() {} };
  try {
    const { launch } = await importSource('e2e/lib/cdp.mjs', { replace: [
      ["import { spawn } from 'node:child_process';", 'const spawn = globalThis.__cdpSpawn;'],
      ["import fs from 'node:fs';", 'const fs = globalThis.__cdpFS;'],
    ] });
    const browser = await launch({ chrome: '/fixture/chrome', extension: '/fixture/extension', beforeLoad: async api => { isolated = await isolateTargets(api); } });
    assert.equal(startupEscaped, false);
    assert.ok(isolated);
    await Promise.all(isolated.sessions.values());
    event({ method: 'Target.attachedToTarget', params: { sessionId: 'replacement', targetInfo: { type: 'service_worker' } } });
    event({ method: 'Target.attachedToTarget', params: { sessionId: 'page', targetInfo: { type: 'page' } } });
    await Promise.all(isolated.sessions.values());
    for (const sessionId of ['initial', 'replacement', 'page']) {
      const methods = trace.filter(x => x.sessionId === sessionId).map(x => x.method);
      assert.ok(methods.indexOf('Fetch.enable') < methods.indexOf('Runtime.runIfWaitingForDebugger'));
    }
    await browser.close();
  } finally { delete globalThis.__cdpSpawn; delete globalThis.__cdpFS; }
});

test('CDO-f6d08a1598 an observed unsafe installation aborts dependent dispatch', async () => {
  const source = await sourceText('tools/e2e.mjs');
  const marker = source.indexOf("await check('installs disarmed,");
  const prefix = source.lastIndexOf('  let installSafe', marker);
  const block = source.slice(prefix >= 0 ? prefix : marker, source.indexOf("  await check('onInstalled logged", marker));
  const execute = new Function('check', 'sw', 'popup', 'eq', 'send', `return (async () => { ${block}; await send('tick'); })()`);
  for (const stored of [{ config: { mode: 'full-auto' }, runtime: { armed: true, killSwitch: false } }, {},
    { config: { mode: 'dry-run' }, runtime: { armed: true, killSwitch: false } }]) {
    const sent = [];
    await assert.rejects(execute(async (_name, run) => { try { await run(); } catch {} }, { ev: async () => stored }, { ev: async () => 'dry-run' }, assert.deepEqual,
      async name => sent.push(name)));
    assert.deepEqual(sent, []);
  }
});

test('CDO-b9c31bc0e4 lost click acknowledgement still enters test-owned cleanup', async () => {
  const source=await sourceText('tools/control-room-e2e.mjs'), click="await browser.evaluate(pageSession, `document.getElementById('controlRoomStart').click()`);";
  const at=source.indexOf(click), before=source.lastIndexOf('  started = true;',at), start=before>=at-30?before:at;
  const block=source.slice(start,source.indexOf('  const healthy =',at));
  const execute=new Function('browser',`return (async()=>{let started=false,cleaned=false;const pageSession='fixture';try{${block}}catch{}finally{if(started)cleaned=true;}return cleaned;})()`);
  assert.equal(await execute({evaluate:async()=>{throw new Error('owned click acknowledgement lost');}}),true);
});
test('CDO-129039c193 paper gate refuses price failure and requires positive simulated placement', async()=>{
  const {assertPaperExecutionTick}=await import('../e2e/lib/guard.mjs');
  for(const tick of [{errors:[{error:'price failed'}],skipped:[]},{mode:'dry-run',price:100,errors:[],pnl:{},placed:[],skipped:[]}])assert.throws(()=>assertPaperExecutionTick(tick),/Paper tick/);
  assert.doesNotThrow(()=>assertPaperExecutionTick({mode:'dry-run',price:100,errors:[],pnl:{},placed:[{simulated:true}],skipped:[]}));
});
test('CDO-5af83efe38 forced real selection still requires a successful readiness probe',async()=>{
  const {installHost}=await import('../e2e/lib/soltui-host.mjs'); let calls=0;
  await assert.rejects(installHost({profile:'/fixture-never-created',extensionId:'fixture',mode:'real',probe:async()=>{calls++;return false;}}),/did not answer/);
  assert.equal(calls,1);
});
test('CDO-e072af742a screenshot artifacts use distinct private directories and exclusive files',async()=>{
  const fs=await import('node:fs/promises'),path=await import('node:path');const {saveScreenshot}=await import('../e2e/lib/signal-desk.mjs');
  const files=[];try{
    files.push(saveScreenshot(Buffer.from('fixture').toString('base64'),'light'),saveScreenshot(Buffer.from('other').toString('base64'),'light'));
    assert.notEqual(path.dirname(files[0]),path.dirname(files[1]));
    for(const file of files){assert.equal((await fs.stat(file)).mode&0o777,0o600);assert.equal((await fs.stat(path.dirname(file))).mode&0o777,0o700);}
  }finally{for(const file of files)await fs.rm(path.dirname(file),{recursive:true,force:true});}
});
