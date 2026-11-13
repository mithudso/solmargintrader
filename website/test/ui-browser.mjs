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
const plans = [
  { id: 'starter', name: 'Starter', monthlyUsd: 9.99, botLimit: 3, backtestsPerDay: 10 },
  { id: 'advanced', name: 'Advanced', monthlyUsd: 29.99, botLimit: 10, backtestsPerDay: null },
  { id: 'unlimited', name: 'Unlimited', monthlyUsd: 49.99, botLimit: null, backtestsPerDay: null },
];
const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  if (pathname.startsWith('/api/')) {
    const data = pathname === '/api/config' ? { coins: ['SOL', 'BTC'], trialDays: 7, billingConfigured, plans, engineConfigured: false }
      : pathname === '/api/me' ? { user: { id: 'fixture', wallet: 'fixture-wallet' }, subscription: { status: 'trialing', entitled: true, plan: plans[0] }, portalAvailable: true, usage: { policy: plans[0], bots: 2, backtests: 7, reservedBacktests: 0 } }
        : pathname === '/api/bots' ? (botsUnavailable ? { error: 'service_unavailable' } : paginatedBots ? (new URL(request.url, 'http://localhost').searchParams.get('page') === '1' ? { bots: [{ id: 'second', name: 'Second page configuration', coin: 'SOL', status: 'configured' }], nextPage: null } : { bots: [{ id: 'first', name: 'First page configuration', coin: 'SOL', status: 'configured' }], nextPage: 1 }) : { bots })
          : pathname === '/api/strategies' ? { strategies: [{ id: 'rsi', name: 'RSI' }] }
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
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
