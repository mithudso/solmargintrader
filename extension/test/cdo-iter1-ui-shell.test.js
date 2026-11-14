import test from 'node:test';
import assert from 'node:assert/strict';
import { importSource } from './helpers/import-source.js';
async function shell() {
  return importSource('src/ui/dashboard.js', { replace: [
    ['observeSortableTables(document);', ''], ['mountLiveWorkspace();', ''], ['mountControlRoom();', ''],
    ["document.getElementById('version').textContent = `v${chrome.runtime.getManifest().version}`;", ''],
  ], tail: '/* ------------------------------------------------------------------ boot -- */', append: 'export { show, mountSettings, state, VIEWS };' });
}
function fixture() {
  const nodes = new Map();
  const node = id => { if (!nodes.has(id)) nodes.set(id, Object.assign(new EventTarget(), { textContent: '', value: '', elements: {}, replaceChildren() { this.textContent = ''; } })); return nodes.get(id); };
  globalThis.document = { querySelector: selector => node(selector), querySelectorAll: () => [] };
  globalThis.location = { hash: '#settings' };
  globalThis.chrome = { runtime: { sendMessage: async () => ({ ok: false, error: 'synthetic refusal' }) } };
  return node;
}
test('CDO-408d8eeb82 failed view remains retryable and concurrent visits share the pending load', async () => {
  fixture(); const { show, state, VIEWS } = await shell(); let calls = 0, release;
  const gate = new Promise(resolve => { release = resolve; });
  VIEWS.settings.load = async () => { calls++; await gate; throw new Error('fixture unavailable'); };
  const warning = console.warn; console.warn = () => {};
  try {
    const first = show(); const second = show(); release(); await Promise.all([first, second]);
    assert.equal(calls, 1); assert.equal(state.loaded.has('settings'), false);
    VIEWS.settings.load = async () => { calls++; }; await show(); assert.equal(calls, 2); assert.equal(state.loaded.has('settings'), true);
  } finally { console.warn = warning; }
});
test('CDO-c637d00cb1 saved wallet invalidates loaded holdings and their old rendered balances', async () => {
  const node = fixture(), { mountSettings, state } = await shell();
  node('#walletForm').elements = { baseAddress: {value:'fixture'}, solanaAddress: {value:''} };
  state.loaded.add('holdings'); state.holdings = { totalUsd: 999 };
  chrome.runtime.sendMessage = async m => ({ ok: true, result: m.type === 'overview' ? { prefs: {} } : {} });
  mountSettings(); const event = new Event('submit', { cancelable: true });
  node('#walletForm').dispatchEvent(event); for(let i=0;i<20;i++) await Promise.resolve();
  assert.equal(state.loaded.has('holdings'), false); assert.equal(state.holdings, null);
  assert.match(node('#holdingsKpis').textContent, /refresh|loading|address/i);
});
test('CDO-56bc76e738 rejected API-key save clears DOM secret and reports refusal', async () => {
  const node = fixture(), { mountSettings } = await shell(); mountSettings();
  const input = node('#keyForm input[name="apiKey"]'); input.value = 'synthetic-test-only';
  chrome.runtime.sendMessage = async () => { throw new Error('fixture transport'); };
  node('#keyForm').dispatchEvent(new Event('submit', { cancelable: true })); for(let i=0;i<20;i++) await Promise.resolve();
  assert.equal(input.value, ''); assert.match(node('#walletStatus').textContent, /not saved|failed/i);
});
