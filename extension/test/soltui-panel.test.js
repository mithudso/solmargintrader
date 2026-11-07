import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { coerceField, buildParams, commandNames } from '../src/ui/soltui-panel.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

test('coerceField converts by declared type and skips empty optional fields', () => {
  assert.deepEqual(coerceField({ name: 'n', type: 'number' }, ' 2.5 '), { value: 2.5 });
  assert.deepEqual(coerceField({ name: 's', type: 'string' }, ' hi '), { value: 'hi' });
  assert.deepEqual(coerceField({ name: 'j', type: 'json' }, '{"a":[1]}'), { value: { a: [1] } });
  assert.deepEqual(coerceField({ name: 'b', type: 'bool' }, true), { value: true });
  assert.deepEqual(coerceField({ name: 'b', type: 'bool' }, false), { skip: true });
  assert.deepEqual(coerceField({ name: 's', type: 'string' }, ''), { skip: true });
  assert.deepEqual(coerceField({ name: 's', type: 'string', required: true }, '  '), { error: 's is required' });
  assert.match(coerceField({ name: 'n', type: 'number' }, 'abc').error, /must be a number/);
  assert.match(coerceField({ name: 'n', type: 'number' }, 'Infinity').error, /must be a number/);
  assert.match(coerceField({ name: 'j', type: 'json' }, '{bad').error, /valid JSON/);
});

test('buildParams collects params and reports every problem', () => {
  const command = { params: [{ name: 'a', type: 'string', required: true }, { name: 'n', type: 'number' }, { name: 'j', type: 'json' }] };
  assert.deepEqual(buildParams(command, { a: 'x', n: '3', j: '' }), { params: { a: 'x', n: 3 }, errors: [] });
  assert.deepEqual(buildParams(command, { a: '', n: 'q', j: '{' }).errors.length, 3);
});

test('confirm is sent only when the box was ticked, and a declared confirm field cannot bypass it', () => {
  const command = { params: [{ name: 'confirm', type: 'bool' }] };
  assert.deepEqual(buildParams(command, { confirm: true }).params, {}, 'a stray confirm value is ignored');
  assert.deepEqual(buildParams(command, {}, { confirmed: true }).params, { confirm: true });
  assert.deepEqual(buildParams(command, {}, { confirmed: false }).params, {});
  assert.deepEqual(buildParams(command, {}, { confirmed: 'yes' }).params, {}, 'only a real true counts');
});

test('only names from the listing are sendable', () => {
  const names = commandNames([{ name: 'a.b' }, { name: 'c.d' }]);
  assert.equal(names.has('a.b'), true);
  assert.equal(names.has('rm'), false);
  assert.equal(commandNames(undefined).size, 0);
});

test('the panel renders results with textContent only, never innerHTML', async () => {
  const source = await readFile(join(ROOT, 'src', 'ui', 'soltui-panel.js'), 'utf8');
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(/.test(source), 'KNOW-407: soltui output must never be parsed as markup');
  assert.match(source, /result\.textContent = /);
});

test('the dashboard loads the panel and has its mount points', async () => {
  const html = await readFile(join(ROOT, 'src', 'ui', 'dashboard.html'), 'utf8');
  for (const id of ['soltuiCommand', 'soltuiReload', 'soltuiStatus', 'soltuiDescribe', 'soltuiForm', 'soltuiResult']) {
    assert.match(html, new RegExp(`id="${id}"`), id);
  }
  const dashboard = await readFile(join(ROOT, 'src', 'ui', 'dashboard.js'), 'utf8');
  assert.match(dashboard, /mountSoltuiPanel/);
});

test('the manifest asks for exactly the permissions and hosts it uses, and widens nothing else', async () => {
  const manifest = JSON.parse(await readFile(join(ROOT, 'manifest.json'), 'utf8'));
  // notifications: the alert scan (src/bg/service-worker.js runAlertScan).
  assert.deepEqual(manifest.permissions, ['storage', 'alarms', 'nativeMessaging', 'notifications']);
  assert.deepEqual(manifest.host_permissions, [
    'https://api.jup.ag/*', 'https://lite-api.jup.ag/*', 'https://tx.jup.ag/*',
    // Read-only market data (src/market): Base and Solana JSON-RPC, DefiLlama prices and yields.
    'https://mainnet.base.org/*', 'https://base-rpc.publicnode.com/*', 'https://api.mainnet-beta.solana.com/*',
    'https://coins.llama.fi/*', 'https://yields.llama.fi/*',
  ]);
  assert.equal(manifest.content_security_policy.extension_pages, "script-src 'self'; object-src 'self'; base-uri 'none'");
  assert.equal(manifest.externally_connectable, undefined, 'no other page or extension may message this one');
  assert.equal(manifest.background.service_worker, 'src/bg/service-worker.js');
});

test('src/core stays free of chrome.* and node:* even with the soltui bridge', async () => {
  const files = ['soltui.js', 'autoreload.js', 'commands.js', 'engine.js', 'alerts.js'].map((f) => join('core', f))
    .concat(['net.js', 'evm.js', 'tokens.js', 'holdings.js', 'pools.js', 'quote.js'].map((f) => join('market', f)));
  for (const file of files) {
    const source = await readFile(join(ROOT, 'src', file), 'utf8');
    assert.ok(!/\bchrome\./.test(source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')), `${file} reaches chrome.*`);
    assert.ok(!/from 'node:/.test(source), `${file} imports node:*`);
  }
});
