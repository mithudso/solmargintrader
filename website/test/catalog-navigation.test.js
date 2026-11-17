import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Exercise the production initializer with deferred public metadata, without a server.
test('catalog completion refreshes research after navigation during startup', async () => {
  const source = readFileSync(new URL('../public/app.js', import.meta.url), 'utf8');
  const initializer = source.slice(source.indexOf('async function initialize() {'), source.indexOf('\ninitialize();'));
  let resolveCatalog;
  const catalog = new Promise(resolve => { resolveCatalog = resolve; });
  const state = { accountEpoch: 0, navigationEpoch: 0, accountStatus: 'loading', accountTransition: false, view: 'overview', config: {}, articles: [], strategies: [] };
  const renders = [];
  const api = path => path === '/research/catalog.json' ? catalog : Promise.resolve(path === '/api/config' ? { coins: ['SOL'] } : { strategies: [] });
  const context = vm.createContext({ state, api, refreshAccount: async () => {}, render: () => renders.push({ view: state.view, count: state.articles.length }), populateSelects: () => {}, main: {}, loadOracle: () => {} });
  const promise = vm.runInContext(`${initializer}\ninitialize()`, context);
  state.view = 'research'; state.navigationEpoch++; context.render();
  resolveCatalog({ articles: [{ slug: 'note' }] });
  await promise;
  assert.deepEqual(renders.at(-1), { view: 'research', count: 1 });
});
