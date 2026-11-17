import { el, clear, usd, pct, signClass } from './ui-kit.js';

const finite = n => typeof n === 'number' && Number.isFinite(n);
export const utc = seconds => finite(seconds) ? new Date(seconds * 1000).toISOString().slice(0, 19).replace('T', ' ') + ' UTC' : 'Time unavailable';
export const fraction = n => finite(n) ? pct(n * 100) : '—';
const text = (value, fallback = 'Unavailable') => value == null || value === '' ? fallback : String(value);
const note = value => el('p', { class: 'note', text: value });
const button = (label, run, cls = '') => { const b = el('button', { class: cls, text: label, onclick: run }); b.type = 'button'; return b; };
const link = (label, route) => el('a', { href: route, text: label,
  target: route.startsWith('chrome-extension://') ? '_blank' : null,
  rel: route.startsWith('chrome-extension://') ? 'noopener noreferrer' : null });

export function workflowText(workflow = {}) {
  const batch = workflow.batch;
  if (batch) return `${text(batch.phase)} · ${Object.entries(batch.counts ?? {}).map(([k, v]) => `${v} ${k}`).join(' · ')}${batch.assets?.length ? ` · ${batch.assets.length} coins` : ''}`;
  if (workflow.running) return 'Preparing paper tests and monitoring…';
  return workflow.message ?? (workflow.state === 'ready' ? 'Paper monitoring prepared; inspect measured results below.' : text(workflow.state, 'Paper workflow has not been requested.'));
}

export function workflowButtonText(workflow = {}) {
  if (workflow.running) return 'Preparing paper workflow…';
  if (workflow.state === 'ready') return 'Paper monitoring ready';
  return 'Start / resume paper bots';
}

/** These are separate ledgers. A saved wallet balance is never called profit. */
export function pnlLines(pnl) {
  if (!pnl) return [];
  return [['Net', `${usd(pnl.net_usd, { sign: true })} · ${fraction(pnl.net_pct)}`],
    ['Realized', usd(pnl.realized_usd, { sign: true })], ['Open position', usd(pnl.unrealized_usd, { sign: true })],
    ['Equity', usd(pnl.equity)], ...(finite(pnl.costs_usd) ? [['Costs', usd(pnl.costs_usd)]] : []),
    ...(finite(pnl.round_trips) ? [['Round trips', String(pnl.round_trips)]] : []),
    ...(finite(pnl.hold_return) ? [['Buy & hold', fraction(pnl.hold_return)], ['Versus hold', fraction(pnl.excess_return)]] : [])];
}

function pnlNode(pnl) {
  if (!pnl) return note('P&L unavailable until this session is assessed.');
  return el('dl', { class: 'rail-numbers' }, pnlLines(pnl).flatMap(([label, value], i) => [
    el('dt', { text: label }), el('dd', { class: i === 0 ? signClass(pnl.net_usd) : '', text: value }),
  ]));
}

/** One view lifecycle. It starts only a bounded read-model, never bots or tests. */
export function mountLivePanel(host, { read, asset = 'SOL', clock = window, onSnapshot = () => {}, onAsset = () => {}, voteButton = null, dashboardURL = '' } = {}) {
  let coin = asset, epoch = 0, disposed = false, busy = false, last = null, lastWarm = 0, queued = false;
  const status = note('Connecting to saved live evidence…'); status.setAttribute('role', 'status');
  const content = el('div');
  const refresh = button('Refresh', () => tick(true), 'small');
  const assetInput = el('input', { value: coin, maxLength: 20, size: 7, 'aria-label': 'Live sidebar coin' });
  const header = el('div', { class: 'card-head' }, el('h2', { text: 'Live monitor' }), assetInput, refresh);
  host.replaceChildren(header, status, content);
  const route = hash => dashboardURL ? `${dashboardURL}${hash}` : hash;
  const details = (title, body, opened = false) => el('details', { open: opened }, el('summary', { text: title }), body);
  function paint(snapshot) {
    last = snapshot;
    host.dataset.stale = String(snapshot.stale === true);
    const a = snapshot.voting?.aggregate ?? {}, producer = snapshot.voting?.producer ?? {};
    const stale = snapshot.stale === true;
    status.textContent = `${stale ? 'Stale' : 'Updated'} · ${utc(snapshot.observed_at)}${finite(snapshot.age_seconds) ? ` · ${Math.round(snapshot.age_seconds)}s old` : ''}`;
    status.classList.toggle('err', stale);
    const votes = el('section', { class: 'rail-section', 'aria-label': 'Current voting' },
      el('div', { class: 'card-head' }, el('h3', { text: `${coin} votes` }), link('Signals', route('#soltui/signal'))),
      el('p', { class: `rail-score signal-score-${!stale && a.available ? a.color : 'gray'}`, text: !stale && a.available ? `${a.label} · ${a.score > 0 ? '+' : ''}${a.score} / 100` : 'Agreement unavailable' }),
      note(`${a.strategies ?? 0} voting strategies · ${a.votes ?? 0} horizon votes`),
      note(`Prediction producer ${producer.running ? 'running' : producer.paused ? 'paused' : 'stopped / unavailable'}`));
    if (producer.message && !a.available) votes.append(note(producer.message), link('Forward testing', route('#soltui/forward')));
    if (!producer.running && producer.can_start) votes.append(button('Start predictions', async event => {
      const b = event.currentTarget; b.disabled = true;
      try { await read('forwardtest.ensure', { asset: coin, manual: true }); await tick(true); }
      catch (error) { status.textContent = error.message; }
      finally { b.disabled = false; }
    }, 'small'));
    const rows = snapshot.voting?.rows ?? [];
    if (rows.length) {
      const list = el('ul', { class: 'rail-votes' });
      for (const r of rows.slice(0, 4)) {
        const horizons = [1, 5, 10, 30].filter(h => finite(r[`expires_${h}m`]) && r[`expires_${h}m`] > Date.now() / 1000 && finite(r[`issued_${h}m`]) && r[`issued_${h}m`] <= Date.now() / 1000
          && finite(r[`acc_${h}m`]) && r[`acc_${h}m`] >= (a.min_accuracy ?? 60) && r[`resolved_${h}m`] >= (a.min_resolved ?? 20));
        if (!horizons.length || stale) continue;
        list.append(el('li', {}, voteButton ? voteButton(r, coin) : el('span', { text: r.label }),
          el('small', { text: horizons.map(h => `${h}m ${r[`pred_${h}m`]}`).join(' · ') })));
      }
      votes.append(list);
      if ((snapshot.voting?.eligible_count ?? rows.length) > 4) votes.append(link(`All ${snapshot.voting?.eligible_count ?? rows.length} voting strategies`, route('#soltui/signal')));
    }
    const c = snapshot.council ?? {}, grid = snapshot.grid ?? {};
    const council = el('section', { class: 'rail-section' },
      el('div', { class: 'card-head' }, el('h3', { text: `Council · ${c.config?.asset ?? '—'}` }), el('span', { class: 'chip plain', text: 'paper' })),
      el('strong', { text: `${c.running ? 'Running' : 'Stopped / unavailable'} · ${c.position ? c.position.direction > 0 ? 'Long' : 'Short' : 'Flat'}` }),
      note(c.message ?? c.state ?? 'Waiting for status'),
      note(finite(c.confidence) ? `Entry confidence ${(c.confidence * 100).toFixed(1)}% · floor ${((c.config?.execution?.min_confidence ?? .8) * 100).toFixed(0)}%` : `Confidence warming up · ${c.confidence_samples ?? 0} outcomes`),
      pnlNode(c.pnl), link('Council settings & fills', route('#soltui/bots')));
    const gridNode = el('section', { class: 'rail-section' },
      el('div', { class: 'card-head' }, el('h3', { text: `Grid · ${grid.asset ?? '—'}` }), el('span', { class: 'chip plain', text: 'paper' })),
      el('strong', { text: text(grid.state) }), note(grid.message ?? ''), pnlNode(grid.pnl),
      note(grid.started_at ? `Since ${utc(grid.started_at)}` : 'No saved forward session'),
      grid.age_seconds != null ? note(`Assessment ${Math.round(grid.age_seconds)}s old${grid.stale ? ' · stale' : ''}`) : null,
      details('Session evidence', el('div', {}, note(`Session ${grid.session_id ?? 'unavailable'}`), note(grid.pnl?.note ?? ''),
        note(`${grid.coverage?.bars ?? '—'} bars · ${grid.coverage?.snapshots ?? '—'} quotes · ${grid.coverage?.bridged_minutes ?? '—'} bridged minutes`),
        note(grid.source?.kind ?? 'Recorded-stream paper replay'))));
    const wallet = snapshot.wallet ?? {}, activity = snapshot.activity ?? {};
    const walletNode = el('section', { class: 'rail-section' }, el('h3', { text: 'Wallets · actual funds' }),
      note(`Saved valuation ${usd(wallet.total_usd)}${wallet.partial ? ' · partial' : ''}`),
      note(wallet.as_of ? utc(wallet.as_of) : 'Valuation time unavailable'),
      note('Wallet P&L unavailable: deposits and cost basis are not reconciled.'),
      link('Balances & orders', route('#soltui/money')));
    const history = el('section', { class: 'rail-section' }, el('h3', { text: 'Latest wallet actions' }));
    const actions = activity.wallet_items ?? (activity.items ?? []).filter(r => ['wallet', 'live'].includes(r.mode));
    const list = el('ol', { class: 'rail-actions' });
    for (const row of actions.slice(0, 8)) {
      const title = row.summary ?? row.kind ?? 'Wallet action';
      // Fixed explorers only. Provider-controlled URLs never become privileged links.
      const safe = typeof row.url === 'string' && /^https:\/\/(basescan\.org\/tx\/0x[0-9a-fA-F]{64}|solscan\.io\/tx\/[1-9A-HJ-NP-Za-km-z]{64,100})$/.test(row.url);
      const label = safe ? el('a', { href: row.url, target: '_blank', rel: 'noopener noreferrer', text: title }) : el('span', { text: title });
      list.append(el('li', {}, label, el('small', { text: `${row.chain ?? ''} · ${row.status ?? 'unconfirmed'} · ${utc(row.at)}` }),
        row.actor ? el('small', { text: `Actor ${row.actor}`, title: row.actor }) : null));
    }
    history.append(actions.length ? list : note('No actions returned within the covered history.'));
    history.append(details('History coverage', el('div', {},
      ...(activity.coverage ?? []).map(r => note(`${r.chain ?? r.source ?? 'Source'}: ${r.status ?? r.state ?? 'unknown'}${r.message ? ' · ' + r.message : ''}`)),
      ...(activity.gaps ?? []).map(note))));
    const optimizer = snapshot.optimizer ?? {}, workflow = snapshot.workflow ?? {};
    const stages = Object.entries(workflow.stages ?? {});
    const testing = el('section', { class: 'rail-section' }, el('h3', { text: 'Tests & optimization' }), note(workflowText(workflow)),
      note(`Optimizer ${optimizer.running ? 'running' : text(optimizer.state, 'idle')} · ${optimizer.message ?? 'readiness unavailable'}`),
      details('Readiness & process', el('div', {},
        note('Backtests check historical behavior and costs. Forward tests check new data. Optimization adopts only candidates that pass the existing gates.'),
        ...stages.map(([name, stage]) => note(`${name.replaceAll('_', ' ')}: ${stage.state === 'completed' ? 'requested / prepared' : text(stage.state)}${stage.error ? ' · ' + stage.error : stage.result?.message ? ' · ' + stage.result.message : ''}`)),
        note(optimizer.gates?.notice ?? 'Measured results can lose money.'))),
      link('Full testing results', route('#soltui/research')));
    clear(content, votes, council, gridNode, testing, walletNode, history);
    onSnapshot(snapshot);
  }
  async function tick(force = false) {
    if (disposed || busy || (!force && clock.document?.hidden)) return;
    busy = true; const generation = epoch, selected = coin;
    try {
      let warmingFailed = false;
      if (force || Date.now() - lastWarm >= 20_000) {
        lastWarm = Date.now();
        try { await read('live.rail_refresh', { asset: selected }); } catch { warmingFailed = true; }
      }
      const value = await read('live.rail', { asset: selected, limit: 8 });
      if (!disposed && generation === epoch) {
        paint(value);
        if (warmingFailed) { status.textContent += ' · Refresh preparation failed; showing saved evidence.'; status.classList.add('err'); }
      }
    } catch (error) {
      if (!disposed && generation === epoch) { if (last) paint({ ...last, stale: true }); status.textContent = `Monitor unavailable · ${error.message}`; status.classList.add('err'); }
    } finally { busy = false; if (queued && !disposed) { queued = false; tick(true); } }
  }
  function setAsset(value) {
    const next = String(value).trim().toUpperCase();
    if (!/^[A-Z0-9]{1,20}$/.test(next)) { status.textContent = 'Enter a coin such as SOL.'; return; }
    if (next === coin) return;
    epoch++; coin = next; assetInput.value = next; last = null; lastWarm = 0;
    clear(content); status.textContent = `Loading ${next}…`;
    onAsset(next);
    if (busy) queued = true; else tick(true);
  }
  assetInput.addEventListener('change', () => setAsset(assetInput.value));
  const timer = clock.setInterval(() => tick(), 10_000);
  tick(true);
  return { refresh: () => tick(true), setAsset, get asset() { return coin; }, dispose() { disposed = true; epoch++; clock.clearInterval(timer); } };
}
