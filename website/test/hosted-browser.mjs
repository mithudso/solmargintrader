/** Real Chrome UI regressions with local APIs and synthetic signing keys.
 * No Stripe, Coinbase, RPC, or external wallet traffic is permitted. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { base58Encode } from '../../extension/src/wallet/solana.js';
import { importSigningKey } from '../execution/coinbase.js';

const root = new URL('../public/', import.meta.url);
const types = { js: 'text/javascript', html: 'text/html', css: 'text/css', svg: 'image/svg+xml', json: 'application/json' };
const plans = [
  { id: 'starter', name: 'Starter', monthlyUsd: 9.99, botLimit: 3, backtestsPerDay: 10 },
  { id: 'advanced', name: 'Advanced', monthlyUsd: 29.99, botLimit: 10, backtestsPerDay: null },
  { id: 'unlimited', name: 'Unlimited', monthlyUsd: 49.99, botLimit: null, backtestsPerDay: null },
];
const time = () => Math.floor(Date.now() / 1000);
const revision = 'a'.repeat(64);
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const wallets = await Promise.all([0, 1].map(async () => {
  const keys = await crypto.subtle.generateKey('Ed25519', true, ['sign', 'verify']);
  return { keys, user: { id: crypto.randomUUID(), wallet: base58Encode(new Uint8Array(await crypto.subtle.exportKey('raw', keys.publicKey))) }, pkcs8: Buffer.from(await crypto.subtle.exportKey('pkcs8', keys.privateKey)).toString('base64') };
}));
const coinbaseKeys = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
const coinbaseKeyBody = Buffer.from(await crypto.subtle.exportKey('pkcs8', coinbaseKeys.privateKey)).toString('base64');
const coinbaseKeyName = 'organizations/synthetic-org/apiKeys/synthetic-key';
const coinbasePem = `-----BEGIN PRIVATE KEY-----\n${coinbaseKeyBody.match(/.{1,64}/g).join('\n')}\n-----END PRIVATE KEY-----`;
const normalizedCoinbasePem = `-----BEGIN PRIVATE KEY-----\n${coinbaseKeyBody}\n-----END PRIVATE KEY-----`;
const short = value => `${value.slice(0, 4)}…${value.slice(-4)}`;
const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  try {
    const path = new URL(pathname === '/' ? 'index.html' : `.${pathname}`, root);
    assert.ok(fileURLToPath(path).startsWith(fileURLToPath(root)));
    response.writeHead(200, { 'Content-Type': types[pathname.split('.').pop()] || 'text/html' }); response.end(await readFile(path));
  } catch { response.writeHead(404); response.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
const groups = [];
async function fixture() {
  const context = await browser.newContext({ serviceWorkers: 'block' }); const page = await context.newPage();
  page.setDefaultTimeout(6000);
  const f = { context, page, owner: 0, requests: [], diagnostics: [], errors: [], blocked: [], onApi: null, onResource: null, jobs: [], releases: [], oracle: deferred(), configured: false };
  f.bot = { id: crypto.randomUUID(), name: 'Synthetic SOL strategy', coin: 'SOL', strategy: 'rsi', venue: 'coinbase', leverage: 1, budget: 10, mode: 'paper', status: 'configured' };
  f.connection = { id: crypto.randomUUID(), venue: 'coinbase', portfolioId: crypto.randomUUID(), status: 'verified' };
  f.challenges = new Map(); f.operations = [];
  const json = (route, value, status = 200) => route.fulfill({ status, json: value });
  page.on('pageerror', error => f.errors.push(error.message));
  page.on('console', message => f.diagnostics.push(message.text()));
  await page.addInitScript(values => {
    window.syntheticWalletIndex = 0; window.syntheticSignatures = []; window.holdSyntheticSignature = false;
    const provider = {
      get publicKey() { return { toString: () => values[window.syntheticWalletIndex].wallet }; },
      async connect() { return { publicKey: this.publicKey }; },
      async signMessage(bytes) {
        const chosen = values[window.syntheticWalletIndex]; const message = new Uint8Array(bytes);
        window.syntheticSignatures.push(new TextDecoder().decode(message));
        if (window.holdSyntheticSignature) await new Promise(resolve => { window.releaseSyntheticSignature = resolve; });
        const key = await crypto.subtle.importKey('pkcs8', Uint8Array.from(atob(chosen.pkcs8), char => char.charCodeAt(0)), 'Ed25519', false, ['sign']);
        return { signature: new Uint8Array(await crypto.subtle.sign('Ed25519', key, message)) };
      },
    };
    window.phantom = { solana: provider }; window.solflare = provider;
  }, wallets.map(value => ({ wallet: value.user.wallet, pkcs8: value.pkcs8 })));
  await page.route('**/*', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.origin !== origin) { f.blocked.push(url.origin); await route.abort(); return; }
    if (!url.pathname.startsWith('/api/')) { if (!await f.onResource?.(route, url.pathname)) await route.continue(); return; }
    const method = request.method(); const body = request.postData() ? request.postDataJSON() : null;
    const entry = { path: url.pathname, method, account: request.headers()['x-oraclebot-account'] || null, body };
    f.requests.push(entry);
    if (await f.onApi?.(route, entry)) return;
    const user = f.owner < 0 ? null : wallets[f.owner].user;
    if (entry.path === '/api/config') return json(route, { coins: ['SOL', 'BTC', 'ETH', 'ZEC'], plans, trialDays: 7, billingConfigured: true, billingPlanChanges: true, durableBacktests: true, customerConnectionsConfigured: true, managedAutomationConfigured: true });
    if (entry.path === '/api/me') return json(route, { user, subscription: user ? { status: 'active', entitled: true, plan: plans[0] } : null, portalAvailable: Boolean(user), usage: user ? { policy: plans[0], bots: 1, backtests: 2, reservedBacktests: 0 } : null });
    if (entry.path === '/api/bots') return json(route, { bots: user ? [f.bot] : [], nextPage: null });
    if (entry.path === '/api/strategies') return json(route, { strategies: [{ id: 'rsi', name: 'RSI', strategyRevision: revision }] });
    if (entry.path === '/api/oracle') { f.oracle.resolve(); return json(route, { status: 'unavailable', topStrategy: null }); }
    if (entry.path === '/api/agent/grants') return json(route, { grants: [] });
    if (entry.path === '/api/backtest-jobs') return json(route, { jobs: f.jobs, moreAvailable: false });
    if (entry.path === '/api/connections' && method === 'GET') return json(route, { connections: [f.connection], nextCursor: null });
    if (entry.path === '/api/billing/plan-changes') return json(route, { changes: f.operations, moreAvailable: false });
    if (entry.path === '/api/auth/logout') { f.owner = -1; return json(route, { signedOut: true }); }
    if (entry.path === '/api/auth/challenge') {
      const id = crypto.randomUUID(); const message = `Synthetic sign-in fixture for ${body.wallet}\nNonce: ${id}`;
      f.challenges.set(id, { wallet: body.wallet, message }); return json(route, { id, message });
    }
    if (entry.path === '/api/auth/verify') {
      const challenge = f.challenges.get(body.id); const index = wallets.findIndex(value => value.user.wallet === challenge?.wallet);
      assert.ok(index >= 0);
      assert.equal(await crypto.subtle.verify('Ed25519', wallets[index].keys.publicKey, Buffer.from(body.signature, 'base64'), new TextEncoder().encode(challenge.message)), true);
      f.owner = index; return json(route, { user: wallets[index].user });
    }
    if (entry.path === `/api/bots/${f.bot.id}/automation` && method === 'GET') return json(route, { configured: f.configured, enabled: f.configured, allocationQuantity: '0', reason: 'awaiting_signal' });
    return json(route, { error: 'unmodeled_fixture_endpoint' }, 501);
  });
  f.go = async view => {
    await page.goto(`${origin}/#overview`); await f.oracle.promise;
    await page.waitForFunction(label => document.querySelector('[data-wallet-label]')?.textContent === label, short(wallets[0].user.wallet));
    await page.evaluate(view => { location.hash = view; }, view);
    await page.waitForFunction(view => document.querySelector(`.sidebar [data-view="${view}"]`)?.classList.contains('active'), view);
  };
  f.start = async view => {
    await page.goto(`${origin}/#${view}`);
    await page.waitForFunction(label => document.querySelector('[data-wallet-label]')?.textContent === label, short(wallets[0].user.wallet));
  };
  f.drain = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  f.switchAccount = async () => {
    await page.evaluate(() => { for (const dialog of document.querySelectorAll('dialog[open]')) dialog.close(); location.hash = 'settings'; });
    await page.locator('main [data-action="logout"]').click();
    await page.waitForSelector('main [data-action="wallet"]');
    await page.evaluate(() => { window.syntheticWalletIndex = 1; });
    await page.locator('main [data-action="wallet"]').click(); await page.locator('[data-provider="phantom"]').click();
    await page.waitForFunction(label => document.querySelector('[data-wallet-label]')?.textContent === label, short(wallets[1].user.wallet));
  };
  f.close = async () => { for (const release of f.releases) release(); await context.close(); };
  f.json = json;
  return f;
}
async function group(name, run) {
  const f = await fixture(); const start = Date.now();
  try { await run(f); assert.deepEqual(f.errors, []); assert.deepEqual(f.blocked, []); groups.push({ name, passed: true, durationMs: Date.now() - start }); console.log(`PASS ${name}`); }
  catch (error) { groups.push({ name, passed: false, durationMs: Date.now() - start }); throw error; }
  finally { await f.close(); }
}
const writes = (f, suffix) => f.requests.filter(entry => entry.method === 'POST' && entry.path.endsWith(suffix));
const configuredServices = { coins: ['SOL', 'BTC', 'ETH', 'ZEC'], plans, trialDays: 7, billingConfigured: true, billingPlanChanges: true, durableBacktests: true, customerConnectionsConfigured: true, managedAutomationConfigured: true };
function holdStartupMetadata(f) {
  const gate = deferred(); f.releases.push(gate.resolve);
  f.onResource = async (route, path) => {
    if (path !== '/research/catalog.json') return false;
    await gate.promise; await f.json(route, { articles: [] }); return true;
  };
  return gate;
}
async function assertCoinbaseKey(pem) {
  assert.equal(pem, normalizedCoinbasePem);
  const key = await importSigningKey(pem); const challenge = new TextEncoder().encode('Synthetic browser credential normalization');
  const signature = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, challenge);
  assert.equal(await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, coinbaseKeys.publicKey, signature, challenge), true);
}
async function assertNoCoinbaseDisclosure(f) {
  const snapshot = await f.page.evaluate(() => JSON.stringify({ html: document.documentElement.outerHTML, text: document.body.innerText, localStorage: { ...localStorage }, sessionStorage: { ...sessionStorage } }));
  for (const marker of [coinbaseKeyName, coinbaseKeyBody]) {
    assert.equal(snapshot.includes(marker), false);
    assert.equal(f.diagnostics.some(value => value.includes(marker)), false);
  }
}
const result = value => ({ metrics: { total_return: value, final_equity: 1000 * (1 + value), total_fees: 1 }, equity: [1000, 1000 * (1 + value)], provenance: 'Synthetic historical fixture' });
async function openAutomation(f) {
  await f.go('bots'); await f.page.getByRole('button', { name: 'Automation & authorization' }).click();
  await f.page.waitForFunction(() => document.querySelector('.automation-dialog button[type="submit"]')?.disabled === false);
  return f.page.locator('.automation-dialog');
}
function automationApi(f, { tamper = false } = {}) {
  f.onApi = async (route, entry) => {
    if (entry.path.endsWith('/automation/challenge')) {
      const challengeId = crypto.randomUUID();
      const value = { challengeId, policy: tamper ? { ...entry.body.policy, maxTotalUsd: 999 } : entry.body.policy,
        config: { version: 1, venue: 'coinbase', asset: 'SOL', product: 'spot', leverage: 1, strategyId: 'rsi', strategyRevision: revision, intervalSeconds: 3600, budgetUsd: 10 },
        message: `Synthetic managed bot preauthorization\nWallet: ${wallets[0].user.wallet}\nCustomer connection: ${f.connection.id}\nLimits: ${JSON.stringify(entry.body.policy)}\nNonce: ${challengeId}` };
      f.challenges.set(challengeId, value); await f.json(route, value); return true;
    }
    if (entry.path.endsWith('/automation') && entry.method === 'POST') {
      const value = f.challenges.get(entry.body.challengeId);
      assert.equal(await crypto.subtle.verify('Ed25519', wallets[0].keys.publicKey, Buffer.from(entry.body.signature, 'base64'), new TextEncoder().encode(value.message)), true);
      f.configured = true; await f.json(route, { enabled: true }); return true;
    }
    return false;
  };
}

try {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}) });
  await group('direct authenticated Settings enables Coinbase as soon as delayed configuration arrives', async f => {
    const config = deferred(); const metadata = holdStartupMetadata(f); f.releases.push(config.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/config') { await config.promise; await f.json(route, configuredServices); return true; }
      if (entry.path === '/api/strategies') { await metadata.promise; await f.json(route, { strategies: [] }); return true; }
      return false;
    };
    await f.start('settings');
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).isDisabled(), true);
    const response = f.page.waitForResponse(value => new URL(value.url()).pathname === '/api/config');
    config.resolve(); await (await response).finished(); await f.drain();
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).isDisabled(), false, 'Direct Settings must apply configured connections before unrelated metadata finishes.');
    assert.equal(await f.page.getByLabel('Secret', { exact: true }).isDisabled(), false);
    assert.equal(await f.page.locator('.connection-form button[type="submit"]').isDisabled(), false);
    assert.equal(f.requests.some(entry => entry.path === '/api/connections' && entry.account === wallets[0].user.id), true);
    // Metadata completion must retain the current form and any private draft.
    const keyInput = await f.page.getByLabel('Key ID', { exact: true }).elementHandle(); await keyInput.fill(coinbaseKeyName);
    const oracle = f.oracle.promise; metadata.resolve(); await oracle; await f.drain();
    assert.equal(await keyInput.evaluate(input => input.isConnected), true);
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).inputValue(), coinbaseKeyName);
    assert.equal(await f.page.evaluate(() => window.syntheticSignatures.length), 0);
  });
  await group('direct Settings uses configuration delivered before account hydration without waiting for research', async f => {
    const metadata = holdStartupMetadata(f); const account = deferred(); f.releases.push(account.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/me') { await account.promise; await f.json(route, { user: wallets[0].user, subscription: null, usage: null }); return true; }
      if (entry.path === '/api/strategies') { await metadata.promise; await f.json(route, { strategies: [] }); return true; }
      return false;
    };
    const response = f.page.waitForResponse(value => new URL(value.url()).pathname === '/api/config');
    await f.page.goto(`${origin}/#settings`); await (await response).finished(); await f.drain();
    assert.equal(await f.page.locator('.connection-form').count(), 0);
    account.resolve();
    await f.page.waitForFunction(label => document.querySelector('[data-wallet-label]')?.textContent === label, short(wallets[0].user.wallet)); await f.drain();
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).isDisabled(), false);
    assert.equal(await f.page.getByLabel('Secret', { exact: true }).isDisabled(), false);
    assert.equal(await f.page.locator('.connection-form button[type="submit"]').isDisabled(), false);
    assert.doesNotMatch(await f.page.locator('.connection-form .form-message').innerText(), /not available/);
  });
  await group('late configuration updates the current Settings after startup navigation', async f => {
    const config = deferred(); const metadata = holdStartupMetadata(f); f.releases.push(config.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/config') { await config.promise; await f.json(route, configuredServices); return true; }
      if (entry.path === '/api/strategies') { await metadata.promise; await f.json(route, { strategies: [] }); return true; }
      return false;
    };
    await f.start('overview'); await f.page.evaluate(() => { location.hash = 'settings'; }); await f.page.waitForSelector('.connection-form');
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).isDisabled(), true);
    const response = f.page.waitForResponse(value => new URL(value.url()).pathname === '/api/config');
    config.resolve(); await (await response).finished(); await f.drain();
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).isDisabled(), false);
    assert.equal(await f.page.locator('.connection-form button[type="submit"]').isDisabled(), false);
  });
  for (const mode of ['disabled', 'malformed flag', 'failed', 'malformed response']) await group(`direct Settings keeps connections disabled when configuration is ${mode}`, async f => {
    f.onApi = async (route, entry) => {
      if (entry.path !== '/api/config') return false;
      const value = mode === 'failed' ? { error: 'service_unavailable' } : mode === 'malformed response' ? null : { ...configuredServices, customerConnectionsConfigured: mode === 'malformed flag' ? 'true' : false };
      await f.json(route, value, mode === 'failed' ? 503 : 200); return true;
    };
    await f.start('settings'); await f.oracle.promise; await f.drain();
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).isDisabled(), true);
    assert.equal(await f.page.getByLabel('Secret', { exact: true }).isDisabled(), true);
    assert.equal(await f.page.locator('.connection-form button[type="submit"]').isDisabled(), true);
    assert.match(await f.page.locator('.connection-form .form-message').innerText(), /not available/);
    assert.equal(f.requests.filter(entry => entry.path === '/api/connections').length, 0);
  });
  await group('late configuration after account replacement loads only the current wallet connections', async f => {
    const config = deferred(); const metadata = holdStartupMetadata(f); f.releases.push(config.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/config') { await config.promise; await f.json(route, configuredServices); return true; }
      if (entry.path === '/api/strategies') { await metadata.promise; await f.json(route, { strategies: [] }); return true; }
      return false;
    };
    await f.start('settings'); await f.switchAccount();
    const response = f.page.waitForResponse(value => new URL(value.url()).pathname === '/api/config');
    config.resolve(); await (await response).finished(); await f.drain();
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).isDisabled(), false);
    const reads = f.requests.filter(entry => entry.path === '/api/connections');
    assert.equal(reads.length, 1); assert.equal(reads[0].account, wallets[1].user.id);
    assert.equal(writes(f, '/connections').length, 0);
  });
  await group('late configuration after logout cannot restore the former wallet connection form', async f => {
    const config = deferred(); const metadata = holdStartupMetadata(f); f.releases.push(config.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/config') { await config.promise; await f.json(route, configuredServices); return true; }
      if (entry.path === '/api/strategies') { await metadata.promise; await f.json(route, { strategies: [] }); return true; }
      return false;
    };
    await f.start('settings'); await f.page.locator('main [data-action="logout"]').click(); await f.page.waitForSelector('main [data-action="wallet"]');
    const response = f.page.waitForResponse(value => new URL(value.url()).pathname === '/api/config');
    config.resolve(); await (await response).finished(); metadata.resolve(); await f.oracle.promise; await f.drain();
    assert.equal(await f.page.locator('.connection-form').count(), 0);
    assert.equal(await f.page.locator('.settings-value').count(), 0);
    assert.equal(f.requests.filter(entry => entry.path === '/api/connections').length, 0);
    assert.equal(await f.page.evaluate(() => window.syntheticSignatures.length), 0);
  });
  await group('late configuration and metadata preserve the current Backtest form and typed values', async f => {
    const config = deferred(); const metadata = holdStartupMetadata(f); f.releases.push(config.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/config') { await config.promise; await f.json(route, { ...configuredServices, coins: ['SOL', 'BTC'] }); return true; }
      if (entry.path === '/api/strategies') { await metadata.promise; await f.json(route, { strategies: [{ id: 'rsi', name: 'RSI' }] }); return true; }
      return false;
    };
    await f.start('backtest');
    const form = await f.page.locator('#backtest-form').elementHandle();
    await f.page.locator('#backtest-form [name="capital"]').fill('2345');
    await f.page.locator('#backtest-form [name="coin"]').selectOption('BTC');
    await f.page.locator('#backtest-form [name="strategy"]').selectOption('rsi');
    const response = f.page.waitForResponse(value => new URL(value.url()).pathname === '/api/config');
    config.resolve(); await (await response).finished(); await f.drain();
    assert.equal(await form.evaluate(value => value.isConnected), true);
    assert.deepEqual(await f.page.locator('#backtest-form [name="coin"] option').evaluateAll(values => values.map(value => value.value)), ['SOL', 'BTC']);
    metadata.resolve(); await f.oracle.promise; await f.drain();
    assert.equal(await form.evaluate(value => value.isConnected), true);
    assert.equal(await f.page.locator('#backtest-form [name="capital"]').inputValue(), '2345');
    assert.equal(await f.page.locator('#backtest-form [name="coin"]').inputValue(), 'BTC');
    assert.equal(await f.page.locator('#backtest-form [name="strategy"]').inputValue(), 'rsi');
  });
  await group('durable backtest queues, polls and renders saved result', async f => {
    const id = crypto.randomUUID(); let polls = 0;
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/backtest-jobs' && entry.method === 'POST') { assert.equal(entry.account, wallets[0].user.id); await f.json(route, { id, status: 'queued' }); return true; }
      if (entry.path === `/api/backtest-jobs/${id}`) { polls++; assert.equal(entry.account, wallets[0].user.id); await f.json(route, { id, status: polls === 1 ? 'running' : 'complete', result: result(0.12) }); return true; }
      return false;
    };
    await f.go('backtest'); await f.page.locator('#backtest-form button[type="submit"]').click();
    await f.page.waitForFunction(() => document.querySelector('#backtest-output')?.textContent.includes('12%'));
    assert.equal(polls, 2); assert.equal(writes(f, '/backtest-jobs').length, 1);
    assert.equal(await f.page.locator('svg[aria-label="Historical simulated equity"]').count(), 1);
  });
  await group('lost backtest response recovers through recent jobs without a duplicate submit', async f => {
    const id = crypto.randomUUID();
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/backtest-jobs' && entry.method === 'POST') { f.jobs = [{ id, status: 'complete', request: entry.body.request }]; await route.abort('failed'); return true; }
      if (entry.path === `/api/backtest-jobs/${id}`) { await f.json(route, { id, status: 'complete', result: result(0.17) }); return true; }
      return false;
    };
    await f.go('backtest'); await f.page.locator('#backtest-form button[type="submit"]').click();
    await f.page.waitForFunction(() => document.querySelector('#backtest-message')?.textContent.length > 0);
    await f.page.evaluate(() => { location.hash = 'settings'; }); await f.page.waitForSelector('.connection-form');
    await f.page.evaluate(() => { location.hash = 'backtest'; }); await f.page.getByRole('button', { name: 'View result' }).click();
    await f.page.waitForFunction(() => document.querySelector('#backtest-output')?.textContent.includes('17%'));
    assert.equal(writes(f, '/backtest-jobs').length, 1);
  });
  await group('a previous account pending backtest cannot render into the next account', async f => {
    const id = crypto.randomUUID(); const gate = deferred(); const started = deferred(); f.releases.push(gate.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/backtest-jobs' && entry.method === 'POST') { await f.json(route, { id, status: 'running' }); return true; }
      if (entry.path === `/api/backtest-jobs/${id}`) { started.resolve(); await gate.promise; await f.json(route, { id, status: 'complete', result: result(0.9137) }); return true; }
      return false;
    };
    await f.go('backtest'); await f.page.locator('#backtest-form button[type="submit"]').click(); await started.promise;
    await f.switchAccount(); gate.resolve(); await f.drain();
    await f.page.evaluate(() => { location.hash = 'backtest'; }); await f.page.waitForSelector('#backtest-output'); await f.drain();
    assert.doesNotMatch(await f.page.locator('main').innerText(), /91\.37%/);
    assert.equal(f.requests.find(entry => entry.path === `/api/backtest-jobs/${id}`).account, wallets[0].user.id);
    assert.equal(f.requests.filter(entry => entry.path === '/api/backtest-jobs' && entry.method === 'GET').at(-1).account, wallets[1].user.id);
  });
  await group('masked Coinbase fields preserve a pasted ECDSA key, bind the account and clear before the response', async f => {
    const gate = deferred(); const started = deferred(); f.releases.push(gate.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/connections' && entry.method === 'POST') {
        assert.equal(entry.account, wallets[0].user.id); await assertCoinbaseKey(entry.body.privateKey);
        assert.equal(entry.body.apiKeyName, coinbaseKeyName); assert.equal(entry.body.venue, 'coinbase');
        assert.equal(entry.body.portfolioId, f.connection.portfolioId); assert.match(entry.body.idempotencyKey, /^[0-9a-f-]{36}$/);
        started.resolve(); await gate.promise;
        await f.json(route, { error: 'connection_conflict', message: `Unsafe provider detail: ${coinbaseKeyName} ${coinbaseKeyBody}` }, 409); return true;
      }
      return false;
    };
    await f.go('settings');
    const keyId = f.page.getByLabel('Key ID', { exact: true }); const secret = f.page.getByLabel('Secret', { exact: true });
    assert.equal(await f.page.locator('.connection-form input[type="file"]').count(), 0);
    for (const input of [keyId, secret]) {
      assert.equal(await input.getAttribute('type'), 'password'); assert.equal(await input.getAttribute('autocomplete'), 'off');
      assert.equal(await input.getAttribute('spellcheck'), 'false'); assert.equal(await input.getAttribute('autocapitalize'), 'none');
      assert.equal(await input.evaluate(value => value.required), true);
    }
    await keyId.fill(` ${coinbaseKeyName} `); await secret.fill(coinbasePem);
    const pastedSecret = await secret.inputValue();
    assert.doesNotMatch(pastedSecret, /[\r\n]/); assert.equal(pastedSecret.replace(/\s/g, ''), coinbasePem.replace(/\s/g, ''));
    await f.page.getByLabel('Dedicated portfolio ID (optional)', { exact: true }).fill(f.connection.portfolioId);
    await assertNoCoinbaseDisclosure(f);
    await f.page.locator('.connection-form button[type="submit"]').click(); await started.promise;
    assert.equal(await keyId.inputValue(), ''); assert.equal(await secret.inputValue(), '');
    assert.equal(await f.page.locator('.connection-form button[type="submit"]').isDisabled(), true);
    await assertNoCoinbaseDisclosure(f); gate.resolve();
    await f.page.waitForFunction(() => document.querySelector('.connection-form .form-message')?.textContent.length > 0);
    assert.match(await f.page.locator('.connection-form .form-message').innerText(), /could not be verified/);
    await assertNoCoinbaseDisclosure(f);
    assert.equal(writes(f, '/connections').length, 1);
  });
  await group('masked Coinbase fields accept escaped PEM newlines and omit an unspecified portfolio', async f => {
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/connections' && entry.method === 'POST') {
        assert.equal(entry.account, wallets[0].user.id); assert.equal(entry.body.apiKeyName, coinbaseKeyName);
        assert.equal(Object.hasOwn(entry.body, 'portfolioId'), false); await assertCoinbaseKey(entry.body.privateKey);
        await f.json(route, f.connection); return true;
      }
      return false;
    };
    await f.go('settings');
    await f.page.getByLabel('Key ID', { exact: true }).fill(coinbaseKeyName);
    await f.page.getByLabel('Secret', { exact: true }).fill(coinbasePem.replaceAll('\n', '\\n'));
    await f.page.locator('.connection-form button[type="submit"]').click();
    await f.page.waitForFunction(() => document.querySelector('.connection-form .form-message')?.textContent.includes('Trade-only portfolio verified'));
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).inputValue(), '');
    assert.equal(await f.page.getByLabel('Secret', { exact: true }).inputValue(), '');
    await assertNoCoinbaseDisclosure(f); assert.equal(writes(f, '/connections').length, 1);
  });
  await group('navigation clears unsent Coinbase inputs and account replacement discards a held connection result', async f => {
    const gate = deferred(); const started = deferred(); f.releases.push(gate.resolve);
    f.onApi = async (route, entry) => {
      if (entry.path === '/api/connections' && entry.method === 'POST') {
        assert.equal(entry.account, wallets[0].user.id); await assertCoinbaseKey(entry.body.privateKey);
        started.resolve(); await gate.promise; await f.json(route, f.connection); return true;
      }
      return false;
    };
    await f.go('settings');
    const keyId = await f.page.getByLabel('Key ID', { exact: true }).elementHandle();
    const secret = await f.page.getByLabel('Secret', { exact: true }).elementHandle();
    await keyId.fill(coinbaseKeyName); await secret.fill(coinbasePem);
    await f.page.evaluate(() => { location.hash = 'backtest'; }); await f.page.waitForSelector('#backtest-form');
    assert.equal(await keyId.evaluate(input => input.value), ''); assert.equal(await secret.evaluate(input => input.value), '');
    assert.equal(writes(f, '/connections').length, 0);
    await f.page.evaluate(() => { location.hash = 'settings'; }); await f.page.waitForSelector('.connection-form');
    await f.page.getByLabel('Key ID', { exact: true }).fill(coinbaseKeyName);
    await f.page.getByLabel('Secret', { exact: true }).fill(coinbasePem);
    await f.page.locator('.connection-form button[type="submit"]').click(); await started.promise;
    const pendingKey = await f.page.getByLabel('Key ID', { exact: true }).elementHandle();
    const pendingSecret = await f.page.getByLabel('Secret', { exact: true }).elementHandle();
    // Even newly typed values in the pending form must not survive an account transition.
    await pendingKey.fill(coinbaseKeyName); await pendingSecret.fill(coinbasePem);
    await f.switchAccount(); gate.resolve(); await f.drain();
    assert.equal(await pendingKey.evaluate(input => input.value), ''); assert.equal(await pendingSecret.evaluate(input => input.value), '');
    assert.equal(await f.page.getByLabel('Key ID', { exact: true }).inputValue(), '');
    assert.equal(await f.page.getByLabel('Secret', { exact: true }).inputValue(), '');
    assert.doesNotMatch(await f.page.locator('main').innerText(), /Trade-only portfolio verified/);
    assert.equal(f.requests.filter(entry => entry.path === '/api/connections' && entry.method === 'GET').at(-1).account, wallets[1].user.id);
    await assertNoCoinbaseDisclosure(f); assert.equal(writes(f, '/connections').length, 1);
  });
  await group('unsupported Coinbase credential formats clear without a connection request', async f => {
    await f.go('settings');
    for (const [keyId, secret] of [[crypto.randomUUID(), coinbasePem], [coinbaseKeyName, 'synthetic-hmac-secret'], [coinbaseKeyName, coinbasePem.replace('END PRIVATE KEY', 'END EC PRIVATE KEY')]]) {
      await f.page.getByLabel('Key ID', { exact: true }).fill(keyId); await f.page.getByLabel('Secret', { exact: true }).fill(secret);
      await f.page.locator('.connection-form button[type="submit"]').click();
      assert.equal(await f.page.getByLabel('Key ID', { exact: true }).inputValue(), '');
      assert.equal(await f.page.getByLabel('Secret', { exact: true }).inputValue(), '');
      assert.match(await f.page.locator('.connection-form .form-message').innerText(), /could not be verified/);
    }
    assert.equal(writes(f, '/connections').length, 0); await assertNoCoinbaseDisclosure(f);
  });
  await group('billing quote and keep-current collect no charge; confirm and scheduled undo are explicit', async f => {
    let quotes = 0;
    f.onApi = async (route, entry) => {
      if (entry.path.endsWith('/plan-change/quote')) { quotes++; assert.equal(entry.account, wallets[0].user.id); await f.json(route, { quoteId: `quote_fixture_${quotes}`, targetPlan: 'advanced', kind: 'upgrade', currency: 'usd', amountDueNowCents: 1234, renewalAmountCents: 2999, renewalAmountExcludesTax: true, automaticTaxEnabled: true, managedPaymentsEnabled: true, effectiveAt: time() }); return true; }
      if (entry.path.endsWith('/plan-change/commit')) { assert.equal(entry.body.quoteId, 'quote_fixture_2'); assert.equal(entry.account, wallets[0].user.id); await f.json(route, { status: 'applied' }); return true; }
      if (entry.path.endsWith('/cancel') && entry.path.includes('/plan-changes/')) { assert.equal(entry.account, wallets[0].user.id); await f.json(route, { status: 'applied' }); return true; }
      return false;
    };
    await f.go('pricing'); await f.page.locator('main [data-plan="advanced"] button').click();
    await f.page.waitForSelector('#plan-change-dialog');
    const quoteText = await f.page.locator('#plan-change-dialog').innerText();
    assert.match(quoteText, /\$29\.99 USD per month \+ applicable tax/);
    assert.match(quoteText, /Due now: \$12\.34 USD, including any tax in this quote/);
    assert.equal(writes(f, '/plan-change/commit').length, 0);
    await f.page.getByRole('button', { name: 'Keep current plan' }).click(); assert.equal(writes(f, '/plan-change/commit').length, 0);
    await f.page.locator('main [data-plan="advanced"] button').click(); await f.page.getByRole('button', { name: 'Confirm this change' }).click();
    await f.page.waitForSelector('.connection-form'); assert.equal(writes(f, '/plan-change/commit').length, 1);
    f.operations = [{ changeId: crypto.randomUUID(), kind: 'plan_change', status: 'scheduled' }];
    await f.page.evaluate(() => { location.hash = 'pricing'; }); await f.page.waitForSelector('.tier-grid');
    await f.page.evaluate(() => { location.hash = 'settings'; }); await f.page.getByRole('button', { name: 'Cancel scheduled downgrade' }).click();
    await f.page.waitForFunction(() => document.querySelector('main')?.textContent.includes('Downgrade undo · applied'));
    assert.equal(f.requests.filter(entry => entry.method === 'POST' && entry.path.includes('/plan-changes/') && entry.path.endsWith('/cancel')).length, 1);
    assert.equal(writes(f, '/billing/checkout').length, 0);
  });
  await group('a quote returned after account switch cannot open a stale payment confirmation', async f => {
    const gate = deferred(); const started = deferred(); f.releases.push(gate.resolve);
    f.onApi = async (route, entry) => {
      if (!entry.path.endsWith('/plan-change/quote')) return false;
      started.resolve(); await gate.promise; await f.json(route, { quoteId: 'quote_previous_account', targetPlan: 'advanced', kind: 'upgrade', currency: 'usd', amountDueNowCents: 1234, renewalAmountCents: 2999, effectiveAt: time() }); return true;
    };
    await f.go('pricing'); await f.page.locator('main [data-plan="advanced"] button').click(); await started.promise;
    await f.switchAccount(); gate.resolve(); await f.drain();
    assert.equal(await f.page.locator('#plan-change-dialog').count(), 0); assert.equal(writes(f, '/plan-change/commit').length, 0);
  });
  await group('managed authorization signs exact wallet and finite limits once without per-trade prompts', async f => {
    automationApi(f); const dialog = await openAutomation(f);
    await dialog.locator('[name="maxTradeUsd"]').fill('12'); await dialog.locator('[name="maxTotalUsd"]').fill('120');
    await dialog.locator('[name="days"]').selectOption('1'); await dialog.locator('button[type="submit"]').click();
    await f.page.waitForFunction(() => document.querySelector('.automation-dialog')?.textContent.includes('Authorization saved.'));
    const challenge = writes(f, '/automation/challenge')[0];
    assert.equal(challenge.account, wallets[0].user.id); assert.equal(challenge.body.connectionId, f.connection.id);
    assert.equal(challenge.body.policy.maxTradeUsd, 12); assert.equal(challenge.body.policy.maxTotalUsd, 120);
    assert.deepEqual(challenge.body.policy.assets, ['SOL']); assert.deepEqual(challenge.body.policy.products, ['spot']); assert.equal(challenge.body.policy.maxLeverage, 1);
    assert.ok(challenge.body.policy.expiresAt >= time() + 86390 && challenge.body.policy.expiresAt <= time() + 86400);
    assert.equal(await f.page.evaluate(() => window.syntheticSignatures.length), 1); assert.equal(writes(f, '/automation').length, 1);
    await dialog.getByRole('button', { name: 'Close automation' }).click();
    await f.page.getByRole('button', { name: 'Automation & authorization' }).click();
    await f.page.waitForFunction(() => document.querySelector('.automation-dialog')?.textContent.includes('Enabled'));
    assert.equal(await f.page.evaluate(() => window.syntheticSignatures.length), 1);
    assert.equal(f.requests.some(entry => /\/trades?(?:\/|$)/.test(entry.path)), false);
  });
  await group('wrong signing wallet and altered authorization limits are refused before signing or activation', async f => {
    automationApi(f); let dialog = await openAutomation(f);
    await f.page.evaluate(() => { window.syntheticWalletIndex = 1; }); await dialog.locator('button[type="submit"]').click();
    await f.page.waitForFunction(() => document.querySelector('.automation-dialog')?.textContent.includes('Unlock the signing wallet'));
    assert.equal(writes(f, '/automation/challenge').length, 0); assert.equal(await f.page.evaluate(() => window.syntheticSignatures.length), 0);
    await dialog.getByRole('button', { name: 'Close automation' }).click(); await f.page.evaluate(() => { window.syntheticWalletIndex = 0; });
    automationApi(f, { tamper: true }); await f.page.getByRole('button', { name: 'Automation & authorization' }).click(); dialog = f.page.locator('.automation-dialog');
    await f.page.waitForFunction(() => document.querySelector('.automation-dialog button[type="submit"]')?.disabled === false);
    await dialog.locator('button[type="submit"]').click();
    await f.page.waitForFunction(() => document.querySelector('.automation-dialog')?.textContent.includes('does not match'));
    assert.equal(await f.page.evaluate(() => window.syntheticSignatures.length), 0); assert.equal(writes(f, '/automation').length, 0);
  });
  await group('mutating authorization fields while the wallet holds a signature prevents activation', async f => {
    automationApi(f); const dialog = await openAutomation(f); await f.page.evaluate(() => { window.holdSyntheticSignature = true; });
    await dialog.locator('button[type="submit"]').click(); await f.page.waitForFunction(() => window.syntheticSignatures.length === 1 && typeof window.releaseSyntheticSignature === 'function');
    await dialog.locator('[name="maxTotalUsd"]').fill('110');
    await f.page.evaluate(() => { window.releaseSyntheticSignature(); }); await f.drain();
    await f.page.waitForFunction(() => document.querySelector('.automation-dialog button[type="submit"]')?.disabled === false);
    assert.equal(writes(f, '/automation').length, 0);
  });
  await group('navigation removes private bot authorization details and prevents stale activation', async f => {
    automationApi(f); await openAutomation(f);
    assert.equal(await f.page.locator('.automation-dialog').count(), 1);
    await f.page.evaluate(() => { location.hash = 'settings'; });
    await f.page.waitForFunction(() => document.querySelector('.automation-dialog') === null);
    assert.equal(writes(f, '/automation').length, 0);
    assert.equal(await f.page.evaluate(() => window.syntheticSignatures.length), 0);
  });
  await group('a held authorization signature cannot activate after account replacement', async f => {
    automationApi(f); const dialog = await openAutomation(f); await f.page.evaluate(() => { window.holdSyntheticSignature = true; });
    await dialog.locator('button[type="submit"]').click(); await f.page.waitForFunction(() => typeof window.releaseSyntheticSignature === 'function');
    await f.page.evaluate(() => { window.holdSyntheticSignature = false; });
    await f.switchAccount(); await f.page.evaluate(() => { window.releaseSyntheticSignature(); }); await f.drain();
    assert.equal(writes(f, '/automation').length, 0);
    assert.equal(f.requests.filter(entry => entry.path.endsWith('/automation/challenge'))[0].account, wallets[0].user.id);
    assert.equal(await f.page.locator('.automation-dialog').count(), 0);
  });
  console.log(`PASS hosted browser groups: ${groups.length}/${groups.length}; synthetic fixtures only; browser ${browser.version()}`);
} finally {
  if (process.env.ORACLEBOT_BROWSER_RECEIPT) await writeFile(process.env.ORACLEBOT_BROWSER_RECEIPT, JSON.stringify({ groups, passed: groups.filter(group => group.passed).length, total: groups.length, browserVersion: browser?.version() || null, fixtureOnly: true }, null, 2) + '\n');
  await browser?.close(); await new Promise(resolve => server.close(resolve));
}
