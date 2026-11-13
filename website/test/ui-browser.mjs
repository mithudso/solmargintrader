/** Real browser regressions against local fixtures. No wallet, Stripe or venue calls. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const publicRoot = new URL('../public/', import.meta.url);
const types = { js: 'text/javascript', html: 'text/html', css: 'text/css', svg: 'image/svg+xml', json: 'application/json' };
let billingConfigured = false;
let botsUnavailable = false;
let bots = [];
let paginatedBots = false;
const firstUser = { id: 'fixture', wallet: 'fixture-wallet' };
const secondUser = { id: 'second', wallet: 'second-wallet' };
let fixtureUser = firstUser;
let challengeWallet;
const observedRequests = [];
const plans = [
  { id: 'starter', name: 'Starter', monthlyUsd: 9.99, botLimit: 3, backtestsPerDay: 10 },
  { id: 'advanced', name: 'Advanced', monthlyUsd: 29.99, botLimit: 10, backtestsPerDay: null },
  { id: 'unlimited', name: 'Unlimited', monthlyUsd: 49.99, botLimit: null, backtestsPerDay: null },
];
function accountSnapshot(user = fixtureUser) {
  return { user, subscription: user ? { status: 'trialing', entitled: true, plan: plans[0] } : null, portalAvailable: Boolean(user), usage: user ? { policy: plans[0], bots: 2, backtests: user.id === 'second' ? 3 : 7, reservedBacktests: 0 } : null };
}
const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  if (pathname.startsWith('/api/')) {
    observedRequests.push({ pathname, method: request.method, account: request.headers['x-oraclebot-account'] });
    if (pathname === '/api/auth/logout' || pathname === '/api/me' && request.method === 'DELETE') fixtureUser = null;
    if (pathname === '/api/auth/challenge') { let body = ''; for await (const part of request) body += part; challengeWallet = JSON.parse(body).wallet; }
    if (pathname === '/api/auth/verify') fixtureUser = challengeWallet === secondUser.wallet ? secondUser : firstUser;
    const data = pathname === '/api/config' ? { coins: ['SOL', 'BTC'], trialDays: 7, billingConfigured, plans, engineConfigured: false }
      : pathname === '/api/me' ? accountSnapshot()
        : pathname === '/api/bots' ? (botsUnavailable ? { error: 'service_unavailable' } : paginatedBots ? (new URL(request.url, 'http://localhost').searchParams.get('page') === '1' ? { bots: [{ id: 'second', name: 'Second page configuration', coin: 'SOL', status: 'configured' }], nextPage: null } : { bots: [{ id: 'first', name: 'First page configuration', coin: 'SOL', status: 'configured' }], nextPage: 1 }) : { bots })
          : pathname === '/api/strategies' ? { strategies: [{ id: 'rsi', name: 'RSI' }] }
            : pathname === '/api/auth/challenge' ? { id: 'fixture-challenge', message: 'Synthetic wallet sign-in fixture' }
              : pathname === '/api/agent/grants' ? { grants: [] }
            : { status: 'unavailable', topStrategy: null };
    response.writeHead(pathname === '/api/bots' && botsUnavailable ? 503 : 200, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify(data));
    return;
  }
  try {
    const resource = new URL(pathname === '/' ? 'index.html' : `.${pathname}`, publicRoot);
    assert.ok(fileURLToPath(resource).startsWith(fileURLToPath(publicRoot)));
    const body = await readFile(resource);
    response.writeHead(200, { 'Content-Type': types[pathname.split('.').pop()] || 'text/html' });
    response.end(body);
  } catch { response.writeHead(404); response.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
try {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}) });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  for (const [index, value] of [false, undefined, 'true', true].entries()) {
    billingConfigured = value;
    await page.goto(`${origin}/?fixture=${index}#pricing`);
    await page.waitForFunction(disabled => document.querySelector('main [data-action="trial"]')?.disabled === disabled && document.querySelector('[data-wallet-label]')?.textContent === 'fixt…llet', value !== true, { timeout: 5000 });
    const trial = page.locator('main [data-action="trial"]').first();
    assert.equal(await trial.isDisabled(), value !== true);
    assert.match(await trial.innerText(), value === true ? /Start your free trial/ : /unavailable/i);
  }
  assert.equal(await page.locator('.tier-grid section[data-plan]').count(), 3);
  for (const [id, amount, limit] of [['starter', '$9.99', '3 configured bot slots'], ['advanced', '$29.99', '10 configured bot slots'], ['unlimited', '$49.99', 'Unlimited bot slots']]) {
    const card = page.locator(`section[data-plan="${id}"]`);
    assert.match(await card.innerText(), new RegExp(amount.replace('$', '\\$').replace('.', '\\.')));
    assert.ok((await card.innerText()).includes(limit));
    assert.ok(await card.getAttribute('aria-labelledby'));
  }
  assert.match(await page.locator('.usage-panel').innerText(), /7 of 10 backtests/);
  let chosenPlan;
  await page.route('**/api/billing/checkout', async route => { chosenPlan = route.request().postDataJSON(); await route.fulfill({ status: 503, json: { error: 'billing_unavailable' } }); });
  await page.locator('button[data-plan="advanced"]').click();
  await page.waitForFunction(() => document.querySelector('#toast').textContent.includes('not available'));
  assert.deepEqual(chosenPlan, { plan: 'advanced' });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.setViewportSize({ width: 1280, height: 720 });
  console.log('PASS three accessible, responsive plans use server policies and selected plan IDs');
  console.log('PASS trial signup requires an explicitly configured billing service');
  billingConfigured = false;
  await page.goto(`${origin}/#overview`);
  await page.locator('.sidebar [data-action="pricing"]').click();
  await page.waitForFunction(() => document.querySelector('#page-label').textContent === 'Membership');
  assert.equal(await page.locator('main [data-action="trial"]').first().isDisabled(), true);
  let portalRequests = 0;
  await page.route('**/api/billing/portal', async route => { portalRequests++; await route.fulfill({ status: 503, json: { error: 'billing_unavailable' } }); });
  await page.locator('main [data-action="portal"]').click();
  await page.waitForFunction(() => document.querySelector('#toast').textContent.includes('not available'));
  assert.equal(portalRequests, 1);
  console.log('PASS membership navigation and portal cancellation stay available without checkout');

  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let requested;
  const started = new Promise(resolve => { requested = resolve; });
  await page.route('**/api/backtests', async route => {
    requested();
    await gate;
    const coin = route.request().postDataJSON().coin;
    await route.fulfill({ json: { status: 'complete', coin, strategy: 'rsi', metrics: { total_return: coin === 'BTC' ? 0.2 : 0.1 } } });
  });
  await page.goto(`${origin}/#backtest`);
  await page.waitForFunction(() => document.querySelector('#backtest-form [name="strategy"]').value === 'rsi');
  await page.evaluate(() => { window.originalForm = document.querySelector('#backtest-form'); });
  await page.locator('#backtest-form button[type="submit"]').click();
  await started;
  await page.evaluate(() => { location.hash = 'research'; });
  await page.waitForSelector('#research-search');
  await page.evaluate(() => { location.hash = 'backtest'; });
  await page.waitForSelector('#backtest-form');
  await page.locator('#backtest-form [name="coin"]').selectOption('BTC');
  release();
  await page.waitForFunction(() => !window.originalForm.querySelector('button[type="submit"]').disabled);
  assert.doesNotMatch(await page.locator('#backtest-output').innerText(), /Results, with context/);
  await page.locator('#backtest-form button[type="submit"]').click();
  await page.waitForFunction(() => document.querySelector('#backtest-output').textContent.includes('20%'));
  console.log('PASS an old backtest cannot replace a new experiment; the new result still renders');
  botsUnavailable = true;
  await page.goto(`${origin}/?fixture=bot-error#bots`);
  await page.waitForFunction(() => document.querySelector('[data-wallet-label]')?.textContent === 'fixt…llet');
  assert.match(await page.locator('main').innerText(), /configurations could not be loaded/i);
  assert.equal(await page.locator('#nav-bot-count').innerText(), '—');
  assert.doesNotMatch(await page.locator('main').innerText(), /Your first configuration will appear here/);
  botsUnavailable = false;
  bots = [{ id: 'archived', name: 'Old idea', status: 'archived' }];
  await page.locator('[data-action="refresh-bots"]').click();
  await page.waitForFunction(() => !document.querySelector('[data-action="refresh-bots"]'));
  assert.match(await page.locator('main').innerText(), /Your first configuration will appear here/);
  console.log('PASS failed bot reads stay distinct from an empty workspace; archived bots do not hide the empty state');
  paginatedBots = true;
  await page.goto(`${origin}/?fixture=paginated#bots`);
  await page.locator('[data-action="more-bots"]').click();
  await page.waitForFunction(() => document.querySelector('main').textContent.includes('Second page configuration'));
  assert.equal(await page.locator('.bot-card').count(), 2);
  assert.equal(await page.locator('[data-action="more-bots"]').count(), 0);
  console.log('PASS bounded bot pages keep earlier and later configurations accessible');
  let releasePage; let pageStarted;
  const pageHeld = new Promise(resolve => { releasePage = resolve; });
  const pageRequested = new Promise(resolve => { pageStarted = resolve; });
  await page.route(url => url.pathname === '/api/bots' && url.searchParams.get('page') === '1', async route => {
    pageStarted(); await pageHeld;
    await route.fulfill({ json: { bots: [{ id: 'stale-private', name: 'Previous account private configuration', status: 'configured', coin: 'SOL' }], nextPage: 2 } });
  });
  await page.goto(`${origin}/?fixture=pending-page#bots`);
  await page.waitForSelector('[data-action="more-bots"]');
  await page.evaluate(() => { window.pendingPageButton = document.querySelector('[data-action="more-bots"]'); });
  await page.locator('[data-action="more-bots"]').click(); await pageRequested;
  await page.evaluate(() => { location.hash = 'settings'; });
  await page.locator('main [data-action="logout"]').click();
  await page.waitForFunction(() => document.querySelector('main [data-action="wallet"]') !== null);
  releasePage();
  await page.waitForFunction(() => !window.pendingPageButton.disabled);
  await page.evaluate(() => { location.hash = 'bots'; });
  await page.waitForFunction(() => document.querySelector('#page-label').textContent === 'My bots');
  assert.doesNotMatch(await page.locator('main').innerText(), /Previous account private configuration/);
  assert.equal(await page.locator('[data-action="more-bots"]').count(), 0);
  console.log('PASS a pending bot page cannot restore another session’s configurations after sign-out');
  assert.deepEqual(errors, []);
  await page.close();

  const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
  const drain = fixturePage => fixturePage.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const freshPage = async () => {
    fixtureUser = firstUser; bots = []; botsUnavailable = false; paginatedBots = false; billingConfigured = true; observedRequests.length = 0;
    const fixturePage = await browser.newPage(); const diagnostics = []; const blockedRequests = [];
    fixturePage.on('pageerror', error => errors.push(error.message));
    fixturePage.on('console', message => diagnostics.push({ type: message.type(), text: message.text() }));
    await fixturePage.route('**/*', route => {
      const request = route.request();
      if (new URL(request.url()).origin === origin) return route.continue();
      blockedRequests.push({ url: request.url(), method: request.method() });
      return route.abort();
    });
    await fixturePage.addInitScript(wallet => {
      window.fixtureReads = []; window.fixtureSignatures = 0;
      const original = window.fetch.bind(window);
      window.fetch = async (resource, options = {}) => {
        const response = await original(resource, options); const read = response.json.bind(response);
        response.json = async () => { const value = await read(); window.fixtureReads.push({ path: new URL(resource, location.href).pathname, method: options.method || 'GET' }); return value; };
        return response;
      };
      const provider = {
        publicKey: { toString: () => wallet },
        async connect() { if (window.rejectConnect) throw window.rejectionValue; return { publicKey: this.publicKey }; },
        async signMessage() { window.fixtureSignatures++; if (window.rejectSign) throw window.rejectionValue; return { signature: new Uint8Array(64).fill(7) }; }
      };
      window.phantom = { solana: provider }; window.solflare = provider;
    }, secondUser.wallet);
    return { page: fixturePage, diagnostics, blockedRequests };
  };
  const ready = async (fixturePage, view = 'settings') => {
    await fixturePage.goto(`${origin}/#${view}`);
    await fixturePage.waitForFunction(() => document.querySelector('[data-wallet-label]')?.textContent === 'fixt…llet');
  };
  const signInSecond = async fixturePage => {
    await fixturePage.locator('[data-wallet-label]').click();
    await fixturePage.locator('[data-provider="phantom"]').click();
    await fixturePage.waitForFunction(() => document.querySelector('[data-wallet-label]')?.textContent === 'seco…llet');
  };
  const heldResponse = async (fixturePage, path, value, method = 'GET') => {
    const gate = deferred(); const started = deferred(); let request;
    await fixturePage.route(url => url.pathname === path, async route => {
      if (request || route.request().method() !== method) { await route.fallback(); return; }
      request = route.request(); started.resolve(); await gate.promise; await route.fulfill({ json: value });
    });
    return {
      started: started.promise,
      request: () => request,
      async release() {
        const previous = await fixturePage.evaluate(({ path, method }) => window.fixtureReads.filter(item => item.path === path && item.method === method).length, { path, method });
        const response = fixturePage.waitForResponse(value => value.request() === request);
        gate.resolve(); await (await response).finished();
        await fixturePage.waitForFunction(({ path, method, previous }) => window.fixtureReads.filter(item => item.path === path && item.method === method).length > previous, { path, method, previous });
        await drain(fixturePage);
      }
    };
  };
  const switchAccount = async (fixturePage, action = 'logout') => {
    await fixturePage.evaluate(() => { location.hash = 'settings'; });
    if (action === 'delete-account') fixturePage.once('dialog', dialog => dialog.accept());
    await fixturePage.locator(`main [data-action="${action}"]`).click();
    await fixturePage.locator('main [data-action="wallet"]').waitFor();
    assert.equal(observedRequests.find(item => item.pathname === (action === 'logout' ? '/api/auth/logout' : '/api/me') && item.method === (action === 'logout' ? 'POST' : 'DELETE'))?.account, firstUser.id);
    bots = [{ id: 'second-only', name: 'Second account configuration', coin: 'BTC', status: 'configured' }];
    await signInSecond(fixturePage);
  };
  const assertSecond = async fixturePage => {
    assert.equal(await fixturePage.locator('[data-wallet-label]').innerText(), 'seco…llet');
    await fixturePage.evaluate(() => { location.hash = 'bots'; });
    await fixturePage.waitForFunction(() => document.querySelector('#page-label').textContent === 'My bots');
    assert.doesNotMatch(await fixturePage.locator('main').innerText(), /Previous account private/);
    assert.equal(await fixturePage.locator('[data-action="more-bots"]').count(), 0);
  };

  for (const path of ['/api/me', '/api/bots']) {
    const { page: fixturePage } = await freshPage();
    const old = await heldResponse(fixturePage, path, path === '/api/me' ? accountSnapshot(firstUser) : { bots: [{ id: 'old-private', name: 'Previous account private configuration', coin: 'SOL', status: 'configured' }], nextPage: 2 });
    await fixturePage.goto(`${origin}/#settings`); await old.started;
    assert.equal(old.request().headers()['x-oraclebot-account'], path === '/api/me' ? undefined : firstUser.id);
    bots = [{ id: 'second-only', name: 'Second account configuration', coin: 'BTC', status: 'configured' }];
    await signInSecond(fixturePage); await old.release(); await assertSecond(fixturePage);
    assert.match(await fixturePage.locator('main').innerText(), /Second account configuration/);
    await fixturePage.close();
  }
  console.log('PASS initial identity and first bot reads cannot overwrite a newer wallet sign-in');

  for (const [path, action] of [['/api/me', 'logout'], ['/api/bots', 'logout'], ['/api/me', 'delete-account'], ['/api/bots', 'delete-account']]) {
    const { page: fixturePage } = await freshPage(); botsUnavailable = true;
    await ready(fixturePage, 'bots'); botsUnavailable = false;
    const old = await heldResponse(fixturePage, path, path === '/api/me' ? accountSnapshot(firstUser) : { bots: [{ id: 'old-private', name: 'Previous account private configuration', coin: 'SOL', status: 'configured' }], nextPage: 2 });
    await fixturePage.locator('[data-action="refresh-bots"]').click(); await old.started;
    assert.equal(old.request().headers()['x-oraclebot-account'], firstUser.id);
    await switchAccount(fixturePage, action); await old.release(); await assertSecond(fixturePage);
    assert.match(await fixturePage.locator('main').innerText(), /Second account configuration/);
    await fixturePage.close();
  }
  console.log('PASS held account refreshes stay invalid after sign-out, deletion and a second wallet sign-in');

  {
    const { page: fixturePage } = await freshPage(); botsUnavailable = true;
    await ready(fixturePage, 'bots');
    const ended = await heldResponse(fixturePage, '/api/me', accountSnapshot(null));
    await fixturePage.locator('[data-action="refresh-bots"]').click(); await ended.started;
    await fixturePage.evaluate(() => { location.hash = 'settings'; });
    await fixturePage.waitForSelector('.settings-value');
    assert.equal(await fixturePage.locator('.settings-value').innerText(), firstUser.wallet);
    await ended.release();
    assert.equal(await fixturePage.locator('[data-wallet-label]').innerText(), 'Connect wallet');
    assert.equal(await fixturePage.locator('.settings-value').count(), 0);
    assert.equal(await fixturePage.locator('main [data-action="wallet"]').count(), 1);
    await fixturePage.close();
  }
  console.log('PASS a confirmed expired session immediately removes the previous account’s private view');

  {
    const { page: fixturePage, blockedRequests } = await freshPage(); await ready(fixturePage, 'pricing');
    const old = await heldResponse(fixturePage, '/api/billing/portal', { url: 'https://billing.stripe.com/p/session/synthetic-old-account' }, 'POST');
    await fixturePage.locator('main [data-action="portal"]').click(); await old.started;
    assert.equal(old.request().headers()['x-oraclebot-account'], firstUser.id);
    await switchAccount(fixturePage); await old.release();
    assert.deepEqual(blockedRequests, []);
    assert.equal(new URL(fixturePage.url()).origin, origin); await assertSecond(fixturePage);
    await fixturePage.close();
  }
  console.log('PASS a delayed billing response cannot redirect a signed-out or replacement account');

  {
    const { page: fixturePage } = await freshPage(); await ready(fixturePage, 'backtest');
    await fixturePage.route('**/api/backtests', route => route.fulfill({ json: { metrics: { total_return: 0.1 } } }));
    const old = await heldResponse(fixturePage, '/api/me', { ...accountSnapshot(firstUser), usage: { policy: { ...plans[0], name: 'Previous account private allowance' }, bots: 99, backtests: 99 } });
    await fixturePage.locator('#backtest-form button[type="submit"]').click(); await old.started;
    assert.equal(old.request().headers()['x-oraclebot-account'], firstUser.id);
    await switchAccount(fixturePage); await old.release();
    await fixturePage.evaluate(() => { location.hash = 'pricing'; });
    await fixturePage.waitForSelector('.usage-panel');
    assert.match(await fixturePage.locator('.usage-panel').innerText(), /3 of 10 backtests/);
    assert.doesNotMatch(await fixturePage.locator('main').innerText(), /Previous account private allowance/);
    await fixturePage.close();
  }
  for (const kind of ['backtest', 'create', 'pause']) {
    const { page: fixturePage } = await freshPage();
    bots = [{ id: 'first-only', name: 'First account configuration', coin: 'SOL', status: 'configured' }];
    await ready(fixturePage, kind === 'backtest' ? 'backtest' : 'bots');
    const path = kind === 'backtest' ? '/api/backtests' : kind === 'create' ? '/api/bots' : '/api/bots/first-only';
    const old = await heldResponse(fixturePage, path, kind === 'backtest' ? { metrics: { total_return: 0.99 } } : { saved: true }, kind === 'pause' ? 'PATCH' : 'POST');
    if (kind === 'backtest') await fixturePage.locator('#backtest-form button[type="submit"]').click();
    else if (kind === 'pause') await fixturePage.locator('[data-bot-status="paused"]').click();
    else {
      await fixturePage.locator('main [data-action="new-bot"]').first().click(); await fixturePage.locator('#bot-form [name="name"]').fill('Pending first-account configuration');
      await fixturePage.locator('#bot-form button[type="submit"]').click();
      await fixturePage.locator('#bot-dialog [data-close-dialog]').click();
    }
    await old.started; assert.equal(old.request().headers()['x-oraclebot-account'], firstUser.id);
    await switchAccount(fixturePage);
    const accountReads = observedRequests.filter(item => item.pathname === '/api/me' && item.method === 'GET').length;
    await old.release();
    assert.equal(new URL(fixturePage.url()).hash, '#settings');
    assert.equal(observedRequests.filter(item => item.pathname === '/api/me' && item.method === 'GET').length, accountReads);
    assert.doesNotMatch(await fixturePage.locator('#toast').innerText(), /Paper configuration saved|Configuration paused/);
    await assertSecond(fixturePage); await fixturePage.close();
  }
  console.log('PASS old backtest usage, backtest results, bot creation and pause completions cannot affect a replacement account');

  {
    const { page: fixturePage, diagnostics } = await freshPage();
    let attempts = 0;
    const privateDiagnostic = { error: 'service_unavailable', message: 'PRIVATE diagnostic must not be logged' };
    await fixturePage.route('**/api/me', route => ++attempts === 1 ? route.fulfill({ status: 503, json: privateDiagnostic }) : route.continue());
    await fixturePage.goto(`${origin}/#bots`); await fixturePage.locator('[data-action="refresh-account"]').waitFor();
    assert.match(await fixturePage.locator('main').innerText(), /sign-in and saved workspace are unknown/i);
    assert.doesNotMatch(await fixturePage.locator('main').innerText(), /Your first configuration will appear here/);
    assert.equal(await fixturePage.locator('#nav-bot-count').innerText(), '—');
    assert.deepEqual(diagnostics.filter(message => message.type === 'warning').map(message => message.text), ['Oraclebot account refresh unavailable']);
    for (const privateValue of Object.values(privateDiagnostic)) assert.ok(diagnostics.every(message => !message.text.includes(privateValue)), 'Private response fields must stay out of every console level');
    await fixturePage.evaluate(() => { location.hash = 'settings'; });
    await fixturePage.waitForFunction(() => document.querySelector('#page-label').textContent === 'Settings & account');
    assert.equal(await fixturePage.locator('main [data-action="wallet"]').count(), 0);
    assert.doesNotMatch(await fixturePage.locator('main').innerText(), /Connect a Solana wallet|Sign in with your wallet/);
    await fixturePage.locator('.account-notice [data-action="refresh-account"]').click();
    await fixturePage.waitForFunction(() => document.querySelector('[data-wallet-label]')?.textContent === 'fixt…llet');
    assert.match(await fixturePage.locator('main').innerText(), /Signed in using a verified wallet signature/);
    await fixturePage.close();
  }
  console.log('PASS an unavailable identity stays unknown, emits only a fixed private diagnostic and supports retry');

  for (const stage of ['connect', 'sign']) for (const nullish of ['null', 'undefined']) {
    const { page: fixturePage } = await freshPage(); fixtureUser = null;
    await fixturePage.goto(`${origin}/#settings`); await fixturePage.locator('main [data-action="wallet"]').waitFor();
    await fixturePage.evaluate(({ stage, nullish }) => { window[stage === 'connect' ? 'rejectConnect' : 'rejectSign'] = true; window.rejectionValue = nullish === 'null' ? null : undefined; }, { stage, nullish });
    await fixturePage.locator('main [data-action="wallet"]').click(); await fixturePage.locator('[data-provider="phantom"]').click();
    await fixturePage.waitForFunction(() => document.querySelector('#wallet-message').textContent.includes('Something went wrong') && !document.querySelector('[data-provider="phantom"]').disabled);
    assert.equal(observedRequests.filter(item => item.pathname === '/api/auth/verify').length, 0);
    assert.equal(await fixturePage.evaluate(() => window.fixtureSignatures), stage === 'connect' ? 0 : 1);
    await fixturePage.close();
  }
  console.log('PASS null and undefined wallet rejections stay recoverable and never reach account verification');
  assert.deepEqual(errors, []);
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
