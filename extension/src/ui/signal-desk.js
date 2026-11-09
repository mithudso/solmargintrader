/** Composed Signal Desk screens over the same reviewed native command registry. */
import { el, clear, table, tableScrollHint } from './ui-kit.js';
import { DESK_PAGES, DESK_READS, commandBlock, finite, numberText, percentText,
  runFromEnvelope, comparisonStatus, handoffValues, forwardColumns } from './desk-model.js';

const STORE = 'signalDesk.v1';
const TITLE = { signal: 'Live signals', research: 'Backtesting', forward: 'Forward testing', bots: 'Bot monitor' };
const PURPOSE = { signal: 'Prices and current strategy signals.',
  research: 'Run and compare backtests.',
  forward: 'Track paper predictions and outcomes.',
  bots: 'Monitor running jobs.' };
const action = (text, fn, primary = false) => { const b = el('button', { text, class: primary ? 'primary' : '', onclick: fn }); b.type = 'button'; return b; };
const note = (text, warning = false) => el('p', { class: warning ? 'banner warn' : 'note', text });
const stamp = (ts) => finite(ts) ? new Date(ts * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC' : 'Unavailable';
const kpi = (label, value, detail) => el('div', { class: 'kpi' }, el('div', { class: 'label', text: label }),
  el('div', { class: 'value', text: value }), el('div', { class: 'sub', text: detail }));

export function mountSignalDesk(root, { ask, openTool, refreshLive, transport, persist = null }) {
  const $ = (s) => root.querySelector(s);
  const host = $('#deskWorkspace');
  if (!host) return { route() {}, commands() {}, receive() {}, live() {}, jobs() {}, dispose() {}, restore: Promise.resolve() };
  const storage = persist ?? globalThis.chrome?.storage?.local;
  let commands = [], page = 'signal', epoch = 0, disposed = false, busy = false, lastAt = null;
  let renderedRead = '';
  let runs = [], selected = new Set(), draft = null, settings = null, data = {}, failures = {}, liveSnapshot = null;
  const activity = [], waiting = new Map();
  const asset = () => $('#soltuiLiveAsset').value.trim().toUpperCase();
  async function save() {
    const val = { runs, selected: [...selected], draft, asset: asset(), page, source: $('#soltuiPriceSource')?.value ?? 'coinbase',
      density: $('#deskDensity')?.value ?? 'comfortable' };
    try {
      if (!storage) throw new Error('Browser storage unavailable');
      await storage.set({ [STORE]: val });
      if ($('#deskStorageStatus')) $('#deskStorageStatus').textContent = '';
    } catch {
      if ($('#deskStorageStatus')) $('#deskStorageStatus').textContent = 'Browser storage could not save this session. Keep this dashboard open and export important results; new snapshots may not survive closing it.';
    }
  }
  const restore = Promise.resolve(storage?.get(STORE)).then((value) => {
    const s = value?.[STORE];
    if (!s || disposed) return;
    if (['coinbase', 'jupiter'].includes(s.source) && $('#soltuiPriceSource')) $('#soltuiPriceSource').value = s.source;
    runs = Array.isArray(s.runs) ? s.runs.filter((r) => r?.context?.schema === 1 && Array.isArray(r.rows)).slice(0, 12) : [];
    selected = new Set(Array.isArray(s.selected) ? s.selected.filter((id) => runs.some((r) => r.id === id)) : []);
    draft = s.draft?.run && s.draft?.row ? s.draft : null;
    if (/^[A-Z0-9]{1,20}$/.test(s.asset ?? '')) $('#soltuiLiveAsset').value = s.asset;
    if (['compact', 'comfortable'].includes(s.density)) { if ($('#deskDensity')) $('#deskDensity').value = s.density; root.querySelector('body')?.setAttribute('data-density', s.density); }
    if (!location.hash && DESK_PAGES.has(s.page)) location.hash = `soltui/${s.page}`;
  }).catch(() => {});

  function inspect(title, value) {
    const dialog = $('#deskDetail');
    if (!dialog) return;
    const trigger = root.ownerDocument?.activeElement ?? document.activeElement;
    $('#deskDetailTitle').textContent = title;
    $('#deskDetailBody').textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    dialog.onclose = () => trigger?.isConnected ? trigger.focus() : $('#deskTitle').focus();
    dialog.showModal();
  }
  function choose(name, values = {}) {
    const c = commands.find((x) => x.name === name);
    if (!c) { inspect('Tool unavailable', 'This installed native host does not expose this command. Reconnect after updating the host.'); return; }
    if (Object.hasOwn(values, 'snapshot') && !['snapshot', 'source_label'].every((name) => c.params?.some((p) => p.name === name))) { inspect('Host update needed', 'This host predates pinned paper handoffs. Reconnect after updating; no unpinned trial was prepared.'); return; }
    const blocked = commandBlock(c);
    if (blocked) { inspect('Archived control', blocked); return; }
    $('#soltuiToolbox').open = true;
    $('#soltuiToolbox').dataset.focused = 'true';
    openTool(name, values);

  }
  function buttons(items) {
    return el('div', { class: 'desk-actions' }, ...items.map(([label, name, values, primary]) => action(label, () => choose(name, values), primary)));
  }
  function message() {
    $('#deskReadStatus').textContent = busy ? 'Reading saved evidence…' : lastAt
      ? `Read ${new Date(lastAt).toISOString().slice(11, 19)} UTC · read-only refresh every 10s while visible`
      : 'No saved evidence read yet.';
  }
  async function read(name, params = {}) {
    const c = commands.find((x) => x.name === name);
    if (!c || c.read_only !== true || c.requires_confirm || c.long_running || commandBlock(c)) throw new Error('Unavailable on this host');
    const key = JSON.stringify([name, params]);
    if (waiting.has(key)) return waiting.get(key);
    const promise = ask(name, params).then((env) => { if (!env?.ok) throw new Error(env?.error?.message ?? 'Read failed'); return env; })
      .finally(() => waiting.delete(key));
    waiting.set(key, promise);
    return promise;
  }
  async function refresh() {
    if (busy || disposed || !DESK_READS[page] || document.hidden || $('#view-soltui').hidden) return;
    const context = ++epoch, current = page, coin = asset();
    if (!/^[A-Z0-9]{1,20}$/.test(coin)) return;
    busy = true; message();
    const output = {}, errors = {};
    try {
      await Promise.all(DESK_READS[current].map(async (name) => {
        const params = name === 'forwardtest.status' ? { coins: [coin] }
          : name === 'compound.unattended_status' ? { asset: coin } : {};
        try { output[name] = (await read(name, params)).result; }
        catch (e) { errors[name] = e.message; }
      }));
      if (disposed || context !== epoch || current !== page || coin !== asset()) return;
      data = output; failures = errors; lastAt = Date.now();
      settings = output['settings.get']?.settings ?? settings;
      if (output['backtest.results']) receive({ ok: true, command: 'backtest.results', result: output['backtest.results'] }, false);
      const signature = JSON.stringify([output, errors]);
      if (signature !== renderedRead) { renderedRead = signature; render(); }
    } finally { busy = false; if (!disposed) message(); }
  }
  function costText(execution) {
    if (!execution) return 'Cost scenario unavailable';
    return `${execution.fee_schedule} · ${numberText(execution.fee_bps)} bps fee + ${numberText(execution.slippage_bps)} bps slippage / side · borrow long ${numberText(execution.borrow_long_bps_hour)} / short ${numberText(execution.borrow_short_bps_hour)} bps/h · ${execution.use_leverage ? execution.leverage + '×' : '1×'} · ${execution.allow_short ? 'shorts allowed' : 'long only'} · confidence ≥ ${numberText(execution.min_confidence)}`;
  }
  function record(run) {
    if (!run || runs.some((r) => r.id === run.id)) return;
    runs = [run, ...runs].slice(0, 12); save();
  }
  function stage(run, row) {
    const values = handoffValues(run, row);
    if (!values) { inspect('Handoff unavailable', 'This result has no complete pinned context, is partial, or predates the new host. Rerun it before staging a paper trial.'); return; }
    draft = { run, row }; save();
    location.hash = 'soltui/forward';
    renderDraft();
  }
  function renderDraft() {
    const target = $('#deskDraft');
    clear(target); target.hidden = !draft;
    if (!draft) return;
    target.append(el('h2', { text: `Paper draft · ${draft.row.label}` }),
      note(`From ${draft.run.context.asset} / ${draft.run.context.interval} historical run ${draft.run.context.run_id ?? draft.run.id}. Nothing has started.`),
      note(costText(draft.run.context.execution)),
      note('Prospective horizons are separate from historical bars. Review the pinned snapshot and horizon before preparing; then explicitly start checking.'),
      action('Review pinned paper setup', () => choose('forwardtest.start', handoffValues(draft.run, draft.row)), true),
      action('Inspect source snapshot', () => inspect('Pinned handoff evidence', draft.run.context)),
      action('Discard draft', () => { draft = null; save(); renderDraft(); }));
  }
  function backtesting(target) {
    const status = data['backtest.status'];
    const context = runs[0]?.context;
    const actual = settings;
    target.append(el('div', { class: 'kpis' },
      kpi('Native-session sweep', status ? (status.running ? 'Running' : status.phase ?? 'Idle') : 'Unavailable', status?.title ?? failures['backtest.status'] ?? 'Read the current owner process'),
      kpi('Progress', status ? `${status.done ?? '—'} / ${status.total ?? '—'}` : 'Unavailable', 'Cancellation stops at a configuration boundary'),
      kpi('Saved run snapshots', String(runs.length), 'Saved in this browser · source context retained'),
      kpi('Current backend asset', actual?.asset ?? 'Unavailable', `${actual?.interval ?? '—'} · historical settings are independent of the live-view asset`)));
    target.append(buttons([['New backtest', 'backtest.run', {}, true], ['Review dates & costs', 'settings.save'], ['Edit roster', 'roster.list'], ['Inspect research queue', 'queue.progress'], ['Review cancel sweep', 'backtest.cancel']]));
    if (actual) target.append(note(`Run settings: ${actual.asset} / ${actual.interval} · ${actual.start || 'beginning'} to ${actual.end || 'end of cache'} · capital ${numberText(actual.capital)}.`));
    const section = el('div', { class: 'card' }, el('div', { class: 'card-head' }, el('h2', { text: 'Historical evidence' }),
      action('Compare selected runs', () => compare())), note('CPCV results · net returns include recorded costs.'));
    if (!runs.length) section.append(note('No versioned sweep is saved in this browser or native session yet. Run a backtest explicitly. Existing research remains available in the queue, strategy history and All tools.'));
    if (runs.length) section.append(tableScrollHint());
    for (const run of runs) {
      const check = el('input', { 'aria-label': `Compare run ${run.context.run_id ?? run.id}` }); check.type = 'checkbox';
      check.checked = selected.has(run.id);
      check.onchange = () => { check.checked ? selected.add(run.id) : selected.delete(run.id); save(); };
      const header = el('div', { class: 'card-head' }, el('label', { class: 'row' }, check,
        `${run.context.asset} / ${run.context.interval} · ${stamp(run.context.created_at)}${run.error ? ' · FAILED / PARTIAL' : run.cancelled ? ' · CANCELED / PARTIAL' : ''}`),
        action('Costs & provenance', () => inspect('Backtest snapshot', run.context)));
      const runCard = el('article', { class: 'desk-run', dataset: { runId: run.id } }, header, note(costText(run.context.execution)));
      if (run.context.data_selection) {
        const w = run.context.data_selection;
        runCard.append(note(`Gap-free window: ${new Date(w.first_ts * 1000).toISOString()} to ${new Date(w.last_ts * 1000).toISOString()} · ${w.selected_bars} of ${w.source_bars} bars · ${w.gaps_excluded} gaps outside the window`));
      }
      runCard.append(el('div', { class: 'table-wrap' }, table([
        { label: 'Strategy', value: (r) => r.label }, { label: 'Median path net', value: (r) => percentText(r.median_return) },
        { label: 'Median Sharpe', value: (r) => numberText(r.median_sharpe) }, { label: 'Sharpe IQR', value: (r) => numberText(r.iqr) },
        { label: 'Positive paths', value: (r) => percentText(r.frac_positive) }, { label: 'Aggregate trades', value: (r) => numberText(r.trades, 0) },
        { label: 'Next step', value: (r) => action('Stage paper trial', () => stage(run, r)) },
      ], run.rows)));
      if (run.skipped.length) runCard.append(note(`Skipped: ${run.skipped.map((r) => `${r.label}: ${r.reason}`).join(' · ')}`));
      section.append(runCard);
    }
    section.append(note('Drawdown, equity and itemized costs are unavailable. Inspect a run for provenance.'));
    target.append(section, buttons([['Replay a decision', 'paper.start'], ['Strategy history', 'strategies.history'], ['Cumulative research', 'cumulative.summary'], ['Experiment workbench', 'experiments.list']]));
    const archives = data['cumulative.summary']?.files ?? [];
    if (archives.length) target.append(el('div', { class: 'card' }, el('h2', { text: 'Existing research archives' }),
      note('Archives retain their original assumptions.'),
      tableScrollHint(), el('div', { class: 'table-wrap' }, table([
        { label: 'Source', value: (r) => r.source }, { label: 'Rankable configurations', value: (r) => numberText(r.rankable, 0) },
        { label: 'Below evidence floor', value: (r) => numberText(r.below_floor, 0) },
        { label: 'Recorded median Sharpe', value: (r) => numberText(r.median_sharpe) },
        { label: 'Provenance', value: (r) => action('Inspect archive summary', () => inspect('Original research summary · not a current-engine rerun', r)) },
      ], archives))));

  }
  function compare() {
    const chosen = runs.filter((r) => selected.has(r.id));
    const summary = comparisonStatus(chosen);
    const rows = chosen.flatMap((run) => run.rows.map((r) => ({ run: run.context.run_id ?? run.id,
      asset: run.context.asset, label: r.label, median_path_net: percentText(r.median_return), median_sharpe: r.median_sharpe,
      sharpe_iqr: r.iqr, aggregate_trades: r.trades, partial: run.cancelled })));
    inspect('Saved comparison', { compatibility: summary, aggregation: 'Original recorded summaries, not a merged portfolio or a new ranking', rows });
  }
  function forward(target) {
    const state = data['forwardtest.state'];
    const rows = data['forwardtest.status']?.rows ?? [];
    target.append(el('div', { class: 'kpis' },
      kpi('Native-session checks', state ? (state.running ? 'Running' : state.prepared ? 'Prepared' : 'Stopped') : 'Unavailable', 'Ends when its owning native session ends'),
      kpi('Saved trial rows', data['forwardtest.status'] ? String(rows.length) : 'Unavailable', `${asset()} · separate trial / horizon records`),
      kpi('Active tuning', state?.optimize == null ? 'Unavailable' : state.optimize ? 'Enabled' : 'Off', 'Adoption changes are kept in the saved trial history'),
      kpi('Paper entry confidence', state?.execution ? numberText(state.execution.min_confidence) : 'Unavailable', 'Separate from live vote accuracy and sample floors')));
    target.append(buttons([['New paper setup', 'forwardtest.start', {}, true], ['Start prepared checks', 'forwardtest.run'], ['Review stop checks', 'forwardtest.stop'], ['Review saved session', 'forwardtest.state'], ['Resume saved session', 'forwardtest.restore']]));
    if (state?.execution) target.append(note(costText(state.execution)));
    target.append(note('Paper checks. Stop applies to this session only.'));
    const section = el('div', { class: 'card' }, el('h2', { text: `${asset()} prospective evidence` }));
    if (!rows.length) section.append(note(failures['forwardtest.status'] ?? 'No saved trial results for this asset. Prepare a paper setup explicitly; reading this view starts nothing.'));
    else section.append(tableScrollHint(), el('div', { class: 'table-wrap' }, table([
      { label: 'Trial', value: (r) => forwardColumns(r).label }, { label: 'Horizon (minutes)', value: (r) => String(forwardColumns(r).horizon) },
      { label: 'Resolved', value: (r) => numberText(r.resolved, 0) }, { label: 'Accuracy', value: (r) => finite(r.correct) && finite(r.resolved) && r.resolved > 0 ? `${numberText(100 * r.correct / r.resolved)}% (${r.correct}/${r.resolved})` : 'Unavailable' },
      { label: 'Pending', value: (r) => numberText(r.pending, 0) }, { label: 'Net paper return', value: (r) => percentText(r.net_pct) },
      { label: 'Evidence', value: (r) => action('Inspect trial', () => inspect('Saved forward trial / horizon', r)) },
    ], rows)));
    section.append(note('Accuracy describes resolved predictions; it is not a profit probability.'));
    target.append(section, buttons([['Current predictions', 'forwardtest.predictions', { asset: asset() }], ['Compound paper evidence', 'compound.forward_status', { asset: asset() }], ['Training history', 'compound.results', { asset: asset() }]]));
  }
  function bots(target) {
    const prices = data['prices.status'], fwd = data['forwardtest.state'], sweep = data['backtest.status'];
    const trainer = data['compound.unattended_status'], schedule = data['bots.schedule_status'];
    target.append(el('div', { class: 'kpis' },
      kpi('Recorder', prices ? (prices.running ? 'Running' : 'Stopped') : 'Unavailable', prices ? `Snapshot age ${numberText(prices.snapshot_age_s, 1)}s · ${prices.live ? 'fresh' : 'stale / unavailable'}` : failures['prices.status']),
      kpi('Session paper checks', fwd ? (fwd.running ? 'Running' : 'Stopped') : 'Unavailable', 'Session-owned; not a detached service'),
      kpi('Backtest worker', sweep ? (sweep.running ? 'Running' : sweep.phase ?? 'Idle') : 'Unavailable', sweep?.title ?? 'Session-owned research'),
      kpi('Money permission', 'Paper research', 'Bot simulations do not place orders; execution controls are separate')));
    const rows = [
      { process: 'Price recorder', state: prices?.running, output: prices ? `${numberText(prices.snapshot_age_s, 1)}s snapshot age` : 'Unavailable', lifetime: 'Recorder service / detached process', tool: 'prices.status' },
      { process: 'Forward checks', state: fwd?.running, output: fwd?.busy ? 'Checking' : 'Inspect last checks', lifetime: 'Native-session owned', tool: 'forwardtest.state' },
      { process: 'Historical sweep', state: sweep?.running, output: sweep?.title ?? 'Unavailable', lifetime: 'Native-session owned', tool: 'backtest.status' },
      { process: `${asset()} compound trainer`, state: trainer?.running, output: trainer?.last_line ?? trainer?.last_error ?? 'Inspect log and last output independently', lifetime: 'Detached; survives browser closure', tool: 'compound.unattended_status', params: { asset: asset() } },
      { process: 'Bot optimizer schedule', state: schedule?.running ?? schedule?.enabled, output: 'Inspect next run and last result', lifetime: 'Scheduler; lifetime supplied by backend', tool: 'bots.schedule_status' },
    ];
    target.append(el('div', { class: 'card' }, el('h2', { text: 'Process responsibilities' }),
      tableScrollHint(),
      el('div', { class: 'table-wrap' }, table([
        { label: 'Process', value: (r) => r.process }, { label: 'Liveness', value: (r) => typeof r.state === 'boolean' ? (r.state ? 'Running' : 'Stopped') : 'Unavailable' },
        { label: 'Last output / freshness', value: (r) => r.output }, { label: 'Lifetime', value: (r) => r.lifetime },
        { label: 'Evidence', value: (r) => action('Inspect', () => choose(r.tool, r.params ?? {})) },
      ], rows)), note('An alive process can have stale output. A local stop does not prove venue cancellation; unknown submits require reconciliation.', true)));
    const sim = data['bots.overview']?.bots ?? [];
    if (sim.length) target.append(el('div', { class: 'card' }, el('h2', { text: 'Paper bot research' }), tableScrollHint(), el('div', { class: 'table-wrap' }, table([
      { label: 'Bot', value: (r) => r.label ?? r.bot }, { label: 'Purpose', value: (r) => r.about },
      { label: 'Last optimizer verdict', value: (r) => r.optimize ?? 'Unavailable' },
      { label: 'Research', value: (r) => action('Inspect bot', () => choose('bots.config', { bot: r.bot, asset: asset() })) },
    ], sim))));
    target.append(buttons([['Recorder controls', 'prices.ensure'], ['Bot ranking / audit', 'bots.rank_coins'], ['Training status', 'compound.unattended_status', { asset: asset() }], ['Schedules', 'bots.schedule_status']]));
    target.append(note('Full standalone executor telemetry is not exposed by this host. Use Wallets & orders for existing reviewed manual order state/reconciliation. The extension Trigger grid remains experimental and live signing blocked; Aero liquidity stays archived.'));
  }
  function render() {
    if (disposed) return;
    const target = $('#deskContent');
    const active = document.activeElement;
    const identity = (node) => [node.tagName, node.getAttribute('aria-label') ?? node.textContent,
      node.closest('tr')?.firstElementChild?.textContent ?? '', node.closest('[data-run-id]')?.dataset.runId ?? ''];
    const focus = target.contains(active) ? identity(active) : null;
    clear(target);
    host.hidden = !['research', 'forward', 'bots'].includes(page);
    renderDraft(); $('#deskDraft').hidden = page !== 'forward' || !draft;
    if (page === 'research') backtesting(target);
    if (page === 'forward') forward(target);
    if (page === 'bots') bots(target);
    const errors = Object.entries(failures);
    if (errors.length && DESK_PAGES.has(page)) target.append(note(`Some evidence is unavailable: ${errors.map(([name, error]) => `${name}: ${error}`).join(' · ')}. Reconnect to retry reads; no action was retried.`, true));
    if (focus) [...target.querySelectorAll('button,input,select,a')].find((node) => JSON.stringify(identity(node)) === JSON.stringify(focus))?.focus({ preventScroll: true });
  }
  function route(next) {
    epoch++; renderedRead = ''; page = next; if ($('#soltuiToolbox')) $('#soltuiToolbox').dataset.focused = 'false'; data = {}; failures = {}; lastAt = null;
    $('#deskTitle').textContent = TITLE[page] ?? 'All tools & library';
    $('#deskPurpose').textContent = PURPOSE[page] ?? 'Every installed tool, with the same parameters and execution gates.';
    $('#deskReadRefresh').hidden = !DESK_READS[page];
    $('#deskLiveMetrics').hidden = page !== 'signal';
    render(); message(); save(); refresh();
  }
  function receive(env, shouldRender = true) {
    const run = runFromEnvelope(env); record(run);
    if (env?.command === 'forwardtest.start' && env.ok && page === 'forward' && !$('#view-soltui').hidden && !document.hidden) {
      inspect('Paper setup prepared', { ...env.result, next: 'Use Start prepared checks explicitly. Preparing did not start a worker.' });
    }
    if (shouldRender && DESK_PAGES.has(page)) { render(); if (!busy) refresh(); }
  }
  function live(snapshot) {
    liveSnapshot = snapshot;
    const q = snapshot.quote, a = snapshot.aggregate;
    clear($('#deskLiveMetrics'),
      kpi(`${snapshot.asset} / USD · ${snapshot.source === 'Jupiter' ? 'Jupiter reference' : snapshot.fresh ? 'current quote' : 'last known / unavailable'}`, finite(q?.mid ?? q?.last) ? `$${numberText(q.mid ?? q.last, 4)}` : 'Unavailable', snapshot.source === 'Jupiter' ? 'Jupiter reference price · request time shown below' : `Coinbase recorder · ${numberText(q?.quote_age_s, 1)}s old`),
      kpi('Directional agreement', a?.available ? `${numberText(a.score, 0)} / 100` : 'Unavailable', a?.available ? `${a.label} · not success probability` : 'No qualifying current predictions'),
      kpi('Eligible strategies', a?.available ? String(a.strategies) : '0', 'Equal strategy weights; inspect horizon eligibility'),
      kpi('Prediction snapshot', snapshot.updated ? new Date(snapshot.updated).toISOString().slice(11, 19) + ' UTC' : 'Unavailable', 'Saved closed-candle predictions · refresh every 10s'));
    const readout = $('#deskInterpretation');
    if (readout) { readout.textContent = a?.available ? `${a.label} · ${numberText(a.score, 0)} / 100` : 'Agreement unavailable'; readout.className = `desk-score ${a?.available ? 'signal-score-' + a.color : 'signal-score-gray'}`; }
  }
  function jobs(names) {
    for (const name of names) if (!activity.some((r) => r.name === name && r.state === 'Running')) activity.unshift({ name, state: 'Running', at: Date.now() });
    for (const r of activity) if (r.state === 'Running' && !names.includes(r.name)) r.state = 'Returned · inspect result';
    activity.splice(12);
    clear($('#deskActivity'), ...activity.map((r) => el('span', { class: 'chip plain', text: `${r.name} · ${r.state}` })));
    if (!activity.length) $('#deskActivity').textContent = 'No actions requested in this dashboard session.';
  }
  function findTools() {
    if ($('#view-soltui').hidden) { location.hash = 'soltui/all'; setTimeout(findTools, 0); return; }
    const dialog = $('#deskSearchDialog'), input = $('#deskSearchInput'), target = $('#deskSearchResults');
    const trigger = document.activeElement;
    const paint = () => {
      const q = input.value.toLowerCase().trim();
      clear(target);
      for (const [key, title] of Object.entries(TITLE).filter(([, title]) => title.toLowerCase().includes(q))) target.append(action(title, () => { dialog.close(); location.hash = `soltui/${key}`; }));
      for (const c of commands.filter((c) => `${c.name} ${c.describe}`.toLowerCase().includes(q)).slice(0, 30)) {
        const b = action(`${c.name}${commandBlock(c) ? ' · Archived / unavailable' : ''}`, () => { dialog.close(); choose(c.name); });
        b.disabled = !!commandBlock(c); target.append(b);
      }
      if (!target.children.length) target.append(note('No matching tools. Try another keyword.'));
    };
    input.value = ''; input.oninput = paint; paint();
    dialog.onclose = () => trigger?.isConnected ? trigger.focus() : $('#deskTitle').focus(); dialog.showModal(); input.focus();
  }
  $('#deskDetailClose').onclick = () => $('#deskDetail').close();
  $('#deskSearchClose').onclick = () => $('#deskSearchDialog').close();
  $('#deskFind')?.addEventListener('click', findTools);
  $('#deskWhyScore').onclick = () => inspect('Directional agreement and eligibility', {
    explanation: 'Average current eligible horizon votes within each strategy, then average strategies equally. UP=+1, DOWN=−1, FLAT=0. Strong Buy ≥60; Buy ≥20; Sell ≤−20; Strong Sell ≤−60. Missing evidence is unavailable. Both strategy-wide and contributed-horizon records must meet accuracy/sample floors. Paper entry confidence is separate.',
    observed: liveSnapshot?.aggregate ?? null,
  });
  $('#deskReadRefresh').onclick = refresh;
  $('#deskDensity')?.addEventListener('change', () => { (root.querySelector('body') ?? document.body).dataset.density = $('#deskDensity').value; save(); });
  const keydown = (e) => { if (e.key === 'Escape') { const dialog = $('#deskSearchDialog').open ? $('#deskSearchDialog') : $('#deskDetail').open ? $('#deskDetail') : null; if (dialog) { e.preventDefault(); dialog.close(); return; } } if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k' && !$('#deskDetail').open && !$('#deskSearchDialog').open) { e.preventDefault(); findTools(); } };
  window.addEventListener('keydown', keydown);
  const timer = setInterval(() => { if (!disposed && !document.hidden && !$('#view-soltui').hidden) refresh(); }, 10_000);
  return { restore, route, live, receive, jobs, inspect, commands(list) { commands = list; },
    assetChanged() { epoch++; data = {}; failures = {}; liveSnapshot = null; live({ asset: asset(), quote: null, aggregate: null }); render(); save(); refresh(); },
    dispose() { disposed = true; epoch++; clearInterval(timer); window.removeEventListener('keydown', keydown); } };
}
