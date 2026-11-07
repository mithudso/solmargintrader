/**
 * Overview and Alerts views.
 *
 * The overview paints from the stored scan first (instant, no network), then
 * refreshes holdings live. Alerts come from the background scan
 * (scanAlerts, src/core/alerts.js); this page only shows and acknowledges them.
 */

import {
  call, soltui, el, $, clear, empty, chip, table, usd, pct, ago, paint, extLink, guard, SOURCE_CHIP,
} from './ui-kit.js';

const SEVERITY_LABEL = { action: 'Worth acting on', review: 'Review', info: 'Lead' };

/** One alert card. `onAck` acknowledges it and repaints. */
export function alertCard(alert, onAck) {
  const ack = el('button', { class: 'small', text: alert.acked ? 'Acknowledged' : 'Acknowledge', disabled: alert.acked });
  ack.addEventListener('click', () => onAck(alert.id));
  return el('div', { class: `alert ${alert.severity}${alert.acked ? ' acked' : ''}` },
    el('div', { class: 'bar' }),
    el('div', {},
      el('div', { class: 'title', text: alert.title }),
      el('div', { class: 'detail', text: alert.detail }),
      el('div', { class: 'meta' },
        chip(SEVERITY_LABEL[alert.severity] ?? alert.severity, alert.severity === 'action' ? 'ok' : alert.severity === 'review' ? 'backtest' : 'warn'),
        chip(alert.source, SOURCE_CHIP[alert.source] ?? 'plain'),
        el('span', { text: `first seen ${ago(alert.firstSeenMs)}` }),
        extLink(alert.link, 'details ↗'))),
    el('div', {}, ack));
}

function holdingsKpis(state) {
  const h = state.holdings ?? state.overview?.scan?.holdings;
  if (!h) return;
  const chain = (name) => h.chains?.find((c) => c.chain === name);
  const atLeast = h.complete ? '' : 'at least ';
  $('#kpiTotal').textContent = usd(h.totalUsd);
  $('#kpiTotalSub').textContent = `${atLeast ? 'some values missing · ' : ''}read ${ago(h.atMs)}`;
  for (const [name, id] of [['base', 'kpiBase'], ['solana', 'kpiSolana']]) {
    const c = chain(name);
    $(`#${id}`).textContent = c && c.status !== 'skipped' && c.status !== 'failed' ? usd(c.totalUsd) : '—';
    $(`#${id}Sub`).textContent = !c ? '' : c.status === 'skipped' ? 'no address set'
      : c.status === 'failed' ? `read failed: ${c.errors?.[0] ?? ''}` : `${c.holdings.length} holdings${c.status === 'partial' ? ' · partial' : ''}`;
  }
  const base = chain('base');
  const idle = (base?.holdings ?? []).filter((x) => x.stable && x.included && Number.isFinite(x.usd)).reduce((s, x) => s + x.usd, 0);
  $('#kpiIdle').textContent = base && base.status !== 'skipped' ? usd(idle) : '—';
}

function lpKpi(state) {
  const lp = state.overview?.scan?.liquidity;
  if (!lp) { $('#kpiLp').textContent = '—'; $('#kpiLpSub').textContent = 'soltui not connected'; return; }
  $('#kpiLp').textContent = usd(lp.wallet?.deployed_usd ?? 0);
  $('#kpiLpSub').textContent = `${lp.killed ? 'halted (KILL file)' : lp.mode ?? 'unknown mode'} · ${lp.positions?.length ?? 0} positions · idle ${usd(lp.wallet?.idle_usd)}`;
}

function scoutTable(pools) {
  return table([
    { label: 'Pair', value: (p) => p.pair },
    { label: 'Net APR', num: true, value: (p) => el('span', { class: p.expected_net_apr >= 0 ? 'pos' : 'neg', text: pct(p.expected_net_apr) }) },
    { label: 'Backtest', num: true, value: (p) => pct(p.backtest_net_apr) },
    { label: 'TVL', num: true, value: (p) => usd(p.tvl_usd, { compact: true }) },
    { label: 'Confidence', value: (p) => p.confidence },
  ], pools, { emptyText: 'No scout data. The aero-lp daemon writes it; soltui reads it.' });
}

export async function renderOverview(state, { onAck }) {
  holdingsKpis(state);
  lpKpi(state);
  const scan = state.overview?.scan;
  const open = (scan?.alerts ?? []).filter((a) => !a.acked).slice(0, 5);
  clear($('#overviewAlerts'), open.length ? open.map((a) => alertCard(a, onAck))
    : empty(scan ? 'Nothing needs attention. The scan found no better modelled pool or strategy.' : 'Press "Scan now" for the first scan.'));
  const best = scan?.liquidity?.bestScout ?? [];
  clear($('#overviewScout'), scoutTable(best.slice(0, 5)));
  if (best.length && best.every((p) => !(p.expected_net_apr > 0))) {
    $('#overviewScout').append(el('p', { class: 'note', text: 'Every scouted pool models negative after loss-versus-rebalancing right now: holding beats providing liquidity.' }));
  }

  // Live: wallet P&L and strategy, each independent of the other.
  guard($('#kpiPnlSub'), async () => {
    const r = await soltui('pnl.summary', { window: '30d', source: 'wallet (live)' });
    const s = r.sections?.find((x) => x.source === 'wallet (live)');
    if (s?.status === 'ok') {
      paint($('#kpiPnl'), s.totals?.net_usd, { sign: true });
      $('#kpiPnlSub').textContent = s.totals?.net_pct_text ?? 'from soltui wallet snapshots';
    } else {
      $('#kpiPnl').textContent = '—';
      $('#kpiPnlSub').textContent = s?.message ?? 'no wallet snapshots yet';
    }
  });
  guard($('#overviewStrategy'), async () => {
    const [rec, top5] = await Promise.all([
      soltui('live.recommendation').catch(() => null),
      soltui('top5.list').catch(() => null),
    ]);
    const leader = top5?.configs?.find((c) => c.rank === 1);
    clear($('#overviewStrategy'),
      leader ? el('div', {},
        el('div', { class: 'row' }, el('strong', { text: leader.label }), chip('Top 5 #1', 'backtest')),
        el('p', { class: 'note', text: `${leader.home?.net_pct_text ?? ''} · median Sharpe ${leader.home?.median_sharpe?.toFixed?.(2) ?? '—'} · ${Math.round((leader.home?.frac_positive ?? 0) * 100)}% of paths positive` }))
        : empty('Top 5 evidence is not available (soltui not connected or not generated).'),
      rec ? el('p', { class: 'note', text: `Live-run pick: ${rec.strategy} (${rec.source}; ${rec.details})` }) : null,
      state.overview?.prefs?.activeStrategy ? el('p', { class: 'note', text: `Active strategy: ${state.overview.prefs.activeStrategy}` }) : null);
  });

  // Fresh balances; the stored scan already painted something.
  await guard(null, async () => {
    state.holdings = await call({ type: 'holdings' });
    holdingsKpis(state);
  });
}

/* --------------------------------------------------------------- Alerts -- */

export function renderAlerts(state, { onAck }) {
  const scan = state.overview?.scan;
  const alerts = scan?.alerts ?? [];
  clear($('#alertList'), alerts.length ? alerts.map((a) => alertCard(a, onAck))
    : empty(scan ? 'No alerts. Thresholds are under Alert settings below.' : 'No scan yet — press "Scan now".'));
  $('#scanNotes').textContent = scan?.notes?.length ? `Scan notes: ${scan.notes.join(' · ')}` : '';
  const form = $('#alertPrefs');
  const prefs = state.overview?.prefs ?? {};
  for (const input of form.elements) {
    if (!input.name || !(input.name in prefs)) continue;
    if (input.type === 'checkbox') input.checked = prefs[input.name] === true;
    else input.value = prefs[input.name] ?? '';
  }
}

export function mountAlertPrefs(refresh) {
  const form = $('#alertPrefs');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const patch = {};
    for (const input of form.elements) {
      if (!input.name) continue;
      if (input.type === 'checkbox') patch[input.name] = input.checked;
      else if (input.value.trim() !== '') patch[input.name] = Number(input.value);
    }
    try {
      await call({ type: 'setPrefs', patch });
      $('#alertPrefsStatus').textContent = 'Saved. The next scan uses these thresholds.';
      await refresh();
    } catch (err) {
      $('#alertPrefsStatus').textContent = `Not saved: ${err.message}`;
    }
  });
}
