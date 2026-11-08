import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { isSolanaPubkey, fetchSolanaAddress, mountWalletPubkeyButton } from '../src/ui/wallet-pubkey.js';
import { runCommand } from '../src/core/commands.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
// Public addresses only. The first is the owner's published Solana address from CLAUDE.md.
const SOL = 'EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV';
const EVM = '0x901a89cEC0608eB5435A915f006b45bD46405314';

const envelope = (result, ok = true, error = null) => ({ ok, command: 'wallet.addresses', result: ok ? result : null, error });

/** A fake host transport plus a `send` that goes through the REAL registry, as the service worker does. */
function bridge(answer) {
  const requests = [];
  const soltui = {
    async request(request) {
      requests.push(request);
      return typeof answer === 'function' ? answer(request) : answer;
    },
  };
  const deps = { soltui, store: new MemoryStore(), configStore: new ConfigStore(null), clock: () => 1 };
  const send = async (msg) => {
    try {
      return { ok: true, result: await runCommand({ name: msg.type, args: { command: msg.command, params: msg.params }, deps }) };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  };
  return { send, requests };
}

test('isSolanaPubkey accepts a 32-byte Base58 key and refuses everything else', () => {
  assert.equal(isSolanaPubkey(SOL), true);
  assert.equal(isSolanaPubkey('11111111111111111111111111111111'), true);
  for (const bad of ['', 'nope', EVM, SOL + 'x', `${SOL.slice(0, 40)}0OIl`, null, 5, '1'.repeat(33)]) {
    assert.equal(isSolanaPubkey(bad), false, String(bad));
  }
});

test('the address comes from the read-only wallet.addresses command through soltuiCall', async () => {
  const { send, requests } = bridge(envelope({ solana_address: SOL, base_address: EVM, eth_address: '', note: 'x' }));
  const out = await fetchSolanaAddress(send);
  assert.deepEqual(out, { ok: true, address: SOL });
  // soltuiCall first asks the host for the command's flags; the one real call is wallet.addresses.
  assert.deepEqual(requests.filter((r) => r.op === 'call'), [{ op: 'call', command: 'wallet.addresses', params: {} }]);
  assert.ok(requests.every((r) => r.op === 'list' || r.command === 'wallet.addresses'));
});

test('an invalid, missing or unreachable address fills nothing and says why', async () => {
  const cases = [
    [envelope({ solana_address: 'not-a-key' }), /not a valid Solana public key/],
    [envelope({ solana_address: '' }), /no Solana address saved/],
    [envelope({}), /no Solana address saved/],
    [envelope(null, false, { code: 'failed', message: 'host is down' }), /host is down/],
  ];
  for (const [answer, pattern] of cases) {
    const out = await fetchSolanaAddress(bridge(answer).send);
    assert.equal(out.ok, false);
    assert.match(out.message, pattern);
  }
  const out = await fetchSolanaAddress(async () => { throw new Error('port closed'); });
  assert.match(out.message, /port closed/);
});

test('an xpub or key in the reply is never used: only solana_address is read', async () => {
  const sneaky = envelope({ solana_address: '', btc_xpub: 'xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB' });
  const out = await fetchSolanaAddress(bridge(sneaky).send);
  assert.equal(out.ok, false);
});

/* A tiny DOM: just what mountWalletPubkeyButton touches. */
function fakeRoot() {
  const listeners = {};
  const button = { disabled: false, addEventListener: (ev, fn) => { listeners[ev] = fn; } };
  const field = { value: '', events: [], dispatchEvent(e) { this.events.push(e.type); } };
  const status = { textContent: '' };
  const map = { '#useSoltuiAddress': button, '#configForm [name="userPubkey"]': field, '#useSoltuiStatus': status };
  return { root: { querySelector: (sel) => map[sel] ?? null }, click: () => listeners.click(), button, field, status };
}

test('clicking the button fills the field and leaves saving to the owner', async () => {
  const ui = fakeRoot();
  const stores = [];
  globalThis.chrome = { storage: { local: { set: (...a) => stores.push(a) }, sync: { set: (...a) => stores.push(a) } } };
  try {
    const { send } = bridge(envelope({ solana_address: SOL, base_address: EVM, eth_address: '' }));
    mountWalletPubkeyButton(ui.root, send);
    await ui.click();
    assert.equal(ui.field.value, SOL);
    assert.match(ui.status.textContent, /Click Save/);
    assert.equal(ui.button.disabled, false);
    assert.deepEqual(stores, [], 'nothing is written to chrome.storage by this page');
  } finally {
    delete globalThis.chrome;
  }
});

test('a refused address leaves the field alone', async () => {
  const ui = fakeRoot();
  ui.field.value = 'existing';
  mountWalletPubkeyButton(ui.root, bridge(envelope({ solana_address: 'bad' })).send);
  await ui.click();
  assert.equal(ui.field.value, 'existing');
  assert.match(ui.status.textContent, /not a valid Solana public key/);
});

test('the dashboard has the button, loads the module, and the module uses textContent only', async () => {
  const html = await readFile(join(ROOT, 'src', 'ui', 'dashboard.html'), 'utf8');
  assert.match(html, /name="userPubkey"/);
  assert.match(html, /id="useSoltuiAddress"[^>]*>Use soltui Solana address</);
  assert.match(html, /id="useSoltuiStatus"/);
  const dashboard = await readFile(join(ROOT, 'src', 'ui', 'dashboard.js'), 'utf8');
  assert.match(dashboard, /mountWalletPubkeyButton\(document, send\)/);
  const source = await readFile(join(ROOT, 'src', 'ui', 'wallet-pubkey.js'), 'utf8');
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(/.test(code));
  assert.ok(!/chrome\.storage|\.storage\./.test(code), 'must not write chrome.storage');
  assert.ok(!/wallet\.private|solana\.private|xpub/i.test(code.replace(/the extension|never an extended/g, '')), 'no key material handling');
});

test('the manifest and package agree on the version (0.3.1, the Lightweight Charts equity chart)', async () => {
  const manifest = JSON.parse(await readFile(join(ROOT, 'manifest.json'), 'utf8'));
  const pkg = JSON.parse(await readFile(join(ROOT, 'package.json'), 'utf8'));
  assert.equal(manifest.version, '0.3.1');
  assert.equal(pkg.version, manifest.version);
});
