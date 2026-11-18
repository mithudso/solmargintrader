#!/usr/bin/env node
/** Real Chrome, real native messaging, and stubbed public GUM data in a disposable profile. */
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { findChromeForTesting, launch } from '../e2e/lib/cdp.mjs';
import { isolateTargets } from '../e2e/lib/isolation.mjs';
import { createApiServer } from './api-server.js';
import { createNodeDeps } from './deps.js';
import { installZecNativeHost } from './zec-native-install.js';
import { requestZecChrome } from './zec-transport.js';

const execute = promisify(execFile);
const EXT = fileURLToPath(new URL('../', import.meta.url));
const CHROME = process.env.CHROME || findChromeForTesting();
const GUM = 'https://api.gum.ag';
const MARK = 461.25;
const PAPER_ENTRY = 459;
const API_TOKEN = randomUUID();

function gumResponse(request, stale) {
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== GUM) return undefined;
  const timestamp = Math.floor(Date.now() / 1000);
  if (url.pathname === '/app/perps/markets') {
    return [{
      symbol: 'ZEC', timestamp: timestamp - (stale ? 60 : 0), markPrice: MARK, maxLeverage: 25, takerFeeBps: 5, makerFeeBps: 2,
      liquidationFeeBps: 100, stepSize: 0.01,
      riskTiers: [{ maintenanceMarginRatioBps: 25, notionalCap: 100_000 }],
      orderLimitConfig: { market: { maxOpenOrderNotional: 100_000, minOrderNotional: 10, maxOpenOrderQty: 100 } },
    }];
  }
  if (url.pathname === '/app/perps/fundingRate/ZEC') {
    return { symbol: 'ZEC', rateBps1h: 0, fundingUpdateTimestamp: timestamp };
  }
  if (url.pathname === '/app/perps/ohlcv/ZEC' && url.searchParams.get('interval') === '1m') {
    const from = Number(url.searchParams.get('from'));
    const to = Number(url.searchParams.get('to'));
    if (!Number.isSafeInteger(from) || to - from !== 3600) return undefined;
    return Array.from({ length: 60 }, (_, i) => ({
      s: 'ZEC', i: '1m', t: (from + i * 60) * 1000, T: (from + (i + 1) * 60) * 1000,
      o: 460, h: 462, l: 459, c: MARK,
    }));
  }
  return undefined;
}

async function installFakeClaude(root) {
  const bin = path.join(root, 'bin');
  const entry = path.join(bin, 'fake-claude.mjs');
  await mkdir(bin, { mode: 0o700 });
  const shellQuote = value => "'" + value.replaceAll("'", "'\\''") + "'";
  await writeFile(path.join(bin, 'claude'),
    `#!/bin/sh\nexec ${shellQuote(process.execPath)} ${shellQuote(entry)} "$@"\n`, { mode: 0o700 });
  await writeFile(entry, `
    import assert from 'node:assert/strict';
    import { existsSync } from 'node:fs';
    const args = process.argv.slice(2);
    const value = flag => args[args.indexOf(flag) + 1];
    for (const flag of ['--print', '--strict-mcp-config', '--no-session-persistence']) assert.ok(args.includes(flag));
    assert.equal(value('--agent'), 'zec');
    assert.equal(value('--output-format'), 'json');
    assert.equal(value('--tools'), '');
    assert.equal(value('--setting-sources'), 'project');
    assert.deepEqual(JSON.parse(value('--mcp-config')), { mcpServers: {} });
    assert.deepEqual(JSON.parse(value('--settings')), { disableAllHooks: true });
    assert.ok(existsSync('.claude/agents/zec.md'), 'Helper must start in the project with the canonical agent');
    let input = '';
    for await (const chunk of process.stdin) input += chunk;
    const { question, snapshot } = JSON.parse(input.trim().split('\\n').at(-1));
    assert.equal(question, 'How should I proceed in this fixture?');
    assert.equal(snapshot.origin, 'chrome-extension');
    assert.equal(snapshot.source.markPrice, ${MARK});
    assert.equal(snapshot.paper.position.side, 'short');
    assert.deepEqual(JSON.parse(value('--json-schema')).properties.snapshotId.enum, [snapshot.id]);
    console.log(JSON.stringify({ type: 'result', subtype: 'success', is_error: false, structured_output: {
      snapshotId: snapshot.id, decision: 'OBSERVE', rationale: 'Fixture response from simulated Claude Code.',
      invalidation: 'The supplied market or paper position changes.',
    } }));
  `);
  return bin;
}

async function verify() {
  const root = await mkdtemp('/tmp/smt-zec-e2e-');
  let browser, server, isolation;
  const watchdog = setTimeout(async () => {
    console.error('Zec browser check timed out');
    server?.closeAllConnections();
    await browser?.close().catch(() => {});
    await rm(root, { recursive: true, force: true }).catch(() => {});
    process.exit(1);
  }, 45_000);
  watchdog.unref();
  const requests = [];
  let interceptFailure;
  let stale = false;
  try {
    browser = await launch({
      chrome: CHROME,
      extension: EXT,
      noSandbox: process.env.E2E_NO_SANDBOX === '1',
      beforeLoad: async client => {
        isolation = await isolateTargets(client, {
          onEvent(message) {
            if (message.method !== 'Fetch.requestPaused') return;
            const { requestId, request } = message.params;
            requests.push({ method: request.method, url: new URL(request.url).pathname });
            const response = gumResponse(request, stale);
            const fetchCommand = response
              ? ['Fetch.fulfillRequest', {
                  requestId, responseCode: 200, responseHeaders: [{ name: 'content-type', value: 'application/json' },
                    { name: 'access-control-allow-origin', value: '*' }],
                  body: Buffer.from(JSON.stringify(response)).toString('base64'),
                }]
              : ['Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' }];
            client.call(...fetchCommand, message.sessionId).catch((error) => { interceptFailure = error; });
          },
        });
      },
    });
    const { endpoint } = await installZecNativeHost({
      extensionId: browser.extensionId,
      directory: path.join(browser.profile, 'NativeMessagingHosts'),
      endpoint: path.join(root, 'ipc', 'chrome.sock'),
    });
    const env = { SOLMARGIN_ZEC_SOCKET: endpoint };
    const cli = async (...args) => {
      const { stdout } = await execute(process.execPath, [path.join(EXT, 'tools/cli.js'), ...args, '--ephemeral', '--json'],
        { env, timeout: 15_000 });
      return JSON.parse(stdout);
    };

    server = createApiServer({
      deps: await createNodeDeps({ ephemeral: true, quiet: true, zecRequest: (name, params) => requestZecChrome(name, params, { env }) }),
      token: API_TOKEN,
    });
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    const api = async (command, opts = {}) => {
      const { method = 'GET', token = API_TOKEN, origin, body } = opts;
      const response = await fetch(`http://127.0.0.1:${server.address().port}/v1/${command}`, {
        method,
        headers: { authorization: `Bearer ${token}`, ...(origin ? { origin } : {}), ...(body ? { 'content-type': 'application/json' } : {}) },
        body: body ? JSON.stringify(body) : undefined,
        signal: AbortSignal.timeout(15_000),
      });
      return { status: response.status, body: await response.json() };
    };
    assert.equal((await api('zecSnapshot', { token: '' })).status, 401);
    assert.equal((await api('zecSnapshot', { origin: 'https://example.test' })).status, 403);
    assert.equal((await api('zecSnapshot')).status, 503);

    const origin = `chrome-extension://${browser.extensionId}`;
    const { targetId } = await browser.call('Target.createTarget', { url: `${origin}/src/ui/dashboard.html` });
    const session = await browser.attach(targetId);
    const evaluate = expression => browser.evaluate(session, expression);
    assert.ok(await browser.waitFor(() => evaluate('!!document.querySelector("#zecAdvisor") && !!chrome.runtime?.id').catch(() => false)));
    for (const source of ['src/bg/service-worker.js', 'src/bg/zec-advisory.js', 'src/ui/dashboard.js']) {
      const actual = await evaluate(`fetch(chrome.runtime.getURL(${JSON.stringify(source)})).then(response => response.text())`);
      assert.equal(actual, await readFile(path.join(EXT, source), 'utf8'));
    }

    // Plant a paper observation through the real IndexedDB API in this disposable
    // origin. There is no paper runner or funded state in this test.
    const openedAt = Math.floor(Date.now() / 1000) - 60;
    await evaluate(`(async () => {
      const { openWorkbenchStore, paperMarketKey } = await import(chrome.runtime.getURL('src/perps/workbench-store.js'));
      const db = await openWorkbenchStore();
      await db.update(paperMarketKey('GUM', 'ZEC'), () => ({
        account: { running: true, lastPoint: ${openedAt + 5},
          broker: { position: { direction: -1, openedAt: ${openedAt}, entry: ${PAPER_ENTRY}, quantity: 3,
            extra: 'must-not-leave-the-browser' } } },
        trades: [],
      }));
      db.close();
    })()`);

    const message = type => evaluate(`chrome.runtime.sendMessage(${JSON.stringify({ type })})`);
    const before = (await message('zecAdvisories')).result.bridge;
    assert.deepEqual(before, { enabled: false, connected: false, issue: null });
    const gridState = () => evaluate('chrome.storage.local.get(["config", "runtime", "secrets", "lastTick"])');
    const gridBefore = await gridState();

    await evaluate('document.getElementById("zecAdvisor").open = true');
    assert.ok(await browser.waitFor(() => evaluate('!document.getElementById("zecBridgeToggle").disabled && document.getElementById("zecBridgeStatus").textContent.includes("disabled")')));
    await evaluate('document.getElementById("zecBridgeToggle").click()');
    assert.ok(await browser.waitFor(async () => {
      const value = await message('zecAdvisories');
      return value.ok && value.result.bridge.connected;
    }), 'Chrome never received the native readiness handshake');

    const { snapshot } = await cli('zecSnapshot');
    assert.equal(snapshot.origin, 'chrome-extension');
    assert.equal(snapshot.source.status, 'ok');
    assert.equal(snapshot.source.markPrice, MARK);
    assert.equal(snapshot.source.providerAt !== null, true);
    assert.equal(snapshot.closedCandles.status, 'ok');
    assert.equal(snapshot.closedCandles.rows.length, 12);
    assert.equal(snapshot.closedCandles.rows.at(-1).close, MARK);
    assert.equal(snapshot.engine.mode, 'dry-run');
    assert.equal(snapshot.engine.armed, false);
    assert.equal(snapshot.paper.running, true);
    assert.deepEqual(snapshot.paper.position, { side: 'short', openedAt: new Date(openedAt * 1000).toISOString(), entryPrice: PAPER_ENTRY });

    const viaApi = await api('zecSnapshot');
    const apiSnapshot = viaApi.body.result?.snapshot;
    assert.equal(viaApi.status, 200);
    assert.equal(apiSnapshot?.source.markPrice, MARK);
    assert.deepEqual(apiSnapshot.paper.position, snapshot.paper.position);
    assert.equal((await api('zecBridge', { method: 'POST', body: { enabled: false } })).status, 403);
    assert.equal((await api('zecAdvice')).status, 405);

    const advice = {
      snapshotId: snapshot.id,
      decision: 'OBSERVE',
      rationale: 'E2E: watch this paper position with stubbed market data.',
      invalidation: 'GUM history or the paper position changes.',
    };
    const unknown = await api('zecAdvice', { method: 'POST', body: { advice: { ...advice, snapshotId: randomUUID() } } });
    assert.equal(unknown.status, 409);
    const accepted = await api('zecAdvice', { method: 'POST', body: { advice } });
    assert.equal(accepted.status, 200);
    assert.deepEqual((await api('zecAdvice', { method: 'POST', body: { advice } })).body, accepted.body);
    assert.equal((await api('zecAdvice', { method: 'POST', body: {
      advice: { ...advice, decision: 'WAIT' },
    } })).status, 409);
    const { advisories } = await cli('zecAdvisories');
    assert.equal(advisories.length, 1);
    assert.equal(advisories[0].snapshotId, snapshot.id);
    assert.equal(advisories[0].rationale, advice.rationale);
    assert.ok(await browser.waitFor(() => evaluate('document.getElementById("zecAdviceList").textContent.includes("E2E: watch this paper position")')), 'Dashboard did not display the injected advisory');

    const pathWithFakeClaude = await installFakeClaude(root);
    const helper = async (...args) => {
      const { stdout } = await execute(process.execPath, [path.join(EXT, 'tools/zec-advisor.mjs'), ...args],
        { env: { ...env, PATH: pathWithFakeClaude }, timeout: 15_000 });
      return stdout.trim().split('\n').map(line => JSON.parse(line));
    };
    const stream = await helper('watch', '--samples', '2', '--interval', '5');
    assert.equal(stream.length, 2);
    assert.notEqual(stream[0].id, stream[1].id);
    assert.ok(stream.every(record => record.source.markPrice === MARK && record.engine.armed === false));
    const question = 'How should I proceed in this fixture?';
    const [draft] = await helper('ask', '--question', question);
    assert.equal(draft.advice.decision, 'OBSERVE');
    assert.equal(draft.advice.snapshotId, draft.snapshot.id);
    assert.equal((await cli('zecAdvisories')).advisories.length, 1);
    const [published] = await helper('ask', '--question', question, '--publish');
    assert.equal(published.advice.snapshotId, published.snapshot.id);
    assert.equal(published.published.snapshotId, published.snapshot.id);
    assert.equal((await cli('zecAdvisories')).advisories.length, 2);

    stale = true;
    const staleSnapshot = (await cli('zecSnapshot')).snapshot;
    assert.equal(staleSnapshot.source.status, 'unavailable');
    assert.equal(staleSnapshot.source.markPrice, null);
    assert.equal(staleSnapshot.closedCandles.status, 'ok');
    assert.equal((await api('zecAdvice', { method: 'POST', body: {
      advice: { ...advice, snapshotId: staleSnapshot.id, decision: 'PAPER_ONLY' },
    } })).status, 422);
    assert.deepEqual(await gridState(), gridBefore);
    await evaluate('document.getElementById("zecBridgeToggle").click()');
    assert.ok(await browser.waitFor(async () => (await message('zecAdvisories')).result?.bridge.enabled === false));
    assert.equal((await api('zecSnapshot')).status, 503);
    assert.ok(requests.some(({ url }) => url === '/app/perps/markets'));
    assert.equal(requests.filter(({ url, method }) => url.startsWith('/app/perps/') && method !== 'GET').length, 0);
    isolation.assertHealthy();
    if (interceptFailure) throw interceptFailure;
    console.log(`PASS Zec advisory Chrome=${browser.version} extension=${browser.extensionId} CLI/API/dashboard, watch and fixture Zec helper verified with stubbed GUM market data and unchanged disarmed state`);
  } finally {
    clearTimeout(watchdog);
    if (server) await new Promise(resolve => server.close(resolve));
    await browser?.close();
    await rm(root, { recursive: true, force: true });
  }
}

if (!CHROME) {
  console.error('Zec browser check needs Chrome for Testing. Set CHROME to the browser executable.');
  process.exitCode = 2;
} else {
  verify().catch(error => { console.error(error.stack); process.exitCode = 1; });
}
