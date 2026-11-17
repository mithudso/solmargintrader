import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { COMMANDS, runCommand } from '../src/core/commands.js';
import { controlRoomUrl, controlRoomSnapshot, openControlRoom, controlRoomTransitions, CONTROL_ROOM_ALERT_COOLDOWN_MS } from '../src/core/control-room.js';
import { controlRoomPresentation } from '../src/ui/control-room.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';

const response = ({ state = 'up', url = 'http://127.0.0.1:57927', overall = 'up', ready = true } = {}) => ({
  ok: true, command: 'suite', error: null,
  result: { schema_version: 1, capability: 'control-room-v1', status: { state, ui_url: url },
    health: { schema_version: 1, overall, ready, components: {
      suite: { state: 'up' }, manager: { state: 'up' }, control_room: { state: 'up' }, market_data: { state: 'unknown' },
    } } },
});
function fixture(answer = () => response()) {
  const calls = [], opened = [];
  return { calls, opened, deps: { store: new MemoryStore(), configStore: new ConfigStore(null),
    soltui: { async request(request, options) { calls.push({ request, options }); return answer(request); } },
    async openControlRoom(url) { opened.push(url); } } };
}

test('control-room URLs allow only the verified numeric IPv4 loopback origin', () => {
  assert.equal(controlRoomUrl('http://127.0.0.1:57927/'), 'http://127.0.0.1:57927');
  for (const url of ['https://127.0.0.1:57927', 'http://localhost:57927', 'http://127.0.0.1:0',
    'http://127.0.0.1:65536', 'http://127.0.0.1:057927', 'http://127.0.0.1:57927/path',
    'http://127.0.0.1:57927?x=1', 'http://127.0.0.1:57927#hash', 'http://user@127.0.0.1:57927',
    'javascript:alert(1)', '//127.0.0.1:57927', 'http://127.0.0.1:57927\n', {}, null]) {
    assert.equal(controlRoomUrl(url), null, String(url));
  }
});

test('status is inert, preserves unknown readiness and uses only the fixed native request', async () => {
  const f = fixture(() => response({ overall: 'degraded', ready: null }));
  const value = await runCommand({ name: 'controlRoomStatus', args: {}, deps: f.deps });
  assert.equal(value.state, 'degraded');
  assert.equal(value.ready, null);
  assert.equal(value.components.find(c => c.name === 'market_data').state, 'unknown');
  assert.deepEqual(f.calls.map(c => c.request), [{ op: 'suite', action: 'status' }]);
  assert.deepEqual(f.opened, []);
  assert.equal(COMMANDS.controlRoomStatus.readOnly, true);
});

test('missing helper, old helper, startup and server failure remain different states', async () => {
  const unavailable = fixture(() => { throw new Error('secret-canary'); });
  const missing = await controlRoomSnapshot(unavailable.deps);
  const old = await controlRoomSnapshot(fixture(() => ({ ok: false, command: 'suite', error: { code: 'unknown_command' }, result: null })).deps);
  const pending = await controlRoomSnapshot(fixture(() => response({ state: 'starting', overall: 'down', ready: false, url: null })).deps);
  const down = await controlRoomSnapshot(fixture(() => response({ overall: 'down', ready: false, url: null })).deps);
  assert.equal(missing.helper, 'unavailable'); assert.equal(missing.state, 'unknown'); assert.equal(missing.ready, null);
  assert.equal(old.helper, 'incompatible'); assert.equal(pending.state, 'starting'); assert.equal(down.state, 'down');
  assert.equal(new Set([missing, old, pending, down].map(s => controlRoomPresentation(s).title)).size, 4);
  assert.ok(!JSON.stringify(missing).includes('secret-canary'));
});

test('a suite controller failure keeps the answered helper available and health unknown', async () => {
  const f = fixture(() => ({ ok: false, command: 'suite', result: null,
    error: { code: 'suite_failed', message: 'managed suite request failed; inspect local solbot stack status' } }));
  const snapshot = await controlRoomSnapshot(f.deps, 'start');
  assert.equal(snapshot.helper, 'available'); assert.equal(snapshot.state, 'unknown'); assert.equal(snapshot.ready, null);
  assert.equal(snapshot.reason, 'suite_request_failed'); assert.equal(snapshot.ui_url, null);
  assert.equal(controlRoomPresentation(snapshot).title, 'Suite request failed');
  assert.match(controlRoomPresentation(snapshot).detail, /solbot stack status/);
  assert.deepEqual(controlRoomTransitions(snapshot, null, 1).alerts, []);
});

test('only explicit start/open requests can bring up servers and no path or execution fields are accepted', async () => {
  const f = fixture(request => response(request.action === 'status' ? { overall: 'down', ready: false, url: null } : {}));
  const opened = await openControlRoom(f.deps);
  assert.equal(opened.opened, true);
  assert.deepEqual(f.calls.map(c => c.request), [{ op: 'suite', action: 'status' }, { op: 'suite', action: 'start' }]);
  assert.deepEqual(f.opened, ['http://127.0.0.1:57927']);
  for (const name of ['controlRoomStatus', 'controlRoomStart', 'controlRoomOpen']) {
    for (const key of ['url', 'home', 'argv', 'command', 'env', 'confirm', 'armed']) {
      await assert.rejects(runCommand({ name, args: { [key]: 'secret-canary' }, deps: f.deps }), /unknown|unexpected/i);
    }
  }
});

test('a corrupt helper URL never opens and pending startup is not reported as healthy', async () => {
  for (const url of ['http://example.com:80', 'http://127.0.0.1:1234/?secret=canary']) {
    const f = fixture(() => response({ state: 'starting', url, overall: 'down', ready: false }));
    const snapshot = await openControlRoom(f.deps);
    assert.equal(snapshot.ui_url, null); assert.equal(snapshot.opened, false); assert.equal(snapshot.state, 'starting');
    assert.deepEqual(f.opened, []);
    assert.equal(f.calls.length, 1);
  }
});

test('popup and dashboard mount one shared safe control-room launcher without added permission', async () => {
  for (const page of ['popup', 'dashboard']) {
    const html = await readFile(new URL(`../src/ui/${page}.html`, import.meta.url), 'utf8');
    const script = await readFile(new URL(`../src/ui/${page}.js`, import.meta.url), 'utf8');
    assert.match(html, /id="controlRoom"/); assert.match(html, /control-room\.css/); assert.match(script, /mountControlRoom\(\)/);
  }
  const source = await readFile(new URL('../src/ui/control-room.js', import.meta.url), 'utf8');
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|eval\(/.test(source));
  const manifest = JSON.parse(await readFile(new URL('../manifest.json', import.meta.url), 'utf8'));
  assert.ok(!manifest.permissions.includes('tabs'));
  assert.ok(!manifest.host_permissions.some(value => value.includes('127.0.0.1')));
});

test('component alerts require a measured failure after up, deduplicate, recover, and respect cooldown', () => {
  const observed = state => ({ helper: 'available', components: [{ name: 'manager', state }] });
  let record = controlRoomTransitions(observed('down'), null, 1000);
  assert.deepEqual(record.alerts, [], 'an intentionally stopped fresh installation is quiet');
  record = controlRoomTransitions(observed('up'), record.state, 2000);
  record = controlRoomTransitions(observed('down'), record.state, 3000);
  assert.equal(record.alerts.length, 1); assert.match(record.alerts[0].title, /Bot Manager is down/);
  const unavailable = controlRoomTransitions({ helper: 'unavailable', components: [] }, record.state, 4000);
  assert.deepEqual(unavailable.alerts, []); assert.deepEqual(unavailable.state, record.state);
  record = controlRoomTransitions(observed('down'), record.state, 5000);
  assert.deepEqual(record.alerts, []);
  record = controlRoomTransitions(observed('up'), record.state, 6000);
  assert.equal(record.alerts.length, 1); assert.match(record.alerts[0].title, /recovered/);
  record = controlRoomTransitions(observed('down'), record.state, 7000);
  assert.deepEqual(record.alerts, [], 'rapid flapping does not flood notifications');
  record = controlRoomTransitions(observed('up'), record.state, CONTROL_ROOM_ALERT_COOLDOWN_MS + 7000);
  record = controlRoomTransitions(observed('degraded'), record.state, CONTROL_ROOM_ALERT_COOLDOWN_MS + 8000);
  assert.equal(record.alerts.length, 1);
});


test('malformed component records remain unknown without aborting availability or alerts', async () => {
  for (const components of [[null, 42, { name: 'suite', state: 'up' }], { suite: null, manager: 'up' }, 'bad']) {
    const answer = response(); answer.result.health.components = components;
    const value = await controlRoomSnapshot(fixture(() => answer).deps);
    assert.equal(value.helper, 'incompatible');
    assert.doesNotThrow(() => controlRoomTransitions(value, null, 1));
  }
  assert.deepEqual(controlRoomTransitions({ helper: 'available', components: [null] }, null, 1).alerts, []);
  assert.deepEqual(controlRoomTransitions({ helper: 'available', components: {} }, null, 1).alerts, []);
});
