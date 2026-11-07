/**
 * Backtest & strategies and Swap views.
 *
 * Strategy work runs in soltui (the backtester is Python): Top 5 evidence, the
 * roster, CPCV sweeps and signal defaults. Swaps are quotes from the extension's
 * registry (swapQuote); signing happens on the venue page (Stele KNOW-837).
 */

import {
  call, soltui, el, $, clear, chip, table, usd, pct, amount, guard, signClass,
} from './ui-kit.js';

/* ----------------------------------------------------------- Strategies -- */

const fracPct = (f) => (Number.isFinite(f) ? `${Math.round(f * 100)}%` : '—');

async function loadTop5(state) {
  await guard($('#top5Table'), async () => {
    const r = await soltui('top5.list');
    const active = state.overview?.prefs?.activeStrategy ?? null;
    $('#activeStrategy').textContent = active ? `Active: ${active}` : 'No active strategy set';
    clear($('#top5Table'), table([
      { label: '#', value: (c) => c.rank },
      { label: 'Configuration', value: (c) => el('span', {}, c.label, c.label === active ? ' ' : '', c.label === active ? chip('active', 'ok') : '') },
      { label: 'Horizon', value: (c) => c.horizon },
      { label: 'Median Sharpe', num: true, value: (c) => c.home?.median_sharpe?.toFixed?.(2) },
      { label: 'Paths positive', num: true, value: (c) => fracPct(c.home?.frac_positive) },
      { label: 'Result (SOL)', value: (c) => c.home?.net_pct_text },
      { label: 'Other coins', value: (c) => (c.transfers ?? []).map((t) => `${t.asset} ${t.median_sharpe?.toFixed?.(2) ?? '—'}`).join(', ') },
      { label: '', value: (c) => {
        const add = el('button', { class: 'small', text: 'Add to roster', title: 'Adds its member signals to the backtest roster' });
        add.addEventListener('click', () => rosterAction(state, () => soltui('top5.add_to_roster', { ranks: [c.rank] })));
        const use = el('button', { class: 'small', text: c.label === active ? 'In use' : 'Use', disabled: c.label === active,
          title: 'Mark as the strategy you run; alerts compare the others against it' });
        use.addEventListener('click', async () => {
          await call({ type: 'setPrefs', activeStrategy: c.label });
          state.overview = await call({ type: 'overview' });
          loadTop5(state);
        });
        return el('span', { class: 'row' }, add, use);
      } },
    ], r.configs, { emptyText: 'No Top 5 evidence: run the research sweep (research/sweep.py) first.' }));
  });
}

async function rosterAction(state, fn) {
  await guard($('#rosterTable'), async () => { await fn(); await loadRoster(state); });
}

async function loadRoster(state) {
  await guard($('#rosterTable'), async () => {
    const r = await soltui('roster.list');
    clear($('#rosterTable'), table([
      { label: 'Label', value: (e) => e.label },
      { label: 'Family', value: (e) => e.family },
      { label: 'Warm-up', num: true, value: (e) => e.warmup },
      { label: '', value: (e) => {
        const b = el('button', { class: 'small', text: 'Remove' });
        b.addEventListener('click', () => rosterAction(state, () => soltui('roster.remove', { label: e.label })));
        return b;
      } },
    ], r.entries, { emptyText: 'The roster is empty: add a strategy below.' }));
  });
}

async function loadCatalogue() {
  await guard(null, async () => {
    const list = await soltui('strategies.list');
    const select = $('#rosterAdd').elements.name;
    clear(select, list.map((s) => el('option', { value: s.name, text: `${s.name} (${s.family})` })));
  });
}

async function loadHistory() {
  await guard($('#historyTable'), async () => {
    const r = await soltui('strategies.history');
    const rows = (r.rows ?? []).filter((x) => x.tested).sort((a, b) => (b.last_at ?? 0) - (a.last_at ?? 0));
    clear($('#historyTable'), table([
      { label: 'Strategy', value: (x) => x.name },
      { label: 'Runs', num: true, value: (x) => x.runs },
      { label: 'Positive', num: true, value: (x) => x.positive },
      { label: 'Last', value: (x) => x.last_tested },
      { label: 'Result', value: (x) => x.result },
    ], rows, { emptyText: `No strategy has been tested on ${r.asset ?? 'this asset'} yet.` }),
    el('p', { class: 'note', text: `${(r.rows ?? []).length - rows.length} registered strategies are untested.` }));
  });
  await guard($('#recommendation'), async () => {
    const rec = await soltui('live.recommendation');
    clear($('#recommendation'), el('p', {}, el('strong', { text: rec.strategy }), ` — ${rec.source}. ${rec.details}`));
  });
}

async function loadSignals() {
  await guard($('#signalsForm'), async () => {
    const r = await soltui('signals.get');
    const form = $('#signalsForm');
    const fields = (r.groups ?? []).flatMap((g) => [
      el('h3', { class: 'full', text: g.group }),
      ...g.names.map((name) => {
        const input = el('input', { name, value: r.values?.[name] ?? '', step: 'any' });
        input.type = 'number';
        return el('label', {}, name, input);
      }),
    ]);
    const save = el('button', { class: 'primary', text: 'Save signal defaults' });
    save.type = 'submit';
    clear(form, fields, save);
  });
}

function backtestRows(r) {
  return table([
    { label: 'Strategy', value: (x) => x.label },
    { label: 'Family', value: (x) => x.family },
    { label: 'Median Sharpe', num: true, value: (x) => x.median_sharpe?.toFixed?.(2) },
    { label: 'IQR', num: true, value: (x) => x.iqr?.toFixed?.(2) },
    { label: 'Paths positive', num: true, value: (x) => fracPct(x.frac_positive) },
    { label: 'Trades', num: true, value: (x) => x.trades },
    { label: 'Result', value: (x) => el('span', { class: signClass(x.net_pct), text: x.net_pct_text }) },
  ], r.rows, { emptyText: 'No evaluable rows: every strategy was below the warm-up or trade floor.' });
}

let polling = null;

async function pollStatus() {
  const s = await soltui('backtest.status').catch(() => null);
  if (!s) return;
  $('#backtestBar').style.width = `${Math.round(s.percent ?? 0)}%`;
  $('#backtestStatus').textContent = s.title ?? s.phase;
  $('#backtestCancel').disabled = !s.running;
}

export function mountStrategies(state) {
  $('#backtestRun').addEventListener('click', async () => {
    $('#backtestRun').disabled = true;
    $('#backtestCancel').disabled = false;
    $('#backtestStatus').textContent = 'Starting the CPCV sweep over the roster…';
    clear($('#backtestResults'));
    polling = setInterval(pollStatus, 2000);
    await guard($('#backtestResults'), async () => {
      const r = await soltui('backtest.run');
      $('#backtestStatus').textContent = r.message;
      clear($('#backtestResults'), backtestRows(r),
        r.skipped?.length ? el('p', { class: 'note', text: `Skipped: ${r.skipped.map((x) => `${x.label} (${x.reason})`).join(', ')}` }) : null);
    });
    clearInterval(polling);
    $('#backtestBar').style.width = '100%';
    $('#backtestRun').disabled = false;
    $('#backtestCancel').disabled = true;
    loadHistory();
  });
  $('#backtestCancel').addEventListener('click', () => soltui('backtest.cancel').catch(() => {}));
  $('#rosterReset').addEventListener('click', () => rosterAction(state, () => soltui('roster.reset')));
  $('#rosterAdd').addEventListener('submit', (e) => {
    e.preventDefault();
    const f = e.target.elements;
    let params;
    if (f.params.value.trim()) {
      try { params = JSON.parse(f.params.value); } catch { clear($('#rosterTable'), el('p', { class: 'err', text: 'Params must be a JSON object.' })); return; }
    }
    rosterAction(state, () => soltui('roster.add', params ? { name: f.name.value, params } : { name: f.name.value }));
    f.params.value = '';
  });
  $('#signalsDetails').addEventListener('toggle', () => { if ($('#signalsDetails').open) loadSignals(); });
  $('#signalsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const values = {};
    for (const input of e.target.elements) if (input.name && input.value.trim() !== '') values[input.name] = Number(input.value);
    try {
      await soltui('signals.save', { values });
      $('#signalsStatus').textContent = 'Saved. The next backtest uses these values.';
    } catch (err) {
      $('#signalsStatus').textContent = `Not saved: ${err.message}`;
    }
  });
}

export async function refreshStrategies(state) {
  await Promise.all([loadTop5(state), loadRoster(state), loadCatalogue(), loadHistory(), pollStatus()]);
}

/* ------------------------------------------------------------------ Swap -- */

let swapChain = 'base';
let tokens = null;

function fillTokenSelects() {
  const list = tokens?.[swapChain] ?? [];
  const f = $('#swapForm').elements;
  const opts = () => list.map((t) => el('option', { value: t.symbol, text: t.symbol }));
  clear(f.from, opts());
  clear(f.to, opts());
  f.from.value = swapChain === 'base' ? 'ETH' : 'SOL';
  f.to.value = 'USDC';
}

function showBalance(state) {
  const f = $('#swapForm').elements;
  const h = (state.holdings ?? state.overview?.scan?.holdings)?.chains?.find((c) => c.chain === swapChain);
  const sym = f.from.value;
  const held = h?.holdings?.find((x) => x.symbol === sym);
  $('#swapBalance').textContent = held ? `Balance: ${amount(held.amount)} ${sym} (${usd(held.usd)})` : '';
}

export function mountSwap(state) {
  const form = $('#swapForm');
  for (const b of form.querySelectorAll('[data-chain]')) {
    b.addEventListener('click', () => {
      swapChain = b.dataset.chain;
      for (const o of form.querySelectorAll('[data-chain]')) o.setAttribute('aria-pressed', String(o === b));
      fillTokenSelects();
      showBalance(state);
      $('#swapQuote').hidden = true;
    });
  }
  // Any change to the request makes the shown quote (and its hand-off link) stale.
  const stale = () => { $('#swapQuote').hidden = true; form.elements.out.value = ''; };
  form.elements.from.addEventListener('change', () => { stale(); showBalance(state); });
  form.elements.to.addEventListener('change', stale);
  form.elements.amount.addEventListener('input', stale);
  form.elements.slippageBps.addEventListener('input', stale);
  $('#swapFlip').addEventListener('click', () => {
    const f = form.elements;
    [f.from.value, f.to.value] = [f.to.value, f.from.value];
    stale();
    showBalance(state);
  });
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = form.elements;
    $('#swapError').textContent = '';
    $('#swapQuote').hidden = true;
    // The tolerance sets "minimum received": never substitute one the owner did not type.
    const slippageBps = Number(f.slippageBps.value);
    if (!Number.isInteger(slippageBps) || slippageBps < 1 || slippageBps > 1000) {
      $('#swapError').textContent = 'Slippage tolerance must be a whole number of basis points from 1 to 1000.';
      return;
    }
    f.out.value = '…';
    try {
      const q = await call({
        type: 'swapQuote', chain: swapChain, from: f.from.value, to: f.to.value,
        amount: f.amount.value.trim(), slippageBps,
      });
      f.out.value = amount(q.to.amount);
      $('#swapVenue').textContent = q.venue;
      const rows = [
        ['You pay', `${amount(q.from.amount)} ${q.from.symbol}`],
        ['You receive (quote)', `${amount(q.to.amount)} ${q.to.symbol}`],
        ['Minimum received', q.minOut == null ? '—' : `${amount(q.minOut)} ${q.to.symbol}`],
        ['Rate', `1 ${q.from.symbol} = ${amount(q.to.amount / q.from.amount)} ${q.to.symbol}`],
        ['Price impact', pct(q.priceImpactPct, { sign: false, places: 3 })],
        ['Pool fee', q.feePct == null ? 'included in route' : pct(q.feePct, { sign: false, places: 3 })],
        ['Route', q.route.join(' → ')],
        q.usdValue ? ['Value', usd(q.usdValue)] : null,
      ].filter(Boolean);
      clear($('#swapDetails'), rows.flatMap(([k, v]) => [el('dt', { text: k }), el('dd', { text: v })]));
      clear($('#swapCaveats'), (q.caveats ?? []).map((c) => el('li', { text: c })));
      const link = $('#swapHandoff');
      link.href = q.handoffUrl;
      link.textContent = `Review and sign on ${q.chain === 'base' ? 'Aerodrome' : 'Jupiter'} ↗`;
      $('#swapQuote').hidden = false;
    } catch (err) {
      f.out.value = '';
      $('#swapError').textContent = err.message;
    }
  });
}

export async function refreshSwap(state) {
  if (!tokens) {
    await guard($('#swapError'), async () => { tokens = await call({ type: 'swapTokens' }); fillTokenSelects(); });
  }
  showBalance(state);
}

