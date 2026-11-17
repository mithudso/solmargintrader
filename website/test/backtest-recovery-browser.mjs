/** Real browser + Worker/D1 contracts. All accounts, engine data and network are isolated fixtures. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

// Running this same test from the immutable baseline also exercises its actual assets/Worker.
const source = pathToFileURL(`${process.cwd()}/`);
const { default: worker } = await import(new URL('src/worker.js', source));
const { environment, seedUser, request, at } = await import(new URL('test/helpers/d1.js', source));
const env = environment();
const owner = await seedUser(env); const other = await seedUser(env);
for (const user of [owner, other]) env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id) VALUES (?,?,'active',?,?,'starter')").run(user.id, `sub_${user.id}`, at() + 86400, at());
const jobs = new Map();
let queued = false;
env.ENGINE_TOKEN = 'fixture-engine-token-at-least-32-bytes';
env.ENGINE_SERVICE = { async fetch(req) {
  const input = req.method === 'POST' ? await req.json() : null;
  const id = input?.id || new URL(req.url).pathname.split('/').at(-1);
  if (input && !jobs.has(id)) {
    const stable = Object.fromEntries(Object.keys(input.request).sort().map(key => [key, input.request[key]]));
    const requestHash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(stable)))).toString('hex');
    jobs.set(id, { id, requestHash, request: input.request, status: queued ? 'queued' : 'complete', createdAt: at(), updatedAt: at() });
  }
  const job = jobs.get(id);
  return Response.json({ ...job, ...(job.status === 'complete' ? { result: { status: 'complete', ...job.request, metrics: { total_return: 0.1 }, equity: [] } } : {}) });
} };
let user = owner;
let postCount = 0;
const call = async (pathname, options = {}) => worker.fetch(request(pathname, { cookie: user.cookie, ...options }), env);
const types = { js: 'text/javascript', html: 'text/html', css: 'text/css', svg: 'image/svg+xml', json: 'application/json' };
const server = createServer(async (req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  try {
    let response;
    if (pathname === '/api/config') response = Response.json({ durableBacktests: true, coins: ['SOL', 'BTC'], plans: [] });
    else if (pathname === '/api/strategies') response = Response.json({ strategies: [{ id: 'rsi', name: 'RSI' }] });
    else if (pathname.startsWith('/api/backtest-jobs')) {
      let body = ''; for await (const part of req) body += part;
      if (req.method === 'POST') postCount++;
      response = await call(pathname, { method: req.method, ...(body ? { body: JSON.parse(body) } : {}), headers: { 'X-Oraclebot-Account': req.headers['x-oraclebot-account'] || '' } });
    } else if (pathname === '/api/me') response = Response.json({ user: { id: user.id, wallet: 'fixture-wallet' }, usage: null });
    else if (pathname.startsWith('/api/')) response = Response.json({ bots: [], articles: [] });
    if (response) { res.writeHead(response.status, { 'Content-Type': 'application/json' }); res.end(await response.text()); return; }
    const resource = new URL(pathname === '/' ? 'public/index.html' : `public/.${pathname}`, source);
    assert.ok(resource.href.startsWith(new URL('public/', source).href));
    res.writeHead(200, { 'Content-Type': types[pathname.split('.').pop()] || 'text/html' }); res.end(await readFile(resource));
  } catch { res.writeHead(500); res.end('fixture_error'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
try {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}) });
  const page = await browser.newPage(); const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  let visits = 0;
  const ready = async () => {
    await page.goto(`${origin}/?account=${user.id}&visit=${++visits}#backtest`);
    await page.waitForFunction(() => document.querySelector('#backtest-form [name="strategy"]')?.value === 'rsi' && document.querySelector('[data-wallet-label]')?.textContent === 'fixt…llet');
  };
  let loseReply = true;
  await page.route('**/api/backtest-jobs', async route => {
    if (route.request().method() !== 'POST' || !loseReply) return route.continue();
    loseReply = false; postCount++;
    const response = await call('/api/backtest-jobs', { method: 'POST', body: route.request().postDataJSON(), headers: { 'X-Oraclebot-Account': user.id } });
    assert.equal(response.status, 202); await response.json();
    await route.abort('failed'); // The real Worker committed the calculation, but its reply was lost.
  });
  await ready();
  await page.locator('#backtest-form [name="capital"]').fill('1234');
  await page.locator('#backtest-form button[type="submit"]').click();
  await page.waitForFunction(() => document.querySelector('#backtest-message').textContent && !document.querySelector('#backtest-form button[type="submit"]').disabled);
  assert.equal(jobs.size, 1);
  user = other; await ready();
  assert.equal(await page.locator('#backtest-form [name="capital"]').inputValue(), '1000', 'a replacement account must not see a private pending experiment');
  user = owner; await ready();
  assert.equal(await page.locator('#backtest-form [name="capital"]').inputValue(), '1234', 'reload must restore the exact pending request');
  assert.equal(await page.locator('#backtest-form [name="coin"]').isDisabled(), true);
  assert.match(await page.locator('#backtest-form button[type="submit"]').innerText(), /Recover/);
  await page.locator('#backtest-form button[type="submit"]').click();
  await page.waitForFunction(() => document.querySelector('#backtest-output').textContent.includes('Results, with context'));
  await page.waitForFunction(() => !document.querySelector('#backtest-form button[type="submit"]').disabled);
  assert.equal(jobs.size, 1); assert.equal(env.sqlite.prepare("SELECT COUNT(*) AS n FROM backtest_usage WHERE state='complete'").get().n, 1);
  assert.equal(await page.locator('#backtest-form [name="coin"]').isDisabled(), false);
  await page.locator('#backtest-form button[type="submit"]').click();
  await page.waitForFunction(() => document.querySelector('#backtest-form button[type="submit"]').disabled === false);
  assert.equal(jobs.size, 2, 'a deliberate new experiment after a known terminal result gets a new identity');
  assert.equal(env.sqlite.prepare("SELECT COUNT(*) AS n FROM backtest_usage WHERE state='complete'").get().n, 2);
  console.log('PASS lost acceptance reply + reload + account replacement recover one job and one credit; a deliberate later run stays available');
  queued = true;
  let loseStatus = true;
  await page.route('**/api/backtest-jobs/*', async route => {
    if (!loseStatus) return route.continue();
    loseStatus = false;
    const pathname = new URL(route.request().url()).pathname;
    jobs.get(pathname.split('/').at(-1)).status = 'complete';
    assert.equal((await call(pathname, { headers: { 'X-Oraclebot-Account': user.id } })).status, 200);
    await route.abort('failed');
  });
  await page.locator('#backtest-form button[type="submit"]').click();
  await page.waitForFunction(() => /Recover the saved/.test(document.querySelector('#backtest-message').textContent) && !document.querySelector('#backtest-form button[type="submit"]').disabled);
  const acceptedPosts = postCount;
  await ready();
  await page.locator('#backtest-form button[type="submit"]').click();
  await page.waitForFunction(() => document.querySelector('#backtest-output').textContent.includes('Results, with context'));
  assert.equal(postCount, acceptedPosts, 'a known job is recovered by GET after a polling failure');
  assert.equal(jobs.size, 3);
  console.log('PASS lost polling reply retains the known job and recovers by read without another submission');
  await page.addInitScript(() => { Storage.prototype.setItem = () => { throw new DOMException('fixture storage disabled', 'SecurityError'); }; });
  await ready(); const before = postCount;
  await page.locator('#backtest-form button[type="submit"]').click();
  await page.waitForFunction(() => /recovery|storage/i.test(document.querySelector('#backtest-message').textContent));
  assert.equal(postCount, before, 'a calculation must not be submitted without a durable recovery identity');
  assert.deepEqual(errors, []);
  console.log('PASS unavailable browser storage refuses before quota or engine writes');
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
  env.sqlite.close();
}
