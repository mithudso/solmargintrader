import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Exercise the production initializer with deferred public metadata, without a server.
test('catalog completion refreshes research after navigation while account hydration is pending', async () => {
  const source = readFileSync(new URL('../public/app.js', import.meta.url), 'utf8');
  const initializer = source.slice(source.indexOf('async function loadResearchCatalog() {'), source.indexOf('\ninitialize();'));
  let resolveCatalog;
  const catalog = new Promise(resolve => { resolveCatalog = resolve; });
  let resolveAccount;
  const account = new Promise(resolve => { resolveAccount = resolve; });
  let catalogRendered;
  const rendered = new Promise(resolve => { catalogRendered = resolve; });
  const state = { accountEpoch: 0, navigationEpoch: 0, accountStatus: 'loading', accountTransition: false, view: 'overview', config: {}, articles: [], researchStatus: 'idle', strategies: [] };
  const renders = [];
  const api = path => path === '/research/catalog.json' ? catalog : Promise.resolve(path === '/api/config' ? { coins: ['SOL'] } : { strategies: [] });
  const render = () => {
    renders.push({ view: state.view, count: state.articles.length });
    if (state.view === 'research' && state.articles.length) catalogRendered();
  };
  const context = vm.createContext({ state, api, refreshAccount: () => account, render, populateSelects: () => {}, main: {}, loadOracle: () => {} });
  const promise = vm.runInContext(`${initializer}\ninitialize()`, context);
  state.view = 'research'; state.navigationEpoch++; context.render();
  resolveCatalog({ articles: [{ slug: 'note' }] });
  await rendered;
  assert.equal(state.researchStatus, 'ready');
  assert.deepEqual(renders.at(-1), { view: 'research', count: 1 });
  resolveAccount();
  await promise;
});
