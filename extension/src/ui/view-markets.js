/**
 * Holdings, Profit & loss and Discover views.
 *
 * Holdings come from the extension's own read-only market reads (holdings);
 * the deeper scan, snapshots, P&L history and the Aero scout come from soltui.
 * Every figure keeps its source label: a quoted APY is never shown as income.
 */

import {
  call, soltui, el, $, clear, empty, chip, table, usd, pct, amount, ago, extLink, guard, lineChart, signClass,
} from './ui-kit.js';

/* ------------------------------------------------------------- Holdings -- */

function chainCard(c) {
  const status = c.status === 'ok' ? chip('live', 'ok') : c.status === 'partial' ? chip('partial', 'warn')
    : c.status === 'skipped' ? chip('no address', 'plain') : chip('failed', 'bad');
  return el('div', { class: 'card' },
    el('div', { class: 'card-head' },
      el('h2', { text: c.chain === 'base' ? 'Base' : 'Solana' }),
      el('div', { class: 'row' }, el('strong', { text: usd(c.totalUsd) }), status)),
    c.address ? el('p', { class: 'note' }, el('code', { text: c.address }), ' ',
      extLink(c.chain === 'base' ? `https://basescan.org/address/${c.address}` : `https://solscan.io/account/${c.address}`, 'explorer ↗')) : null,
    table([
      { label: 'Token', value: (h) => el('span', {}, h.symbol, h.unverified ? ' ' : '', h.unverified ? el('span', { class: 'chip warn', text: 'unverified', title: 'Unknown and unpriced: listed, not counted. Airdrops look like this; do not interact with it.' }) : '') },
      { label: 'Amount', num: true, value: (h) => amount(h.amount) },
      { label: 'Price', num: true, value: (h) => usd(h.priceUsd) },
      { label: 'Value', num: true, value: (h) => (h.included ? usd(h.usd) : el('span', { class: 'muted', text: 'not counted' })) },
      { label: '', value: (h) => extLink(h.link, '↗') },
    ], c.holdings, { emptyText: c.status === 'skipped' ? 'Set an address under Settings.' : 'No balances above dust.' }),
    ...(c.errors ?? []).map((e) => el('p', { class: 'err', text: e })),
    ...(c.notes ?? []).map((n) => el('p', { class: 'note', text: n })));
}

export function renderHoldings(state) {
  const h = state.holdings ?? state.overview?.scan?.holdings;
  if (!h) { clear($('#holdingsChains'), empty('Loading balances…')); return; }
  const sources = Object.entries(h.addressSource ?? {}).map(([k, v]) => `${k}: ${v}`).join(' · ');
  clear($('#holdingsKpis'),
    el('div', { class: 'kpi' }, el('div', { class: 'label', text: 'Total' }), el('div', { class: 'value', text: usd(h.totalUsd) }),
      el('div', { class: 'sub', text: h.complete ? `complete · ${ago(h.atMs)}` : `some values missing · ${ago(h.atMs)}` })),
    el('div', { class: 'kpi' }, el('div', { class: 'label', text: 'Stablecoins' }), el('div', { class: 'value', text: usd(h.stableUsd) }),
      el('div', { class: 'sub', text: 'both chains' })),
    el('div', { class: 'kpi' }, el('div', { class: 'label', text: 'Addresses from' }), el('div', { class: 'sub', text: sources || 'preferences' })));
  clear($('#holdingsChains'), (h.chains ?? []).map(chainCard));
  const lp = state.overview?.scan?.liquidity;
  $('#lpStatus').textContent = lp ? (lp.killed ? 'halted (KILL file)' : lp.mode ?? 'unknown') : 'soltui not connected';
  clear($('#lpPositions'), table([
    { label: 'Pair', value: (p) => p.pair },
    { label: 'In range', value: (p) => (p.in_range ? 'yes' : 'no') },
    { label: 'Value', num: true, value: (p) => usd(p.value_usd) },
    { label: 'Deposited', num: true, value: (p) => usd(p.deposited_usd) },
    { label: 'P&L', num: true, value: (p) => el('span', { class: signClass(p.pnl_usd), text: usd(p.pnl_usd, { sign: true }) }) },
    { label: 'vs HODL', num: true, value: (p) => usd(p.pnl_vs_hodl_usd, { sign: true }) },
    { label: 'Realized APR', num: true, value: (p) => pct(p.apr_realized) },
    { label: 'Decision', value: (p) => p.decision },
  ], lp?.positions ?? [], { emptyText: lp ? `No open positions. Idle in the daemon wallet: ${usd(lp.wallet?.idle_usd)}.` : 'Connect soltui to see the LP daemon.' }));
}

export async function refreshHoldings(state) {
  clear($('#holdingsChains'), empty('Reading Base and Solana…'));
  return guard($('#holdingsChains'), async () => {
    state.holdings = await call({ type: 'holdings' });
    renderHoldings(state);
  });
}

export function mountHoldings(state) {
  $('#holdingsRefresh').addEventListener('click', () => refreshHoldings(state));
  $('#holdingsChanges').addEventListener('click', () => guard($('#holdingsChangesOut'), async () => {
    $('#holdingsChangesOut').textContent = 'Loading…';
    const r = await soltui('portfolio.changes', {});
    $('#holdingsChangesOut').textContent = JSON.stringify(r, null, 2);
  }));
  $('#holdingsDeep').addEventListener('click', async () => {
    const out = $('#deepScanOut');
    $('#deepScanCard').hidden = false;
    $('#holdingsDeep').disabled = true;
    clear(out, empty('Scanning every configured wallet through soltui… this can take a minute.'));
    await guard(out, async () => {
      const r = await soltui('portfolio.scan', { chain: 'all' });
      const chains = Object.entries(r.chains ?? {});
      clear(out, table([
        { label: 'Chain', value: ([name]) => name },
        { label: 'Status', value: ([, c]) => c.status ?? (c.errors?.length ? 'partial' : 'ok') },
        { label: 'Holdings', num: true, value: ([, c]) => c.counts?.holdings ?? c.holdings?.length },
        { label: 'Value', num: true, value: ([, c]) => usd(c.total_usd ?? c.usd) },
      ], chains, { emptyText: 'soltui found no wallets: add addresses or extended public keys in soltui Settings.' }),
      el('details', {}, el('summary', { text: 'Raw result' }), el('pre', { text: JSON.stringify(r, null, 2) })));
    });
    $('#holdingsDeep').disabled = false;
  });
}

/* ------------------------------------------------------------------ P&L -- */

function pnlSection(s) {
  const real = s.group === 'real';
  const head = el('div', { class: 'card-head' },
    el('h2', { text: s.label ?? s.source }),
    chip(real ? 'real money' : 'simulated', real ? 'live' : 'backtest'));
  if (s.status !== 'ok') {
    // Wallet P&L needs at least two snapshots; offer to record one rather than
    // leaving the owner to find the soltui command.
    let snap = null;
    if (s.source === 'wallet (live)') {
      snap = el('button', { class: 'small', text: 'Record a wallet snapshot now' });
      snap.addEventListener('click', async () => {
        snap.disabled = true;
        snap.textContent = 'Scanning wallets…';
        try {
          const r = await soltui('portfolio.snapshot');
          snap.textContent = `Recorded ${usd(r.total_usd)}${r.total_complete ? '' : ' (partial)'}; a second snapshot later shows a change`;
        } catch (err) {
          snap.textContent = `Not recorded: ${err.message}`;
        }
      });
    }
    return el('div', { class: 'card' }, head, el('p', { class: 'note', text: s.message ?? s.status }),
      ...(s.notes ?? []).map((n) => el('p', { class: 'note', text: n })), snap);
  }
  const t = s.totals ?? {};
  const stat = (label, value, cls) => el('div', { class: 'kpi' }, el('div', { class: 'label', text: label }), el('div', { class: `value ${cls ?? ''}`, text: value }));
  const days = s.days ?? [];
  return el('div', { class: 'card' }, head,
    el('div', { class: 'kpis' },
      stat('Net', usd(t.net_usd, { sign: true }), signClass(t.net_usd)),
      stat('Return', t.net_pct_text ?? '—'),
      stat('Costs', usd(t.costs_usd)),
      stat('Max drawdown', usd(s.drawdown?.max_drawdown_usd)),
      stat('Win rate', Number.isFinite(t.win_rate) ? `${Math.round(t.win_rate * 100)}% of ${t.closed_trades}` : '—')),
    days.length ? lineChart(days.map((d) => ({ x: Date.parse(d.date), y: d.cumulative })), { label: `${s.label} cumulative P&L` }) : null,
    s.by_strategy?.length ? table([
      { label: 'Strategy', value: (r) => r.strategy ?? r.name },
      { label: 'Asset', value: (r) => r.asset },
      { label: 'Net', num: true, value: (r) => usd(r.net_usd, { sign: true }) },
      { label: 'Return', num: true, value: (r) => r.net_pct_text },
    ], s.by_strategy) : null,
    ...(s.notes ?? []).map((n) => el('p', { class: 'note', text: n })));
}

let pnlGeneration = 0;

export async function refreshPnl() {
  const generation = ++pnlGeneration;
  const window = $('#pnlWindow').value;
  const source = $('#pnlSource').value;
  clear($('#pnlSections'), empty('Loading…'));
  try {
    const [summary, series] = await Promise.all([
      soltui('pnl.summary', { window, source }),
      soltui('pnl.series', { window, source }),
    ]);
    const days = new Map((series.sections ?? []).map((s) => [s.source, s]));
    const sections = (summary.sections ?? []).map((s) => ({ ...s, days: days.get(s.source)?.days ?? [] }));
    const grid = await call({ type: 'pnl' }).catch(() => null);
    if (generation !== pnlGeneration) return;
    $('#pnlNotice').textContent = summary.notice ?? '';
    clear($('#pnlSections'), sections.map(pnlSection),
      el('div', { class: 'card' },
        el('div', { class: 'card-head' }, el('h2', { text: 'Grid (this extension)' }), chip('simulated unless armed live', 'backtest')),
        el('p', {}, !grid ? 'Grid accounting unavailable.' : grid.roundTripCount > 0
          ? `Net ${usd(grid.totalNetUsd, { sign: true })} over ${grid.roundTripCount} round trips.${grid.accountingComplete === false ? ' Costs or basis are incomplete.' : ''} Details on the Grid tab.`
          : 'No closed grid round trips. Details on the Grid tab.')));
  } catch (err) {
    if (generation !== pnlGeneration) return;
    clear($('#pnlSections'), el('p', { class: 'err', text: `P&L unavailable: ${err.message}` }));
    return null;
  }
}

export function mountPnl() {
  $('#pnlRefresh').addEventListener('click', refreshPnl);
  $('#pnlWindow').addEventListener('change', refreshPnl);
  $('#pnlSource').addEventListener('change', refreshPnl);
}

/* ------------------------------------------------------------- Discover -- */

export async function refreshScout() {
  return guard($('#scoutTable'), async () => {
    const r = await soltui('liquidity.data', { top: 40 });
    $('#scoutMeta').textContent = r.scout_ok
      ? `${r.scout.pools.length} pools · ${r.scout.deposit_usd ? `$${r.scout.deposit_usd} deposit · ` : ''}${ago((r.scout.generated_at ?? 0) * 1000)}`
      : r.scout_reason ?? 'no scout data';
    clear($('#scoutTable'), table([
      { label: 'Pair', value: (p) => p.pair },
      { label: 'Spacing', num: true, value: (p) => p.tick_spacing },
      { label: 'TVL', num: true, value: (p) => usd(p.tvl_usd, { compact: true }) },
      { label: '24h volume', num: true, value: (p) => usd(p.volume_24h_usd, { compact: true }) },
      { label: 'Net APR', num: true, value: (p) => el('span', { class: signClass(p.expected_net_apr), text: pct(p.expected_net_apr, { places: 2 }) }) },
      { label: 'Backtest APR', num: true, value: (p) => pct(p.backtest_net_apr, { places: 2 }) },
      { label: 'Confidence', value: (p) => p.confidence },
      { label: 'Flags', value: (p) => (p.flags ?? []).join('; ') },
      { label: '', value: (p) => extLink(`https://basescan.org/address/${p.pool}`, '↗') },
    ], r.scout.pools, { emptyText: 'The scout has not run yet (aero-lp daemon).' }));
  });
}

export async function refreshPools() {
  const form = $('#poolFilters');
  const f = form.elements;
  const args = {
    chain: f.chain.value, sort: f.sort.value, limit: 60,
    stableOnly: f.stableOnly.checked, singleOnly: f.singleOnly.checked,
  };
  const minTvl = Number(f.minTvlUsd.value);
  if (f.minTvlUsd.value.trim() !== '' && Number.isFinite(minTvl)) args.minTvlUsd = minTvl;
  if (f.search.value.trim()) args.search = f.search.value.trim();
  clear($('#poolsTable'), empty('Loading DefiLlama yields (about 11 MB, cached for 10 minutes)…'));
  return guard($('#poolsTable'), async () => {
    const r = await call({ type: 'pools', ...args });
    $('#poolsMeta').textContent = `${r.pools.length} of ${r.total} · fetched ${ago(r.fetchedAtMs)}`;
    clear($('#poolsTable'), table([
      { label: 'Project', value: (p) => p.project },
      { label: 'Pool', value: (p) => el('span', {}, p.symbol, p.meta ? el('span', { class: 'muted', text: ` ${p.meta}` }) : '') },
      { label: 'Chain', value: (p) => p.chain },
      { label: 'TVL', num: true, value: (p) => usd(p.tvlUsd, { compact: true }) },
      { label: 'APY now', num: true, value: (p) => pct(p.apy) },
      { label: '30-day mean', num: true, value: (p) => pct(p.apyMean30d) },
      { label: 'Fees / rewards', num: true, value: (p) => `${pct(p.apyBase, { sign: false })} / ${pct(p.apyReward, { sign: false })}` },
      { label: '', value: (p) => el('span', { class: 'row' }, p.stablecoin ? chip('stable', 'ok') : null, p.ilRisk ? chip('IL', 'warn', 'Impermanent-loss exposure') : null) },
      { label: '', value: (p) => extLink(p.link, '↗') },
    ], r.pools, { emptyText: 'No pools match these filters.' }),
    el('p', { class: 'note', text: r.note }));
  });
}

export function mountDiscover() {
  $('#poolFilters').addEventListener('submit', (e) => { e.preventDefault(); refreshPools(); });
}
