import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { requester } from '../scripts/smoke_request.mjs';

function deferred() { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; }
function client() {
  const listeners = {};
  const nodes = new Map();
  const element = () => ({ textContent: '', close() {}, reset() {}, setAttribute() {}, querySelector: element });
  const get = selector => nodes.get(selector) ?? (nodes.set(selector, element()), nodes.get(selector));
  const document = { querySelector: get, querySelectorAll: () => [], addEventListener(name, callback) { listeners[name] = callback; } };
  const context = vm.createContext({ document, window: {}, location: { hash: '#backtest' }, FormData: class { constructor(form) { return Object.entries(form.values); } }, setTimeout, clearTimeout, AbortController, console, createAgentAccess: () => ({invalidate() {}, routeChanged() {}}) });
  const source = readFileSync(new URL('../public/app.js', import.meta.url), 'utf8');
  vm.runInContext(source.replace(/^import .*;\n/gm, '').split("$('#menu-button').addEventListener")[0], context);
  vm.runInContext('updateAccountUI = () => {}; render = () => {}; toast = () => {};', context);
  return { context, listeners, nodes, run: code => vm.runInContext(code, context) };
}

test('pending account response cannot restore a cleared or replaced session', async () => {
  const c = client(), pending = deferred();
  c.context.pending = pending.promise;
  c.run("api = async path => path === '/api/me' ? pending : {bots: []}; state.user = {id:'old',wallet:'old'}; state.accountStatus='ready';");
  const refresh = c.run('refreshAccount()');
  const button = { dataset: { action: 'logout' }, setAttribute() {} };
  await c.listeners.click({ target: { closest: selector => selector === '[data-action]' ? button : null } });
  pending.resolve({ user: { id: 'old', wallet: 'old' }, subscription: {} });
  await refresh;
  assert.equal(c.run('state.user'), null);
});

test('bot read failure retains same-account definitions and reports unavailable', async () => {
  const c = client();
  c.run("state.user={id:'same',wallet:'same'}; state.accountStatus='ready'; state.bots=[{id:'saved'}]; api=async path => {if(path==='/api/me')return {user:{id:'same',wallet:'same'}}; throw new Error('unavailable');};");
  assert.equal(await c.run('refreshAccount()'), true);
  assert.equal(c.run('state.bots[0].id'), 'saved');
  assert.equal(c.run('state.botsUnavailable'), true);
  c.run("api=async()=>{throw new Error('me unavailable');};");
  assert.equal(await c.run('refreshAccount()'), false);
  assert.equal(c.run('state.bots.length'), 0);
  c.run("api=async path => {if(path==='/api/me')return {user:{id:'same',wallet:'same'}}; throw new Error('unavailable');};");
  c.run("beginAccountTransition(); state.user={id:'different',wallet:'different'};");
  await c.run('refreshAccount()');
  assert.equal(c.run('state.bots.length'), 0);
});

test('old experiment response cannot overwrite a newer request or a returned view', async () => {
  const c = client(), first = deferred(), second = deferred();
  c.context.responses = [first.promise, second.promise];
  c.context.rendered = [];
  c.run("state.user={id:'same',wallet:'same'}; state.accountStatus='ready'; state.view='backtest'; api=path=>path==='/api/me' ? {user:state.user} : responses.shift(); renderBacktest=result=>rendered.push(result);");
  const form = () => ({ id: 'backtest-form', isConnected: true, values: { coin: 'SOL', strategy: 'buy_and_hold', capital: '10000' }, querySelector: () => ({ setAttribute() {} }) });
  const submit = form => { c.nodes.set('#backtest-form', form); return c.listeners.submit({ target: form, preventDefault() {} }); };
  const old = submit(form()), current = submit(form());
  second.resolve({ id: 'current' }); await current;
  first.resolve({ id: 'old' }); await old;
  assert.equal(c.context.rendered.length, 1);
  assert.equal(c.context.rendered[0].id, 'current');
  const late = deferred(); c.context.responses = [late.promise];
  const pending = submit(form());
  c.run("++state.navigationEpoch; state.view='backtest';");
  late.resolve({ id: 'away-and-back' }); await pending;
  assert.equal(c.context.rendered.length, 1);
});

test('smoke request bounds both transport and body under one deadline', async () => {
  for (const bodyStalls of [false, true]) {
    let signal;
    const request = requester('https://synthetic.invalid', { timeoutMs: 5, fetchImpl: async (url, init) => {
      signal = init.signal;
      if (!bodyStalls) return new Promise(() => {});
      return { text: () => new Promise(() => {}), status: 200, headers: new Headers() };
    } });
    await assert.rejects(request('/fixture'), /deadline exceeded/);
    assert.equal(signal.aborted, true);
  }
});
