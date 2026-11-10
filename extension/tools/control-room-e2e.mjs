#!/usr/bin/env node
/** Separate nontrading gate. Ordinary e2e still forbids server starts and tab creation. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import { launch, findChromeForTesting, sleep } from '../e2e/lib/cdp.mjs';
import { controlRoomUrl } from '../src/core/control-room.js';
import { assertSoltuiCallAllowed } from '../e2e/lib/guard.mjs';

const EXTENSION = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = path.dirname(EXTENSION);
const PYTHON = process.env.SOLBOT_TEST_PYTHON || path.join(os.homedir(), '.venvs/soltui/bin/python');
const INSTALLED = process.env.SOLBOT_TEST_INSTALLED === '1';
const ALLOWED = new Set(['controlRoomStatus', 'controlRoomStart', 'controlRoomOpen']);
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const shq = value => `'${String(value).replace(/'/g, `'\\''`)}'`;
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'solbot-control-room-'));
const manager = path.join(temporary, 'manager');
const ecosystem = path.join(temporary, 'ecosystem');
const consoleHome = path.join(temporary, 'console');
fs.mkdirSync(path.join(consoleHome, 'forwardtest'), { recursive: true });
fs.writeFileSync(path.join(consoleHome, 'forwardtest/control.json'), '{"paused":true}', { mode: 0o600 });
const environment = { ...process.env, INDEX_NO_AUTO: '1', SOLBOT_HOME: manager,
  SOLBOT_ECOSYSTEM_HOME: ecosystem, SOLTUI_CONFIG_DIR: consoleHome };
if (INSTALLED) delete environment.PYTHONPATH;
else environment.PYTHONPATH = `${path.join(ROOT, 'botmanager/src')}:${ROOT}`;
const python = (code, args = [], timeout = 20000) => new Promise((resolve, reject) => {
  execFile(PYTHON, [...(INSTALLED ? ['-I'] : []), '-c', code, ...args], {
    cwd: INSTALLED ? os.tmpdir() : ROOT, env: environment, timeout,
  }, (error, output, stderr) => error ? reject(new Error(`isolated availability helper failed: ${stderr.slice(-2000)}`)) : resolve(JSON.parse(output)));
});
const report = { kind: 'isolated_real_chrome_control_room_availability', installed_runtime: INSTALLED,
  runtime_python: PYTHON, everyday_browser_changed: false, trading_armed: false, network: [], checks: {} };
let browser, started = false;
try {
  assert(INSTALLED, 'This gate requires SOLBOT_TEST_INSTALLED=1 and a compatible regular SOLBOT_TEST_PYTHON runtime');
  browser = await launch({ chrome: process.env.CHROME || findChromeForTesting(), extension: EXTENSION,
    noSandbox: process.env.E2E_NO_SANDBOX === '1' });
  report.browser = browser.version;
  report.extension_id = browser.extensionId;
  report.extension_version = JSON.parse(fs.readFileSync(path.join(EXTENSION, 'manifest.json'))).version;
  report.sources = ['src/core/control-room.js', 'src/ui/control-room.js', 'src/bg/service-worker.js'].map(file => ({
    file, sha256: createHash('sha256').update(fs.readFileSync(path.join(EXTENSION, file))).digest('hex'),
  }));
  const origin = `chrome-extension://${browser.extensionId}`;
  browser.on(message => {
    if (message.method !== 'Fetch.requestPaused') return;
    const { requestId, request } = message.params;
    const url = new URL(request.url);
    const localRead = url.protocol === 'http:' && url.hostname === '127.0.0.1' && request.method === 'GET';
    const packaged = url.protocol === 'chrome-extension:';
    if (!packaged) report.network.push({ method: request.method, origin: url.origin, path: url.pathname, allowed: localRead });
    browser.call(packaged || localRead ? 'Fetch.continueRequest' : 'Fetch.failRequest',
      packaged || localRead ? { requestId } : { requestId, errorReason: 'BlockedByClient' }, message.sessionId).catch(() => {});
  });
  const worker = await browser.waitFor(async () => (await browser.targets()).find(target => target.type === 'service_worker'
    && target.url === `${origin}/src/bg/service-worker.js`));
  assert(worker, 'Extension worker absent');
  const workerSession = await browser.attach(worker.targetId);
  await browser.call('Fetch.enable', { patterns: [{ urlPattern: '*' }] }, workerSession);
  const page = await browser.call('Target.createTarget', { url: 'about:blank' });
  const pageSession = await browser.attach(page.targetId);
  await browser.call('Fetch.enable', { patterns: [{ urlPattern: '*' }] }, pageSession);
  await browser.call('Page.navigate', { url: `${origin}/src/ui/popup.html` }, pageSession);
  assert(await browser.waitFor(() => browser.evaluate(pageSession, `!!document.getElementById('controlRoomRefresh')`)), 'Control-room card absent');
  const call = async type => {
    assert(ALLOWED.has(type), 'Availability gate refuses this registry operation');
    const reply = await browser.evaluate(pageSession, `chrome.runtime.sendMessage(${JSON.stringify({ type })})`);
    assert(reply?.ok, `Availability registry ${type} failed`);
    return reply.result;
  };
  const missing = await call('controlRoomStatus');
  assert(missing.helper === 'unavailable' && missing.state === 'unknown' && missing.ready === null,
    'Absent helper must report unknown health, never a healthy or failed server');
  assert(!fs.existsSync(manager) && !fs.existsSync(ecosystem), 'Read-only missing-helper status created owner homes');
  report.checks.helper_missing_unknown = true;
  const install = await python(`import json,sys\nfrom pathlib import Path\nfrom soltui.native_host_install import install\nprint(json.dumps(install(repo=Path(sys.argv[1]),python=Path(sys.executable),extra_ids=[sys.argv[2]],dirs=[Path(sys.argv[3])],wrapper=Path(sys.argv[4]),manager_home=Path(sys.argv[5]),ecosystem_home=Path(sys.argv[6]),isolated=${INSTALLED ? 'True' : 'False'})))`,
    [ROOT, browser.extensionId, path.join(browser.profile, 'NativeMessagingHosts'), path.join(browser.profile, 'control-room-host'), manager, ecosystem]);
  let wrapper = fs.readFileSync(install.wrapper, 'utf8');
  const localEnvironment = `export SOLTUI_CONFIG_DIR=${shq(consoleHome)}\n${INSTALLED ? '' : `export PYTHONPATH=${shq(environment.PYTHONPATH)}\n`}`;
  wrapper = wrapper.replace('#!/bin/sh\n', `#!/bin/sh\n${localEnvironment}`);
  fs.writeFileSync(install.wrapper, wrapper, { mode: 0o700 });
  const native = async request => {
    assert(['ping', 'buildHash'].includes(request.op), 'Availability gate refuses this direct native operation');
    const reply = await browser.evaluate(pageSession, `chrome.runtime.sendNativeMessage('com.mitchhudson.soltui',${JSON.stringify({ id: randomUUID(), ...request })})`);
    assert(reply?.response?.ok, `Installed legacy native ${request.op} probe failed`);
    return reply.response.result;
  };
  const ping = await native({ op: 'ping' });
  assert(ping.pong === true && ping.protocol === 1, 'Installed native ping protocol changed');
  const build = await native({ op: 'buildHash' });
  assert(/^[a-f0-9]{64}$/.test(build.hash) && build.root === EXTENSION, 'Installed native buildHash did not cover the actual loaded extension directory');
  const listingReply = await browser.evaluate(pageSession, `chrome.runtime.sendMessage({type:'soltuiCommands'})`);
  const listing = listingReply?.result?.result;
  assert(listingReply?.ok && listingReply.result.ok && Array.isArray(listing) && listing.length > 40, 'Installed native command help/list unavailable');
  for (const command of ['settings.get', 'prices.status']) {
    assertSoltuiCallAllowed(command, {}, listing);
    const reply = await browser.evaluate(pageSession, `chrome.runtime.sendMessage(${JSON.stringify({ type: 'soltuiCall', command, params: {} })})`);
    assert(reply?.ok && reply.result?.ok, `Installed headless native read ${command} unavailable`);
  }
  report.checks.legacy_ping_help_build_hash_status_calls = true;
  const down = await call('controlRoomStatus');
  assert(down.helper === 'available' && down.state === 'down' && down.ui_url === null,
    'Installed helper did not distinguish stopped servers from a missing helper');
  assert(!fs.existsSync(manager) && !fs.existsSync(ecosystem), 'Health initialized an absent owner home');
  report.checks.native_origin_authenticated = true;
  report.checks.servers_down_before_click = true;
  await browser.evaluate(pageSession, `document.getElementById('controlRoomRefresh').click()`);
  assert(await browser.waitFor(() => browser.evaluate(pageSession, `!document.getElementById('controlRoomStart').disabled`)), 'Start button did not enable after verified helper health');
  await browser.evaluate(pageSession, `document.getElementById('controlRoomStart').click()`);
  started = true;
  const healthy = await browser.waitFor(async () => {
    const snapshot = await call('controlRoomStatus');
    return snapshot.ui_url && snapshot.components?.find(item => item.name === 'control_room')?.state === 'up' ? snapshot : null;
  }, 60000, 500);
  assert(healthy && controlRoomUrl(healthy.ui_url) === healthy.ui_url, 'Explicit Start did not produce a verified loopback UI');
  report.checks.explicit_click_started_servers = true;
  report.initial_ui_url = healthy.ui_url;
  assert(await browser.waitFor(() => browser.evaluate(pageSession, `!document.getElementById('controlRoomOpen').disabled`), 30000), 'Open button remained disabled after startup');
  await browser.evaluate(pageSession, `document.getElementById('controlRoomOpen').click()`);
  const controlTarget = await browser.waitFor(async () => (await browser.targets()).find(target => target.type === 'page'
    && target.url.replace(/\/$/, '') === healthy.ui_url));
  assert(controlTarget, 'Actual popup did not open the helper-provided control-room URL');
  const controlSession = await browser.attach(controlTarget.targetId);
  await browser.call('Fetch.enable', { patterns: [{ urlPattern: '*' }] }, controlSession);
  const title = await browser.waitFor(() => browser.evaluate(controlSession, `document.title.includes('Bot control room') && document.title`));
  assert(title, 'Opened tab is not the actual Bot control room');
  const httpHealth = await browser.evaluate(controlSession, `fetch('/api/health').then(response => response.json())`);
  assert(httpHealth.data?.schema_version === 1 && Array.isArray(httpHealth.data.components) === false, 'Actual UI machine-health endpoint absent');
  report.checks.actual_ui_opened = true;
  report.checks.actual_ui_health_read = true;
  // The fault target comes from verified lock + nonce health in our temporary home.
  const killed = await python(`import json,os,signal,sys\nfrom ecosystem.ui_service import status\nstate=status(sys.argv[1])\nassert state['running'] and state['url']==sys.argv[2]\nos.kill(state['pid'],signal.SIGTERM)\nprint(json.dumps({'pid':state['pid'],'instance':state['instance']}))`, [ecosystem, healthy.ui_url]);
  const recovered = await browser.waitFor(async () => {
    const state = await python(`import json,sys\nfrom ecosystem.ui_service import status\nprint(json.dumps(status(sys.argv[1])))`, [ecosystem]);
    return state.running && state.pid !== killed.pid && state.instance !== killed.instance ? state : null;
  }, 60000, 500);
  assert(recovered, 'Managed suite did not recover the test-owned control-room process');
  const recoveredHealth = await call('controlRoomStatus');
  assert(recoveredHealth.ui_url === recovered.url && recoveredHealth.components.find(item => item.name === 'control_room')?.state === 'up',
    'Actual Chrome helper did not observe monitored UI recovery');
  report.checks.monitored_ui_restart_observed_by_chrome = true;
  const runtime = await browser.evaluate(workerSession, `chrome.storage.local.get(['runtime','config'])`);
  assert(runtime.runtime?.armed === false && runtime.config?.mode === 'dry-run', 'Server bringup changed trading safety defaults');
  report.checks.dry_run_disarmed_preserved = true;
  const offlineManifest = path.join(browser.profile, 'NativeMessagingHosts/com.mitchhudson.soltui.json');
  fs.renameSync(offlineManifest, `${offlineManifest}.offline`);
  const offline = await call('controlRoomStatus');
  assert(offline.helper === 'unavailable' && offline.state === 'unknown', 'Removing the helper registration did not restore unknown health');
  report.checks.offline_helper_unknown = true;
  fs.renameSync(`${offlineManifest}.offline`, offlineManifest);
  report.recovered_ui_url = recovered.url;
} finally {
  try {
    if (started) {
      await python(`import json\nfrom botmanager.suite import operation\nprint(json.dumps(operation('stop')))`, [], 30000);
      const stopped = await python(`import json\nfrom botmanager.machine_health import check\nprint(json.dumps(check()))`);
      assert(stopped.components.suite.state === 'down' && stopped.components.manager.state === 'down'
        && stopped.components.control_room.state === 'down', 'Test-owned suite left a component running');
      report.checks.test_owned_components_stopped = true;
    }
  } finally {
    if (browser) await browser.close();
    await sleep(100);
    fs.rmSync(temporary, { recursive: true, force: true });
  }
}
console.log(JSON.stringify(report, null, 2));
