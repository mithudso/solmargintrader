#!/usr/bin/env node
/** Separate paper-only acceptance gate. The ordinary e2e guard stays unchanged. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { launch, findChromeForTesting, sleep } from '../e2e/lib/cdp.mjs';

const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = path.dirname(EXT);
const PYTHON = process.env.SOLBOT_TEST_PYTHON || path.join(os.homedir(), '.venvs/soltui/bin/python');
const CHROME = process.env.CHROME || findChromeForTesting();
const HOST = 'com.mitchhudson.soltui';
const ALLOWED = new Set(['browserManagerPoll', 'browserManagerSnapshot', 'tick']);
const shq = v => `'${String(v).replace(/'/g, `'\\''`)}'`;
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const python = (home, code, args = []) => new Promise((resolve, reject) => {
  execFile(PYTHON, ['-c', code, home, ...args], { cwd: ROOT, env: { ...process.env,
    PYTHONPATH: `${path.join(ROOT, 'botmanager/src')}:${ROOT}`, SOLBOT_HOME: home }, timeout: 10000 },
  (error, out, err) => error ? reject(new Error(`isolated manager call failed: ${err}`)) : resolve(JSON.parse(out)));
});

const report = { kind: 'isolated_real_chrome_paper_browser_owner', browser: null, profiles: [],
  everyday_browser_updated: false, live_execution_verified: false };
const browsers = [];
const testHome = fs.mkdtempSync(path.join(os.tmpdir(), 'solbot-browser-gate-'));
try {
  assert(CHROME && fs.existsSync(CHROME), 'Chrome for Testing is unavailable');
  assert(fs.existsSync(PYTHON), 'Existing test Python is unavailable');
  const identities = [];
  for (let profileNumber = 0; profileNumber < 2; profileNumber++) {
    const browser = await launch({ chrome: CHROME, extension: EXT, noSandbox: process.env.E2E_NO_SANDBOX === '1' });
    browsers.push(browser);
    report.browser = browser.version;
    const home = path.join(testHome, `manager-${profileNumber}`);
    const nativeDir = path.join(browser.profile, 'NativeMessagingHosts');
    fs.mkdirSync(nativeDir, { recursive: true });
    const configDir = path.join(browser.profile, 'soltui-config');
    fs.mkdirSync(path.join(configDir, 'forwardtest'), { recursive: true });
    fs.writeFileSync(path.join(configDir, 'forwardtest/control.json'), '{"paused":true}', { mode: 0o600 });
    const wrapper = path.join(browser.profile, 'browser-owner-host');
    fs.writeFileSync(wrapper, `#!/bin/sh\nexport PYTHONPATH=${shq(`${path.join(ROOT, 'botmanager/src')}:${ROOT}`)}\nexport SOLBOT_HOME=${shq(home)}\nexport SOLTUI_CONFIG_DIR=${shq(configDir)}\nexport SOLTUI_EXTRA_EXTENSION_IDS=${shq(browser.extensionId)}\ncd ${shq(ROOT)} || exit 1\nexec ${shq(PYTHON)} -m soltui.native_host "$@"\n`, { mode: 0o700 });
    const manifestPath = path.join(nativeDir, `${HOST}.json`);
    fs.writeFileSync(manifestPath, JSON.stringify({ name: HOST, description: 'test-owned paper browser owner',
      path: wrapper, type: 'stdio', allowed_origins: [`chrome-extension://${browser.extensionId}/`] }));
    const origin = `chrome-extension://${browser.extensionId}`;
    const target = await browser.waitFor(async () => (await browser.targets()).find(t => t.type === 'service_worker' && t.url === `${origin}/src/bg/service-worker.js`));
    assert(target, 'Actual extension service worker is absent');
    let session = await browser.attach(target.targetId);
    await browser.waitFor(() => browser.evaluate(session, `typeof chrome !== 'undefined' && !!chrome.runtime?.id`).catch(() => false));
    const network = [];
    browser.on(message => {
      if (message.method !== 'Fetch.requestPaused') return;
      const { requestId, request } = message.params;
      if (request.url.startsWith('chrome-extension:')) {
        browser.call('Fetch.continueRequest', { requestId }, message.sessionId).catch(() => {}); return;
      }
      network.push({ method: request.method, url: request.url.split('?')[0] });
      const url = new URL(request.url);
      const price = request.method === 'GET' && url.hostname === 'lite-api.jup.ag' && url.pathname === '/price/v3';
      const body = { So11111111111111111111111111111111111111112: { usdPrice: 75, decimals: 9 },
        EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v: { usdPrice: 1, decimals: 6 } };
      browser.call(price ? 'Fetch.fulfillRequest' : 'Fetch.failRequest', price ? { requestId, responseCode: 200,
        responseHeaders: [{ name: 'content-type', value: 'application/json' }, { name: 'access-control-allow-origin', value: '*' }],
        body: Buffer.from(JSON.stringify(body)).toString('base64') } : { requestId, errorReason: 'BlockedByClient' }, message.sessionId).catch(() => {});
    });
    await browser.call('Fetch.enable', { patterns: [{ urlPattern: '*' }] }, session);
    const pageTarget = await browser.call('Target.createTarget', { url: `${origin}/src/ui/popup.html` });
    let pageSession = await browser.attach(pageTarget.targetId);
    await browser.waitFor(() => browser.evaluate(pageSession, `typeof chrome !== 'undefined' && !!chrome.runtime?.sendMessage`).catch(() => false));
    const call = async (type, args = {}) => {
      assert(ALLOWED.has(type), 'Paper gate refuses this registry operation');
      const value = await browser.evaluate(pageSession, `chrome.runtime.sendMessage(${JSON.stringify({ type, ...args })})`);
      assert(value.ok, `Registry ${type} failed: ${value.error}`);
      return value.result;
    };
    await call('browserManagerPoll');
    const first = (await call('browserManagerSnapshot')).snapshot;
    identities.push(first.installation_id);
    assert(first.mode === 'dry-run' && first.armed === false && first.running === false, 'Fresh profile must stay disarmed and stopped');
    const sourceFiles = ['src/bg/service-worker.js', 'src/core/commands.js', 'src/core/bot-manager.js'];
    for (const file of sourceFiles) {
      const loaded = await browser.evaluate(session, `fetch(chrome.runtime.getURL(${JSON.stringify(file)})).then(r=>r.text())`);
      assert(loaded === fs.readFileSync(path.join(EXT, file), 'utf8'), `Loaded source differs: ${file}`);
    }
    const diskVersion = JSON.parse(fs.readFileSync(path.join(EXT, 'manifest.json'))).version;
    assert(first.extension_version === diskVersion, 'Loaded extension version differs from source');
    const queue = operation => python(home, `import json,sys\nfrom uuid import uuid4\nfrom botmanager.adapters.extension import BrowserStore\ns=BrowserStore(sys.argv[1]);o=s.discover()[0]['snapshot'];print(json.dumps(s.control(o['installation_id'],sys.argv[2],str(uuid4()),expected_generation=o['generation'],expected_config_hash=o['config_hash'])))`, [operation]);
    const getReceipt = id => python(home, `import json,sys\nfrom botmanager.adapters.extension import BrowserStore\nprint(json.dumps(BrowserStore(sys.argv[1]).receipt(sys.argv[2])))`, [id]);
    const pending = await queue('start');
    assert(pending.outcome === 'pending', 'Manager must write ahead before owner delivery');
    await call('browserManagerPoll');
    await call('browserManagerPoll');
    const start = await getReceipt(pending.request_id);
    assert(start.outcome === 'acknowledged', 'Real browser did not acknowledge delegated start');
    const running = (await call('browserManagerSnapshot')).snapshot;
    assert(running.running && !running.armed && running.runtime_id, 'Paper slot did not start independently of live arming');
    const tick = await call('tick');
    assert(!tick.skipped?.some(s => s.reason === 'not-armed'), 'Canonical paper tick did not receive its paper grant');
    const stopped = await queue('stop');
    await call('browserManagerPoll');
    await call('browserManagerPoll');
    const stop = await getReceipt(stopped.request_id);
    assert(stop.outcome === 'acknowledged', 'Real browser did not acknowledge delegated stop');
    const storage = await browser.evaluate(session, `chrome.storage.local.get(['browserManager','runtime'])`);
    assert(storage.browserManager.running === false && storage.runtime.armed === false, 'Actual Chrome storage did not preserve stopped/disarmed state');
    const registration = await python(home, `import json,sys\nfrom botmanager.adapters.extension import BrowserStore\nprint(json.dumps(BrowserStore(sys.argv[1]).discover()))`);
    assert(registration[0].native_origin.replace(/\/$/, '') === origin, 'Host did not verify actual native caller origin');
    fs.renameSync(manifestPath, `${manifestPath}.offline`);
    const offline = await browser.evaluate(pageSession, `chrome.runtime.sendMessage({type:'browserManagerPoll'})`);
    assert(offline.ok === false, 'Absent native host must report failure');
    assert((await call('browserManagerSnapshot')).snapshot.installation_id === first.installation_id, 'Offline handling changed installation identity');
    fs.renameSync(`${manifestPath}.offline`, manifestPath);
    await call('browserManagerPoll');
    // Evict the actual MV3 worker while keeping this throwaway profile and
    // extension page. The next runtime message must wake a new worker.
    await browser.call('ServiceWorker.enable', {}, pageSession);
    await browser.call('ServiceWorker.stopAllWorkers', {}, pageSession);
    await sleep(300);
    const wake = await browser.evaluate(pageSession, `chrome.runtime.sendMessage({type:'browserManagerSnapshot'})`);
    assert(wake.ok && wake.result.snapshot.installation_id === first.installation_id, 'Worker eviction replaced persisted installation UUID');
    const restarted = await browser.waitFor(async () => (await browser.targets()).find(t => t.type === 'service_worker' && t.url === `${origin}/src/bg/service-worker.js`));
    assert(restarted, 'Restarted MV3 service worker did not appear');
    session = await browser.attach(restarted.targetId);
    assert((await call('browserManagerSnapshot')).snapshot.installation_id === first.installation_id, 'Service-worker restart replaced persisted installation UUID');
    report.profiles.push({ installation_id: first.installation_id, extension_id: browser.extensionId,
      extension_version: diskVersion, loaded_source_hash: first.source_hash,
      loaded_source_files: sourceFiles.map(file => ({ file, sha256: createHash('sha256').update(fs.readFileSync(path.join(EXT, file))).digest('hex') })),
      actual_native_origin: registration[0].native_origin, start, stop, actual_storage_disarmed: true,
      restart_identity_preserved: true, offline_native_failure_observed: true,
      canonical_paper_tick: { placed: tick.placed?.length ?? 0, errors: tick.errors ?? [] }, network });
    await browser.close(); browsers.splice(browsers.indexOf(browser), 1);
  }
  assert(identities[0] !== identities[1], 'Separate actual browser profiles reused an installation UUID');
  console.log(JSON.stringify(report, null, 2));
} finally {
  for (const browser of browsers) await browser.close();
  fs.rmSync(testHome, { recursive: true, force: true });
}
