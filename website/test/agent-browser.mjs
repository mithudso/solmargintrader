/** Real Chrome against isolated HTTP/wallet fixtures. No provider or real key calls. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const publicRoot = new URL('../public/', import.meta.url);
const types = { js: 'text/javascript', html: 'text/html', css: 'text/css', svg: 'image/svg+xml', json: 'application/json' };
const requestId = 'A'.repeat(43);
const wallet = '11111111111111111111111111111111';
const grantId = '00000000-0000-4000-8000-000000000001';
const hostileName = '<img src=x onerror="window.hostileAgentRan=true"> Fixture agent';
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
let origin;
let fixture;
function reset(options = {}) {
  fixture = { signedIn: true, trading: true, grants: [], challengeBodies: [], approvals: [], walletCalls: [], authorizationGets: 0, grantGets: 0, logoutPosts: 0, ...options };
}
async function body(request) { let text = ''; for await (const part of request) text += part; return JSON.parse(text || '{}'); }
const json = (response, value, status = 200) => { response.writeHead(status, { 'Content-Type': 'application/json' }); response.end(JSON.stringify(value)); };
const server = createServer(async (request, response) => {
  const url = new URL(request.url, origin || 'http://127.0.0.1'); const path = url.pathname; const active = fixture;
  try {
    if (path.startsWith('/api/')) {
      if (path === '/api/me') { if (request.method === 'DELETE') active.deleteRequests = (active.deleteRequests || 0) + 1; return json(response, { user: active.signedIn ? { id: 'fixture-user', wallet } : null, subscription: null }); }
      if (path === '/api/config') return json(response, { coins: ['SOL', 'BTC'], trialDays: 7, plans: [], billingConfigured: false });
      if (path === '/api/bots') return json(response, { bots: [], nextPage: null });
      if (path === '/api/strategies') return json(response, { strategies: [{ id: 'rsi', name: 'RSI' }] });
      if (path === '/api/agent/authorization' && request.method === 'GET') {
        active.authorizationGets++; active.authorizationStarted?.resolve(); await active.holdAuthorization?.promise;
        return json(response, { requestId, client: { id: 'fixture-client', name: hostileName, redirectOrigin: origin, redirectUri: `${origin}/agent-callback?existing=one` }, wallet, scopes: active.trading ? ['status:read', 'trade:prepare', 'trade:submit'] : ['status:read'], resource: `${origin}/mcp`, expiresAt: Math.floor(Date.now() / 1000) + 600, requiresPolicyProof: active.trading });
      }
      if (path === '/api/agent/authorization/challenge') {
        const input = await body(request); active.challengeBodies.push(input);
        const policy = { ...input.policy, venues: [...input.policy.venues].sort(), assets: [...input.policy.assets].sort() };
        if (policy.products) policy.products = [...policy.products].sort();
        if (active.tamperPolicy) policy.maxTotalUsd += 1;
        if (active.tamperProduct) policy.products = ['perpetual', 'spot'];
        if (active.tamperLeverage) policy.maxLeverage = 5;
        if (active.unknownPolicyField) policy.wallet = 'another-wallet';
        if (active.legacyPolicyResponse) { delete policy.version; delete policy.products; delete policy.maxLeverage; }
        return json(response, { challengeId: grantId, message: `Oraclebot agent trading preauthorization\nWallet: ${wallet}\nPolicy: ${JSON.stringify(policy)}`, expiresAt: Math.floor(Date.now() / 1000) + 180, policy });
      }
      if (path === '/api/agent/authorization' && request.method === 'POST') {
        active.approvals.push(await body(request)); active.approvalStarted?.resolve(); await active.holdApproval?.promise;
        return json(response, { redirectTo: `${origin}/${active.badRedirect ? 'unexpected-path' : 'agent-callback'}?existing=one&${active.approvals.at(-1).approve ? 'code=synthetic-authorization-code' : 'error=access_denied'}&state=synthetic-state` });
      }
      if (path === '/api/agent/grants') {
        active.grantGets++; active.grantsStarted?.resolve(); await active.holdGrants?.promise;
        return json(response, { grants: active.grants });
      }
      if (path === `/api/agent/grants/${grantId}/revoke`) { active.revoked = true; return json(response, { revoked: true }); }
      if (path === '/api/auth/logout') { active.logoutPosts++; active.logoutStarted?.resolve(); await active.holdLogout?.promise; active.signedIn = false; return json(response, {}); }
      return json(response, { status: 'unavailable', topStrategy: null });
    }
    if (path === '/agent-callback') { response.writeHead(200, { 'Content-Type': 'text/html' }); response.end('<!doctype html><title>Agent returned</title><p>Authorization returned to fixture agent.</p>'); return; }
    const file = new URL(path === '/' ? 'index.html' : `.${path}`, publicRoot);
    assert.ok(fileURLToPath(file).startsWith(fileURLToPath(publicRoot)));
    response.writeHead(200, { 'Content-Type': types[path.split('.').pop()] || 'text/html' }); response.end(await readFile(file));
  } catch { if (!response.headersSent) response.writeHead(500); response.end(); }
});
reset();
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
origin = `http://127.0.0.1:${server.address().port}`;
let browser;
try {
  browser = await chromium.launch({ headless: true, ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}) });
  const page = await browser.newPage(); const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  await page.exposeFunction('recordFixtureWalletCall', kind => {
    assert.ok(kind === 'connect' || kind === 'sign'); fixture.walletCalls.push(kind);
  });
  await page.addInitScript(fixtureWallet => {
    window.fixtureWallet = fixtureWallet; window.fixtureSignatures = []; window.fixtureConnects = 0; window.fixtureConnectReturned = 0; window.fixtureSignReturned = 0;
    window.fixtureFetchStarted = []; window.fixtureJsonReads = [];
    window.fixtureUnhandledRejections = [];
    window.addEventListener('unhandledrejection', () => window.fixtureUnhandledRejections.push(true));
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (resource, options = {}) => {
      const descriptor = { path: new URL(resource, location.href).pathname, method: options.method || 'GET' };
      window.fixtureFetchStarted.push(descriptor);
      const response = await originalFetch(resource, options); const readJSON = response.json.bind(response);
      response.json = async () => { const value = await readJSON(); window.fixtureJsonReads.push(descriptor); return value; };
      return response;
    };
    const provider = {
      publicKey: { toString: () => window.fixtureWallet },
      async connect() { await window.recordFixtureWalletCall('connect'); window.fixtureConnects++; await window.fixtureConnectGate; window.fixtureConnectReturned++; return { publicKey: this.publicKey }; },
      async signMessage(bytes) { await window.recordFixtureWalletCall('sign'); window.fixtureSignatures.push(new TextDecoder().decode(bytes)); await window.fixtureSignGate; if (window.fixtureAfterSignWallet) window.fixtureWallet = window.fixtureAfterSignWallet; window.fixtureSignReturned++; return { signature: new Uint8Array(64).fill(7) }; },
    };
    window.phantom = { solana: provider }; window.solflare = provider;
  }, wallet);
  let navigation = 0;
  const go = async (options = {}, consent = true) => {
    reset(options); await page.goto(`${origin}/?fixture=${++navigation}${consent ? `&agent_request=${requestId}` : ''}#settings`);
    await page.waitForFunction(() => document.querySelector('[data-wallet-label]')?.textContent === '1111…1111');
    if (consent) await page.waitForSelector('#agent-consent-form');
    else await page.waitForSelector('[data-agent-access]');
  };
  const submit = () => page.locator('#agent-consent-form button[type="submit"]').click();

  await go();
  assert.equal(await page.locator('[data-agent-consent] h3').innerText(), `${hostileName} requests access`);
  assert.equal(await page.locator('[data-agent-consent] img').count(), 0);
  assert.equal(await page.evaluate(() => Boolean(window.hostileAgentRan)), false);
  assert.match(await page.locator('[data-agent-access]').innerText(), /do not require repeated wallet approval/);
  assert.match(await page.locator('[data-agent-access]').innerText(), /does not enable execution/);
  assert.equal(await page.getByLabel('Spot (1x)', { exact: true }).isChecked(), true);
  assert.equal(await page.getByLabel('Perpetuals', { exact: true }).isChecked(), false);
  assert.equal(await page.locator('[name="maxLeverage"]').inputValue(), '1');
  assert.equal(await page.locator('[name="maxLeverage"]').isDisabled(), true);
  assert.match(await page.locator('[data-agent-consent]').innerText(), /not collateral/);
  await page.locator('[name="maxTradeUsd"]').fill('0.29'); await page.locator('[name="maxTotalUsd"]').fill('0.57');
  await page.getByLabel('Jupiter', { exact: true }).check(); await page.getByLabel('BTC', { exact: true }).check();
  await page.getByLabel('Perpetuals', { exact: true }).check(); await page.locator('[name="maxLeverage"]').selectOption('3');
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.setViewportSize({ width: 1280, height: 800 });
  await submit(); await page.waitForURL('**/agent-callback?**');
  assert.equal(fixture.challengeBodies.length, 1); assert.equal(fixture.approvals.length, 1);
  assert.deepEqual(fixture.walletCalls, ['connect', 'sign']);
  assert.deepEqual(fixture.challengeBodies[0].policy.venues, ['coinbase', 'jupiter']);
  assert.deepEqual(fixture.challengeBodies[0].policy.assets, ['SOL', 'BTC']);
  assert.equal(fixture.challengeBodies[0].policy.version, 2);
  assert.deepEqual(fixture.challengeBodies[0].policy.products, ['spot', 'perpetual']);
  assert.equal(fixture.challengeBodies[0].policy.maxLeverage, 3);
  assert.equal(fixture.challengeBodies[0].policy.maxTradeUsd, 0.29); assert.equal(fixture.challengeBodies[0].policy.maxTotalUsd, 0.57);
  assert.match(fixture.approvals[0].signature, /^[A-Za-z0-9+/]{86}==$/);
  console.log('PASS bounded trading consent signs once, preserves decimal limits, escapes client text and fits mobile');

  await go({ trading: false });
  assert.equal(await page.locator('[name="maxTradeUsd"]').count(), 0); await submit(); await page.waitForURL('**/agent-callback?**');
  assert.equal(fixture.challengeBodies.length, 0); assert.deepEqual(fixture.approvals, [{ requestId, approve: true }]);
  assert.deepEqual(fixture.walletCalls, []);
  console.log('PASS status-only consent grants no trading policy and needs no wallet signature');

  for (const stage of ['connect', 'signMessage']) {
    for (const rejectedValue of ['null', 'undefined']) {
      await go();
      await page.evaluate(({ stage, rejectedValue }) => {
        window.phantom.solana[stage] = async () => { throw rejectedValue === 'null' ? null : undefined; };
      }, { stage, rejectedValue });
      await submit();
      await page.waitForFunction(() => document.querySelector('#agent-consent-form').getAttribute('aria-busy') === 'false');
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const failure = page.locator('.agent-consent .form-message');
      assert.equal(await failure.isVisible(), true);
      assert.match(await failure.innerText(), /^Authorization could not be completed\./);
      assert.equal(await page.locator('#agent-consent-form').locator('button,input,select,textarea').evaluateAll(controls => controls.filter(control => control.name !== 'maxLeverage').every(control => !control.disabled)), true);
      assert.equal(await page.locator('[name="maxLeverage"]').isDisabled(), true, 'Spot-only consent keeps its new leverage control at 1x');
      assert.equal(await page.locator('[name="maxLeverage"]').inputValue(), '1');
      assert.equal(fixture.challengeBodies.length, stage === 'connect' ? 0 : 1);
      assert.equal(fixture.approvals.length, 0);
      assert.deepEqual(await page.evaluate(() => window.fixtureUnhandledRejections), []);
      assert.deepEqual(errors, []);
      console.log(`PASS ${stage} rejection with ${rejectedValue} shows a failure, restores controls and grants no access without an unhandled rejection`);
    }
  }

  await go(); await page.evaluate(() => { window.fixtureWallet = 'another-wallet'; }); await submit();
  await page.waitForFunction(() => document.querySelector('.agent-consent .form-message').textContent.includes('does not match'));
  assert.equal(fixture.challengeBodies.length, 0); assert.equal(fixture.approvals.length, 0); assert.equal(await page.evaluate(() => window.fixtureSignatures.length), 0);
  await go(); await page.evaluate(() => { window.fixtureAfterSignWallet = 'another-wallet'; }); await submit();
  await page.waitForFunction(() => document.querySelector('.agent-consent .form-message').textContent.includes('wallet changed'));
  assert.equal(fixture.challengeBodies.length, 1); assert.equal(fixture.approvals.length, 0);
  console.log('PASS a mismatched or switched wallet cannot authorize the account');

  await go({ tamperPolicy: true }); await submit();
  await page.waitForFunction(() => document.querySelector('.agent-consent .form-message').textContent.includes('limits changed'));
  assert.equal(await page.evaluate(() => window.fixtureSignatures.length), 0); assert.equal(fixture.approvals.length, 0);
  await go({ badRedirect: true }); await submit();
  await page.waitForFunction(() => document.querySelector('.agent-consent .form-message').textContent.includes('could not be completed'));
  assert.equal(new URL(page.url()).pathname, '/');
  console.log('PASS changed challenge limits and unregistered redirect paths are refused');

  for (const option of ['tamperProduct', 'tamperLeverage', 'unknownPolicyField', 'legacyPolicyResponse']) {
    await go({ [option]: true }); await submit();
    await page.waitForFunction(() => document.querySelector('.agent-consent .form-message').textContent.includes('limits changed'));
    assert.equal(await page.evaluate(() => window.fixtureSignatures.length), 0); assert.equal(fixture.approvals.length, 0);
  }
  console.log('PASS changed products, leverage, unknown fields and downgraded policy versions are refused before signing');

  for (const field of ['products', 'maxLeverage', 'walletProvider']) {
    await go();
    await page.getByLabel('Perpetuals', { exact: true }).check(); await page.locator('[name="maxLeverage"]').selectOption('3');
    await page.evaluate(() => { window.fixtureSignGate = new Promise(resolve => { window.releaseFixtureSign = resolve; }); });
    await submit(); await page.waitForFunction(() => window.fixtureSignatures.length === 1);
    assert.equal(await page.locator('#agent-consent-form input:enabled,#agent-consent-form select:enabled').count(), 0);
    await page.evaluate(changed => {
      if (changed === 'products') document.querySelector('input[name="products"][value="perpetual"]').checked = false;
      if (changed === 'maxLeverage') document.querySelector('[name="maxLeverage"]').value = '5';
      if (changed === 'walletProvider') document.querySelector('[name="walletProvider"]').value = 'solflare';
      window.releaseFixtureSign();
    }, field);
    await page.waitForFunction(() => document.querySelector('.agent-consent .form-message').textContent.includes('limits changed'));
    assert.equal(fixture.approvals.length, 0); assert.deepEqual(fixture.walletCalls, ['connect', 'sign']);
  }
  console.log('PASS product, leverage and provider changes during a held wallet signature cannot issue authorization');

  await go();
  await page.evaluate(() => {
    const original = window.phantom.solana.signMessage;
    window.phantom.solana.signMessage = async function(bytes) { const result = await original.call(this, bytes); bytes[0] ^= 1; return result; };
  });
  await submit();
  await page.waitForFunction(() => document.querySelector('.agent-consent .form-message').textContent.includes('message changed'));
  assert.equal(fixture.approvals.length, 0); assert.deepEqual(fixture.walletCalls, ['connect', 'sign']);
  console.log('PASS the exact message bytes passed to the wallet retain their signed-message hash');

  await go(); await page.evaluate(() => { window.fixtureConnectGate = new Promise(resolve => { window.releaseFixtureConnect = resolve; }); });
  await submit(); await page.waitForFunction(() => window.fixtureConnects === 1);
  assert.equal(await page.locator('#agent-consent-form input:enabled,#agent-consent-form select:enabled').count(), 0);
  await page.evaluate(() => document.querySelector('#agent-consent-form').requestSubmit());
  assert.equal(await page.evaluate(() => window.fixtureConnects), 1);
  await page.evaluate(() => window.releaseFixtureConnect()); await page.waitForURL('**/agent-callback?**');
  assert.equal(fixture.approvals.length, 1);
  console.log('PASS policy and provider controls stay frozen while one consent request is in flight');

  const holdLogout = deferred(); const logoutStarted = deferred();
  await go({ holdLogout, logoutStarted });
  await page.evaluate(() => { window.fixtureConnectGate = new Promise(resolve => { window.releaseFixtureConnect = resolve; }); });
  await submit(); await page.waitForFunction(() => window.fixtureConnects === 1);
  await page.locator('main [data-action="logout"]').click(); await logoutStarted.promise;
  await page.evaluate(() => document.querySelector('#wallet-dialog').showModal());
  await page.locator('[data-provider="solflare"]').click();
  assert.equal(await page.evaluate(() => window.fixtureConnects), 1);
  await page.evaluate(() => document.querySelector('#wallet-dialog').close());
  await page.evaluate(() => window.releaseFixtureConnect());
  await page.waitForFunction(() => window.fixtureConnectReturned === 1);
  // Wait on actual browser work completion, then prove the held HTTP logout has
  // not been needed to invalidate an earlier wallet continuation.
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(await page.evaluate(() => window.fixtureFetchStarted.filter(value => value.path === '/api/agent/authorization/challenge' || value.path === '/api/agent/authorization' && value.method === 'POST').length), 0);
  assert.equal(fixture.challengeBodies.length, 0); assert.equal(fixture.approvals.length, 0);
  await page.evaluate(() => { location.hash = 'overview'; location.hash = 'settings'; });
  await page.waitForFunction(() => document.querySelector('[data-agent-grants]')?.textContent.includes('Sign in with your wallet'));
  holdLogout.resolve(); await page.waitForFunction(() => document.querySelector('main [data-action="logout"]') === null);
  assert.equal(fixture.challengeBodies.length, 0);
  console.log('PASS sign-out immediately invalidates held wallet consent before its HTTP response returns');

  const signLogout = deferred(); const signLogoutStarted = deferred();
  await go({ holdLogout: signLogout, logoutStarted: signLogoutStarted });
  await page.evaluate(() => { window.fixtureSignGate = new Promise(resolve => { window.releaseFixtureSignature = resolve; }); });
  await submit(); await page.waitForFunction(() => window.fixtureSignatures.length === 1);
  await page.locator('main [data-action="logout"]').click(); await signLogoutStarted.promise;
  await page.evaluate(() => window.releaseFixtureSignature());
  await page.waitForFunction(() => window.fixtureSignReturned === 1);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(fixture.approvals.length, 0);
  assert.equal(await page.evaluate(() => window.fixtureFetchStarted.filter(value => value.path === '/api/agent/authorization' && value.method === 'POST').length), 0);
  signLogout.resolve(); await page.waitForFunction(() => document.querySelector('main [data-action="logout"]') === null);
  console.log('PASS a wallet signature completing during sign-out cannot issue agent authorization');

  const holdApproval = deferred(); const approvalStarted = deferred(); const readLogout = deferred(); const readLogoutStarted = deferred();
  await go({ trading: false, holdApproval, approvalStarted, holdLogout: readLogout, logoutStarted: readLogoutStarted });
  await submit(); await approvalStarted.promise;
  await page.locator('main [data-action="logout"]').click(); await readLogoutStarted.promise;
  const approvalResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/agent/authorization' && response.request().method() === 'POST');
  holdApproval.resolve(); await (await approvalResponse).finished();
  await page.waitForFunction(() => window.fixtureJsonReads.some(value => value.path === '/api/agent/authorization' && value.method === 'POST'));
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(new URL(page.url()).pathname, '/');
  readLogout.resolve(); await page.waitForFunction(() => document.querySelector('main [data-action="logout"]') === null);
  console.log('PASS an authorization response arriving during sign-out cannot redirect the previous account');

  const grant = { id: grantId, clientName: hostileName, scopes: ['status:read', 'trade:prepare', 'trade:submit'], policy: { venues: ['coinbase'], assets: ['SOL'], maxTradeUsd: 5, maxTotalUsd: 20 }, createdAt: Math.floor(Date.now() / 1000), expiresAt: Math.floor(Date.now() / 1000) + 1000, revokedAt: null };
  await go({ grants: [grant] }, false); await page.waitForSelector(`[data-grant-id="${grantId}"] button`);
  assert.match(await page.locator(`[data-grant-id="${grantId}"]`).innerText(), /\$5\.00 per trade · \$20\.00 total/);
  await page.getByRole('button', { name: 'Revoke access', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.agent-grant-status').textContent.includes('Access revoked'));
  assert.equal(fixture.revoked, true); assert.equal(await page.getByRole('button', { name: 'Revoke access', exact: true }).count(), 0);
  console.log('PASS agent history displays limits and immediately exposes revocation without claiming order cancellation');

  const holdGrants = deferred(); const grantsStarted = deferred();
  await go({ holdGrants, grantsStarted, grants: [{ ...grant, clientName: 'Previous account private agent' }] }, false); await grantsStarted.promise;
  await page.locator('main [data-action="logout"]').click(); await page.waitForFunction(() => document.querySelector('main [data-action="logout"]') === null);
  const grantsResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/agent/grants');
  const expectedGrantReads = fixture.grantGets;
  holdGrants.resolve(); await (await grantsResponse).finished();
  await page.waitForFunction(expected => window.fixtureJsonReads.filter(value => value.path === '/api/agent/grants').length === expected, expectedGrantReads);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.doesNotMatch(await page.locator('main').innerText(), /Previous account private agent/);
  console.log('PASS pending grant responses cannot restore a previous account’s private authorization history');
  assert.deepEqual(errors, []);
} finally {
  for (const key of ['holdLogout', 'holdGrants', 'holdAuthorization', 'holdApproval']) fixture[key]?.resolve();
  await browser?.close(); await new Promise(resolve => server.close(resolve));
}
