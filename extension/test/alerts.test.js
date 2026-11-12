import test from 'node:test';
import assert from 'node:assert/strict';

import {
  computeAlerts, viableScoutPools, qualifyingLeads, mergeAlerts, notifiable, prefsProblem, DEFAULT_PREFS, SEVERITY,
} from '../src/core/alerts.js';
import { runCommand } from '../src/core/commands.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';

const scoutPool = (over = {}) => ({
  pool: '0xpool', pair: 'WETH/wstETH', tick_spacing: 1, expected_net_apr: 12, backtest_net_apr: 4,
  backtest_days: 7, confidence: 'high', flags: [], gauge_active: true, break_even_deposit_usd: 5, ...over,
});
// A scout written an hour before the scan clock below.
const NOW = 1_800_000_000_000;
const scout = (pools, extra = {}) => ({ generated_at: NOW / 1000 - 3600, deposit_usd: 50, pools, ...extra });
const baseHoldings = (usdc) => ({ chains: [{ chain: 'base', holdings: [{ symbol: 'USDC', usd: usdc, stable: true, included: true }] },
  { chain: 'solana', holdings: [{ symbol: 'USDC', usd: 999, stable: true, included: true }] }] });

test('CDO-2377ccbbdc CDO-05eac51ba7 action capital covers a known positive break-even in both branches', () => {
  for (const breakEven of [null, undefined, NaN, Infinity, -1, 0, 1000]) {
    const liquidity = { scout: scout([scoutPool({ break_even_deposit_usd: breakEven })]),
      positions: [{ pool: 'old', apr_realized: 0, value_usd: 20 }], wallet: { idle_usd: 30 } };
    assert.equal(computeAlerts({ liquidity, prefs: {}, nowMs: NOW }).filter(a => a.severity === SEVERITY.ACTION).length, 0, String(breakEven));
  }
  const liquidity = { scout: scout([scoutPool({ break_even_deposit_usd: 10 })]), positions: [{ pool: 'old', apr_realized: 0, value_usd: 20 }], wallet: { idle_usd: 30 } };
  assert.equal(computeAlerts({ liquidity, prefs: {}, nowMs: NOW }).filter(a => a.severity === SEVERITY.ACTION).length, 2);
});

/* ---------------------------------------------------------- pure rules -- */

test('only modelled pools that pass every gate may justify moving money; a missing field fails the gate', () => {
  const pools = [
    scoutPool({ pool: 'a', expected_net_apr: 20, backtest_net_apr: -1 }),
    scoutPool({ pool: 'b', expected_net_apr: 15, confidence: 'low' }),
    scoutPool({ pool: 'b2', expected_net_apr: 15, confidence: undefined }),
    scoutPool({ pool: 'c', expected_net_apr: 3 }),
    scoutPool({ pool: 'd', expected_net_apr: 9 }),
    scoutPool({ pool: 'd2', expected_net_apr: 8, confidence: 'medium' }),
    scoutPool({ pool: 'e', expected_net_apr: null }),
    scoutPool({ pool: 'f', expected_net_apr: 30, flags: ['fee history < 1 day'] }),
    scoutPool({ pool: 'f2', expected_net_apr: 30, flags: undefined }),
    scoutPool({ pool: 'g', expected_net_apr: 30, gauge_active: false }),
    scoutPool({ pool: 'h', expected_net_apr: 30, backtest_days: null }),
    scoutPool({ pool: 'h2', expected_net_apr: 30, backtest_days: 0.5 }),
  ];
  assert.deepEqual(viableScoutPools(pools, { minNetAprPct: 5 }).map((p) => p.pool), ['d', 'd2']);
});

test('the live scout today (every pool negative) raises no pool alert', () => {
  const liquidity = { scout: scout([scoutPool({ expected_net_apr: -0.002752, backtest_net_apr: -0.000134, flags: ['income below LVR at every width'] })]),
    positions: [], wallet: { idle_usd: 1 } };
  assert.deepEqual(computeAlerts({ holdings: baseHoldings(500), liquidity, prefs: {}, nowMs: NOW }), []);
});

test('a stale or undated scout can never raise an act alert', () => {
  const pools = [scoutPool({ expected_net_apr: 30 })];
  const old = { scout: scout(pools, { generated_at: NOW / 1000 - 72 * 3600 }), positions: [] };
  assert.deepEqual(computeAlerts({ holdings: baseHoldings(500), liquidity: old, prefs: {}, nowMs: NOW }), []);
  const undated = { scout: { pools, deposit_usd: 50 }, positions: [] };
  assert.deepEqual(computeAlerts({ holdings: baseHoldings(500), liquidity: undated, prefs: {}, nowMs: NOW }), []);
  const fresh = { scout: scout(pools), positions: [] };
  assert.deepEqual(computeAlerts({ holdings: baseHoldings(500), liquidity: fresh, prefs: {} }), [], 'no clock, no freshness');
  assert.equal(computeAlerts({ holdings: baseHoldings(500), liquidity: fresh, prefs: {}, nowMs: NOW }).length, 1);
});

test('a modelled pool beating an open position by the margin is an action alert with its evidence', () => {
  const liquidity = { scout: scout([scoutPool({ pool: '0xbest', expected_net_apr: 14 })]),
    positions: [{ slot: '7', pool: '0xmine', pair: 'WETH/cbBTC', apr_realized: 3, value_usd: 50 }] };
  const [a, ...rest] = computeAlerts({ liquidity, prefs: { minAprGainPct: 5 }, nowMs: NOW });
  assert.equal(rest.length, 0);
  assert.equal(a.severity, SEVERITY.ACTION);
  assert.equal(a.source, 'modelled');
  assert.equal(a.id, 'lp-better:7:0xbest');
  assert.equal(a.evidence.expectedNetAprPct, 14);
  assert.match(a.title, /models \+14\.0% net vs your WETH\/cbBTC realizing \+3\.0%/);
  assert.match(a.detail, /modelled, 1 h old/);
  // Below the margin: nothing.
  assert.deepEqual(computeAlerts({ liquidity, prefs: { minAprGainPct: 20 }, nowMs: NOW }), []);
});

test('idle capital counts Base stablecoins only, not Solana ones that would need a bridge', () => {
  const liquidity = { scout: scout([scoutPool({ expected_net_apr: 10 })]), positions: [] };
  assert.deepEqual(computeAlerts({ holdings: baseHoldings(10), liquidity, prefs: { minIdleUsd: 25 }, nowMs: NOW }), []);
  const [idle] = computeAlerts({ holdings: baseHoldings(100), liquidity, prefs: { minIdleUsd: 25 }, nowMs: NOW });
  assert.equal(idle.id, 'idle:0xpool');
  assert.equal(idle.evidence.idleUsd, 100);
  assert.equal(idle.evidence.scoutDepositUsd, 50);
  assert.match(idle.detail, /for a \$50\.00 deposit/);
  assert.match(idle.detail, /A different deposit size changes the result/);
  assert.doesNotMatch(idle.detail, /a year/, 'no dollar projection at a deposit size the scout did not model');
});

test('idle capital below the pool\'s break-even deposit raises nothing', () => {
  const liquidity = { scout: scout([scoutPool({ expected_net_apr: 10, break_even_deposit_usd: 1e12 })]), positions: [] };
  assert.deepEqual(computeAlerts({ holdings: baseHoldings(100), liquidity, prefs: { minIdleUsd: 25 }, nowMs: NOW }), []);
});

test('quoted leads are info only, say they are quoted, and do not notify unless asked', () => {
  const lead = { id: 'llama-1', project: 'aerodrome-v1', symbol: 'USDC-AERO', chain: 'base', apy: 130, apyMean30d: 120, tvlUsd: 4.8e6, link: 'https://defillama.com/yields/pool/llama-1' };
  const alerts = computeAlerts({ leads: [lead], prefs: {} });
  assert.equal(alerts[0].severity, SEVERITY.INFO);
  assert.equal(alerts[0].source, 'quoted');
  assert.match(alerts[0].detail, /not measured/);
  assert.deepEqual(notifiable(alerts, ['lead:llama-1'], {}), []);
  assert.equal(notifiable(alerts, ['lead:llama-1'], { notifyLeads: true }).length, 1);
});

test('qualifyingLeads uses the 30-day mean and DefiLlama outlier flag', () => {
  const pools = [
    { id: 'a', tvlUsd: 2e6, apy: 300, apyMean30d: 5, outlier: false },
    { id: 'b', tvlUsd: 2e6, apy: 10, apyMean30d: 20, outlier: false },
    { id: 'c', tvlUsd: 2e6, apy: 50, apyMean30d: 50, outlier: true },
    { id: 'd', tvlUsd: 1e5, apy: 50, apyMean30d: 50, outlier: false },
  ];
  assert.deepEqual(qualifyingLeads(pools, {}).map((p) => p.id), ['b']);
});

test('strategy alerts: a new Top 5 leader and a config that beats the active strategy are review alerts', () => {
  const top5 = { configs: [
    { rank: 1, label: 'all(a+b)', home: { median_sharpe: 1.4, frac_positive: 0.9, net_pct_text: 'backtest median net +75.1%' } },
    { rank: 2, label: 'any(c+d)', home: { median_sharpe: 1.0 } },
  ] };
  const leader = computeAlerts({ top5, previousLeader: 'any(c+d)', prefs: {} });
  assert.equal(leader.length, 1);
  assert.equal(leader[0].id, 'strategy-leader:all(a+b)');
  assert.equal(leader[0].severity, SEVERITY.REVIEW);
  assert.match(leader[0].detail, /Backtest, not a live result/);
  assert.deepEqual(computeAlerts({ top5, previousLeader: 'all(a+b)', prefs: {} }), [], 'no change, no alert');
  assert.deepEqual(computeAlerts({ top5, previousLeader: null, prefs: {} }), [], 'first scan, no alert');

  const better = computeAlerts({ top5, prefs: { activeStrategy: 'any(c+d)', minSharpeGain: 0.25 } });
  assert.equal(better[0].id, 'strategy-better:any(c+d):all(a+b)');
  assert.deepEqual(computeAlerts({ top5, prefs: { activeStrategy: 'any(c+d)', minSharpeGain: 0.5 } }), []);
  // An active strategy with no Top 5 record has no baseline to beat.
  assert.deepEqual(computeAlerts({ top5, prefs: { activeStrategy: 'macd', minSharpeGain: 0.25 } }), []);
});

test('mergeAlerts keeps first-seen time, applies acks from their own list, and reports only new unacked ids', () => {
  const a = { id: 'x', severity: 'action' };
  const b = { id: 'y', severity: 'review' };
  const first = mergeAlerts([], [a], 100);
  assert.deepEqual(first.fresh, ['x']);
  const second = mergeAlerts(first.alerts, [a, b], 200, ['y']);
  assert.equal(second.alerts[0].firstSeenMs, 100);
  assert.equal(second.alerts[0].lastSeenMs, 200);
  assert.equal(second.alerts[1].acked, true);
  assert.deepEqual(second.fresh, [], 'x is not new, y is acknowledged');
});

test('prefsProblem refuses thresholds that would silently disable or flood alerts', () => {
  assert.equal(prefsProblem({ minNetAprPct: 5, notifyLeads: true }), null);
  assert.match(prefsProblem({ minNetAprPct: NaN }), /finite/);
  assert.match(prefsProblem({ minIdleUsd: -1 }), /non-negative/);
  assert.match(prefsProblem({ alertIntervalMinutes: 1 }), /15 to 1440/);
  assert.match(prefsProblem({ alertsEnabled: 'yes' }), /true or false/);
  assert.match(prefsProblem({ apiKey: 'x' }), /unknown preference/);
  assert.equal(prefsProblem({ activeStrategy: null }), null);
  assert.equal(DEFAULT_PREFS.notifyLeads, false, 'quoted leads never notify by default');
});

/* ------------------------------------------------------------ commands -- */

function deps({ soltui, fetch } = {}) {
  let now = NOW;
  return {
    store: new MemoryStore(),
    configStore: new ConfigStore(null),
    soltui,
    fetch,
    clock: () => (now += 1000),
    log: () => {},
    async buildVenue() { throw new Error('market commands must not build a venue'); },
  };
}

/** A soltui transport stub answering liquidity.data, top5.list and wallet.addresses. */
function soltuiStub(results) {
  const calls = [];
  return {
    calls,
    async request(req) {
      calls.push(req);
      if (req.op === 'list') return { ok: true, command: 'list', result: [], error: null };
      const r = results[req.command];
      return r === undefined
        ? { ok: false, command: req.command, result: null, error: { code: 'unknown_command', message: 'no' } }
        : { ok: true, command: req.command, result: r, error: null };
    },
  };
}

test('setPrefs validates addresses and thresholds; getPrefs merges defaults', async () => {
  const d = deps();
  await assert.rejects(() => runCommand({ name: 'setPrefs', args: {}, deps: d }), /nothing to set/);
  await assert.rejects(() => runCommand({ name: 'setPrefs', args: { baseAddress: '0x12' }, deps: d }), /40 hex/);
  await assert.rejects(() => runCommand({ name: 'setPrefs', args: { solanaAddress: 'not base58 0OIl' }, deps: d }), /base58/);
  await assert.rejects(() => runCommand({ name: 'setPrefs', args: { minIdleUsd: -5 }, deps: d }), /non-negative/);
  await runCommand({ name: 'setPrefs', args: { baseAddress: '0x901a89cEC0608eB5435A915f006b45bD46405314', minNetAprPct: 8 }, deps: d });
  const p = await runCommand({ name: 'getPrefs', args: {}, deps: d });
  assert.equal(p.minNetAprPct, 8);
  assert.equal(p.minIdleUsd, DEFAULT_PREFS.minIdleUsd);
  await runCommand({ name: 'setPrefs', args: { patch: { baseAddress: null } }, deps: d });
  assert.equal((await runCommand({ name: 'getPrefs', args: {}, deps: d })).baseAddress, null);
});

test('holdings without fetch on the surface is a clean 502-style refusal per chain, not a crash', async () => {
  const d = deps();
  await runCommand({ name: 'setPrefs', args: { baseAddress: '0x901a89cEC0608eB5435A915f006b45bD46405314' }, deps: d });
  const h = await runCommand({ name: 'holdings', args: { chain: 'base' }, deps: d });
  assert.equal(h.chains[0].status, 'failed');
  assert.match(h.chains[0].errors[0], /no fetch configured/);
  assert.equal(h.addressSource.base, 'preferences');
  await assert.rejects(() => runCommand({ name: 'holdings', args: { chain: 'eth' }, deps: d }), /chain must be/);
});

test('holdings fills missing addresses from soltui settings and says so', async () => {
  const soltui = soltuiStub({ 'wallet.addresses': { base_address: '0x901a89cEC0608eB5435A915f006b45bD46405314', solana_address: 'EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV' } });
  const h = await runCommand({ name: 'holdings', args: {}, deps: deps({ soltui }) });
  assert.deepEqual(h.addressSource, { base: 'soltui settings', solana: 'soltui settings' });
});

test('scanAlerts stores a scan, records leads silently the first time, then alerts on a new one', async () => {
  const liquidity = { scout: scout([scoutPool({ expected_net_apr: 10 })]), positions: [],
    wallet: { idle_usd: 40 }, killed: true, mode: 'live' };
  const soltui = soltuiStub({ 'liquidity.data': liquidity, 'top5.list': { configs: [{ rank: 1, label: 'L1', home: { median_sharpe: 1 } }] } });
  let feed = [{ chain: 'Base', project: 'aerodrome-v1', symbol: 'A-B', pool: 'p1', tvlUsd: 5e6, apy: 30, apyMean30d: 30 }];
  const fetch = async (url) => ({
    ok: url.startsWith('https://yields.llama.fi'),
    status: url.startsWith('https://yields.llama.fi') ? 200 : 503,
    headers: { get: () => null },
    text: async () => JSON.stringify({ status: 'success', data: feed }),
  });
  const d = deps({ soltui, fetch });

  const first = await runCommand({ name: 'scanAlerts', args: {}, deps: d });
  assert.deepEqual(first.scan.alerts.map((a) => a.id), ['idle:0xpool']);
  assert.deepEqual(first.fresh, ['idle:0xpool']);
  assert.equal(first.notify.length, 1);
  assert.deepEqual(first.scan.leadIds, ['p1']);
  assert.equal(first.scan.leader, 'L1');
  assert.equal(first.scan.liquidity.killed, true);

  feed = [...feed, { chain: 'Solana', project: 'orca-dex', symbol: 'C-D', pool: 'p2', tvlUsd: 3e6, apy: 25, apyMean30d: 25 }];
  // The pool cache is 10 minutes; the stub clock advances 1 s per read, so force a refetch.
  const { fetchPoolsCached } = await import('../src/market/pools.js');
  await fetchPoolsCached(d, { maxAgeMs: 0 });
  const second = await runCommand({ name: 'scanAlerts', args: {}, deps: d });
  const ids = second.scan.alerts.map((a) => a.id);
  assert.deepEqual(ids, ['idle:0xpool', 'lead:p2']);
  assert.deepEqual(second.fresh, ['lead:p2']);
  assert.deepEqual(second.notify, [], 'a quoted lead does not notify by default');
  assert.equal(second.scan.alerts[0].firstSeenMs, first.scan.alerts[0].firstSeenMs);

  await runCommand({ name: 'ackAlerts', args: { id: 'idle:0xpool' }, deps: d });
  const ov = await runCommand({ name: 'overview', args: {}, deps: d });
  assert.equal(ov.scan.alerts.find((a) => a.id === 'idle:0xpool').acked, true);
  assert.equal(ov.scan.alerts.find((a) => a.id === 'lead:p2').acked, false);
  await runCommand({ name: 'ackAlerts', args: { all: true }, deps: d });
  const ov2 = await runCommand({ name: 'overview', args: {}, deps: d });
  assert.ok(ov2.scan.alerts.every((a) => a.acked));
  await assert.rejects(() => runCommand({ name: 'ackAlerts', args: {}, deps: d }), /--id or --all/);
});

test('after a scan that read an empty lead set, the next scan alerts on new leads instead of re-baselining', async () => {
  let feed = [];
  const fetch = async (url) => ({
    ok: url.startsWith('https://yields.llama.fi'), status: url.startsWith('https://yields.llama.fi') ? 200 : 503,
    headers: { get: () => null }, text: async () => JSON.stringify({ status: 'success', data: feed }),
  });
  const d = deps({ fetch });
  const { fetchPoolsCached } = await import('../src/market/pools.js');
  await fetchPoolsCached(d, { maxAgeMs: 0 });
  const first = await runCommand({ name: 'scanAlerts', args: {}, deps: d });
  assert.equal(first.scan.leadsBaselined, true);
  assert.deepEqual(first.scan.leadIds, []);
  feed = [{ chain: 'Base', project: 'aerodrome-v1', symbol: 'A-B', pool: 'p9', tvlUsd: 5e6, apy: 30, apyMean30d: 30 }];
  await fetchPoolsCached(d, { maxAgeMs: 0 });
  const second = await runCommand({ name: 'scanAlerts', args: {}, deps: d });
  assert.deepEqual(second.scan.alerts.map((a) => a.id), ['lead:p9']);
});

test('CDO-ff1819fc04 overlapping scans and acknowledgements preserve the new alert and its acknowledgement', { timeout: 2000 }, async () => {
  let release, entered;
  const gate = new Promise(resolve => { release = resolve; });
  const scanEntered = new Promise(resolve => { entered = resolve; });
  const order = [];
  const liquidity = { scout: scout([scoutPool()]), positions: [], wallet: { idle_usd: 40 } };
  const soltui = {
    async request(req) {
      if (req.op === 'list') return { ok: true, command: 'list', result: [], error: null };
      if (req.command === 'liquidity.data') {
        order.push('scan-read'); entered(); await gate;
        return { ok: true, command: req.command, result: liquidity, error: null };
      }
      return { ok: false, command: req.command ?? req.op, result: null, error: { code: 'failed', message: 'fixture unavailable' } };
    },
  };
  const d = deps({ soltui, fetch: async () => ({ ok: false, status: 503, headers: { get: () => null }, text: async () => '' }) });
  const scan = runCommand({ name: 'scanAlerts', args: {}, deps: d });
  let ack;
  try {
    await scanEntered;
    ack = runCommand({ name: 'ackAlerts', args: { all: true }, deps: d }).then(result => { order.push('ack'); return result; });
    for (let i = 0; i < 16; i++) await Promise.resolve();
    assert.deepEqual(order, ['scan-read'], 'the ack waits for the running scan');
  } finally { release(); }
  const [scanned, acknowledged] = await Promise.all([scan, ack]);
  assert.deepEqual(order, ['scan-read', 'ack']);
  assert.equal(acknowledged.acked, 1);
  assert.deepEqual(scanned.scan.alerts.map(alert => alert.id), ['idle:0xpool']);
  const overview = await runCommand({ name: 'overview', deps: d });
  assert.equal(overview.scan.scannedAtMs, scanned.scan.scannedAtMs);
  assert.equal(overview.scan.alerts[0].id, 'idle:0xpool');
  assert.equal(overview.scan.alerts[0].acked, true);
});

test('ackAlerts refuses an id longer than any alert id', async () => {
  await assert.rejects(() => runCommand({ name: 'ackAlerts', args: { id: 'x'.repeat(201) }, deps: deps() }), /at most 200/);
});

test('scanAlerts without soltui still scans and names what it could not read', async () => {
  const fetch = async () => ({ ok: false, status: 503, headers: { get: () => null }, text: async () => '' });
  const { scan } = await runCommand({ name: 'scanAlerts', args: {}, deps: deps({ fetch }) });
  assert.ok(scan.notes.some((n) => /liquidity\.data: soltui is not connected/.test(n)));
  assert.ok(scan.notes.some((n) => /top5\.list/.test(n)));
  assert.deepEqual(scan.alerts, []);
});

test('swapTokens lists both chains and swapQuote refuses bad input with a 400', async () => {
  const d = deps({ fetch: async () => { throw new Error('no network in this test'); } });
  const t = await runCommand({ name: 'swapTokens', args: {}, deps: d });
  assert.ok(t.base.some((x) => x.symbol === 'USDC') && t.solana.some((x) => x.symbol === 'SOL'));
  await assert.rejects(() => runCommand({ name: 'swapQuote', args: { chain: 'eth', from: 'a', to: 'b', amount: '1' }, deps: d }),
    (err) => err.status === 400 && /chain must be/.test(err.message));
  await assert.rejects(() => runCommand({ name: 'swapQuote', args: { chain: 'base', from: 'WETH', to: 'USDC', amount: '1.0000000000000000001' }, deps: d }),
    (err) => err.status === 400 && /decimal places/.test(err.message));
});
