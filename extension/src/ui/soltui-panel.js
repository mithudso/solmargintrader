/** Dashboard workspace over the installed TUI registry. Results are always text nodes. */
import { mountSignalDesk } from './signal-desk.js';
import { commandBlock, eligibilityReason } from './desk-model.js';
import { el, clear, table, lineChart } from './ui-kit.js';
import { aggregatePredictions, scoreText, appendScoreTick, renderScoreChart } from './live-score.js';
import { WORKSPACES, filterCommands, workspaceFor, cellText, columnsFor, rowsToCsv, resultTables, valuesFromRow, seriesFromRows } from './workspace-model.js';

const send = (msg) => chrome.runtime.sendMessage(msg);
const LIVE_PREDICTIONS_MS = 10_000;
const POLLABLE = new Set(['prices.status', 'forwardtest.predictions', 'forwardtest.state', 'forwardtest.status',
  'backtest.status', 'backtest.results', 'queue.progress', 'compound.autopilot_status', 'compound.unattended_status',
  'compound.forward_status', 'bots.progress', 'bots.fit_status', 'bots.schedule_status']);

export function coerceField(param, raw) {
  if (param.type === 'bool') {
    if (raw === true || raw === 'true') return { value: true };
    if (raw === false || raw === 'false') return { value: false };
    return param.required ? { error: `${param.name} is required` } : { skip: true };
  }
  const text = typeof raw === 'string' ? raw.trim() : '';
  // Document bodies must preserve whitespace, and an explicit empty document is valid.
  if (param.name === 'text' && param.type === 'string' && typeof raw === 'string' && (param.required || text !== '')) return { value: raw };
  if (text === '') return param.required ? { error: `${param.name} is required` } : { skip: true };
  if (param.type === 'number') {
    const n = Number(text);
    return Number.isFinite(n) ? { value: n } : { error: `${param.name} must be a number` };
  }
  if (param.type === 'json') {
    try { return { value: JSON.parse(text) }; }
    catch { return { error: `${param.name} must be valid JSON` }; }
  }
  return { value: text };
}

export function buildParams(command, values, { confirmed = false, emptyFields = [] } = {}) {
  const params = {};
  const errors = [];
  for (const param of command.params ?? []) {
    if (param.name === 'confirm') continue;
    if (param.type === 'string' && emptyFields.includes(param.name)) { params[param.name] = ''; continue; }
    const out = coerceField(param, values[param.name]);
    if (out.error) errors.push(out.error);
    else if (!out.skip) params[param.name] = out.value;
  }
  if (confirmed === true) params.confirm = true;
  return { params, errors };
}

export const commandNames = (commands) => new Set((commands ?? []).map((c) => c.name));

function fieldFor(param) {
  const labels = { labels: 'Strategy roster labels (optional)', use_leverage: 'Use leveraged paper positions', leverage: 'Leverage multiplier', allow_short: 'Allow paper shorts', min_confidence: 'Minimum paper-entry confidence', horizons: 'Forecast horizons (minutes)', scope: 'Strategy scope', coins: 'Coins to observe', optimize: 'Enable adaptive tuning', source_label: 'Pinned source strategy', snapshot: 'Pinned backtest snapshot' };
  const label = el('label', { text: `${labels[param.name] ?? param.name}${param.required ? ' *' : ''}` });
  let input;
  if (param.type === 'bool') {
    input = el('select', {}, [el('option', { value: '', text: 'Use saved/default value' }),
      el('option', { value: 'true', text: 'True / on' }), el('option', { value: 'false', text: 'False / off' })]);
  } else if (param.type === 'json' || param.name === 'text') {
    input = el('textarea', { rows: param.name === 'text' ? 12 : 4, spellcheck: false });
    label.className = 'full';
  } else {
    input = el('input', { spellcheck: false });
    input.type = param.type === 'number' ? 'number' : 'text';
    if (param.type === 'number') input.step = 'any';
  }
  input.name = param.name;
  label.append(input, el('span', { class: 'note', text: param.describe }));
  if (param.type === 'string' && !param.required) {
    const clearBox = el('input');
    clearBox.type = 'checkbox';
    clearBox.setAttribute('aria-label', `Clear ${param.name}`);
    const clearLabel = el('span', { class: 'row note' }, clearBox, 'Send an empty value / clear saved value');
    input.clearBox = clearBox;
    clearBox.addEventListener('change', () => { input.disabled = clearBox.checked; });
    label.append(clearLabel);
  }
  return { label, input };
}

function download(name, content, mime = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const a = el('a', { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderResultTable(target, data, useRow, state = {}) {
  const { rows, path } = data;
  const columns = columnsFor(rows);
  let sort = state.sort ?? null;
  let direction = state.direction ?? 1;
  let page = state.page ?? 0;
  const filter = el('input', { placeholder: 'Filter rows', 'aria-label': `Filter ${path}` });
  filter.type = 'search';
  filter.value = state.query ?? '';
  const output = el('div', { class: 'table-wrap' });
  const count = el('span', { class: 'note' });
  const prev = el('button', { text: 'Previous' });
  const next = el('button', { text: 'Next' });
  const csv = el('button', { text: 'Export CSV', class: 'small' });
  let shown = rows;
  function paint() {
    const q = filter.value.toLowerCase();
    shown = rows.filter((r) => columns.some((k) => cellText(r[k]).toLowerCase().includes(q)));
    if (sort) shown = [...shown].sort((a, b) => {
      const x = a[sort], y = b[sort];
      if (x == null) return 1;
      if (y == null) return -1;
      return direction * (typeof x === 'number' && typeof y === 'number' ? x - y : cellText(x).localeCompare(cellText(y), undefined, { numeric: true }));
    });
    const pages = Math.max(1, Math.ceil(shown.length / 100));
    page = Math.min(page, pages - 1);
    const cols = columns.map((k) => ({ label: k, value: (r) => cellText(r[k]) }));
    cols.push({ label: 'Detail', value: (r) => el('button', { class: 'small', text: 'Inspect / use row', onclick: () => useRow(r) }) });
    const t = table(cols, shown.slice(page * 100, (page + 1) * 100));
    for (const [i, th] of [...t.querySelectorAll('th')].entries()) {
      if (i >= columns.length) continue;
      const key = columns[i];
      th.setAttribute('aria-sort', sort === key ? (direction === 1 ? 'ascending' : 'descending') : 'none');
      clear(th, el('button', { class: 'link', text: `${key}${sort === key ? (direction === 1 ? ' ↑' : ' ↓') : ''}`, onclick: () => {
        direction = sort === key ? -direction : 1; sort = key; paint();
      } }));
    }
    clear(output, t);
    count.textContent = `${shown.length} of ${rows.length} rows · page ${page + 1}/${pages}`;
    Object.assign(state, { sort, direction, page, query: filter.value });
    prev.disabled = page === 0;
    next.disabled = page + 1 >= pages;
  }
  filter.addEventListener('input', () => { page = 0; paint(); });
  prev.addEventListener('click', () => { page -= 1; paint(); });
  next.addEventListener('click', () => { page += 1; paint(); });
  csv.addEventListener('click', () => download(`${path.replace(/[^a-z0-9_-]/gi, '-')}.csv`, rowsToCsv(shown)));
  const node = el('div', { class: 'card result-table' },
    el('div', { class: 'card-head' }, el('h3', { text: path }), csv),
    el('div', { class: 'row' }, filter, count, prev, next), output);
  const series = seriesFromRows(rows);
  if (series.length > 1) node.append(lineChart(series, { label: path, format: cellText }));
  target.append(node);
  paint();
}

function renderHeatmap(target, result, useRow) {
  for (const group of result?.groups ?? []) {
    const points = new Map((group.points ?? []).map((p) => [JSON.stringify([p.x, p.y]), p]));
    const values = (group.points ?? []).filter((p) => p.observations > 0 && Number.isFinite(p.value)).map((p) => Math.abs(p.value));
    const maximum = Math.max(1e-12, ...values);
    const head = el('tr', {}, el('th', { text: `${result.y} / ${result.x}` }), ...(group.x_values ?? []).map((x) => el('th', { text: cellText(x) })));
    const body = (group.y_values ?? []).map((y) => el('tr', {}, el('th', { text: cellText(y) }), ...(group.x_values ?? []).map((x) => {
      const p = points.get(JSON.stringify([x, y]));
      const measured = p?.observations > 0 && typeof p.value === 'number' && Number.isFinite(p.value);
      const cell = el('td', { class: measured ? (p.value >= 0 ? 'heat-positive' : 'heat-negative') : 'muted' });
      if (measured) {
        cell.style.backgroundColor = `color-mix(in srgb, var(${p.value >= 0 ? '--pos' : '--neg'}) ${15 + 35 * Math.abs(p.value) / maximum}%, transparent)`;
        cell.append(el('button', { class: 'link', text: `${p.value.toPrecision(5)} (n=${p.observations})`, title: `stdev ${p.stdev ?? 'unknown'}; min ${p.min ?? 'unknown'}; max ${p.max ?? 'unknown'}`, onclick: () => useRow(p) }));
      } else cell.textContent = 'Not measured';
      return cell;
    })));
    target.append(el('div', { class: 'card' }, el('h3', { text: `${result.metric} · ${result.split} · observed cells only` }),
      el('p', { class: 'note', text: `Fixed: ${JSON.stringify(group.fixed ?? {})} · ${group.observed_points}/${group.possible_points} observed · holdout excluded` }),
      el('div', { class: 'table-wrap' }, el('table', {}, el('thead', {}, head), el('tbody', {}, body)))));
  }
}

export function mountSoltuiPanel(root = document, transport = send) {
  const $ = (s) => root.querySelector(s);
  const select = $('#soltuiCommand');
  const describe = $('#soltuiDescribe');
  const form = $('#soltuiForm');
  const result = $('#soltuiResult');
  const status = $('#soltuiStatus');
  const workspace = $('#soltuiWorkspace');
  const search = $('#soltuiSearch');
  const tools = $('#soltuiTools');
  const rich = $('#soltuiTables');
  const selected = $('#soltuiSelection');
  const poll = $('#soltuiPoll');
  const pending = new Map();
  const drafts = new Map();
  const results = new Map();
  const tableStates = new Map();
  const stateFor = (key) => { if (!tableStates.has(key)) tableStates.set(key, {}); return tableStates.get(key); };
  let commands = [];
  let inputs = new Map();
  let confirmBox = null;
  let runButton = null;
  let editor = null;
  let editorBase = null;
  let documentPath = null;
  let documentEpoch = 0;
  let lastEnvelope = null;
  let generation = null;
  let disposed = false;
  let heartbeat;
  let pollTimer;
  let liveTimer;
  let predictionTimer;
  let liveBusy = false;
  let nowBusy = false;
  let nowLoaded = false;
  let liveAsset = '';
  let livePoints = [];
  let predictionsAt = 0;
  let predictionAttempted = false;
  let predictionRows = [];
  let voting = { min_accuracy: 60, min_resolved: 20 };
  let liveGeneration = 0;
  let votingSaving = false;
  let liveRefreshRequested = false;
  const session = crypto.randomUUID();
  $('#soltui').dataset.session = session;
  const current = () => commands.find((c) => c.name === select.value);
  const desk = mountSignalDesk(root, { ask, openTool: choose, refreshLive, transport });
  let deskPage = null;

  async function ask(command, params = {}) {
    const res = await transport({ type: 'soltuiCall', command, params });
    if (!res?.ok) throw new Error(res?.error ?? 'The extension did not answer.');
    return res.result;
  }
  function remember() {
    const vals = Object.fromEntries([...inputs].map(([k, input]) => [k, input.value]));
    if (form.dataset.command) drafts.set(form.dataset.command, { values: vals, emptyFields: [...inputs].filter(([, input]) => input.clearBox?.checked).map(([k]) => k) });
  }
  function clearConfirmation() {
    if (confirmBox) {
      confirmBox.checked = false;
      if (runButton) runButton.disabled = true;
    }
  }
  function setValues(values) {
    clearConfirmation();
    for (const [k, v] of Object.entries(values)) {
      const input = inputs.get(k);
      if (input) {
        input.value = typeof v === 'boolean' ? String(v) : v ?? '';
        if (input.clearBox) input.clearBox.checked = false;
        input.disabled = false;
      }
    }
  }
  function renderForm() {
    form.replaceChildren();
    inputs = new Map();
    confirmBox = null;
    const c = current();
    form.dataset.command = c?.name ?? '';
    if (!c) { describe.textContent = ''; return; }
    const live = /^(coinbase|jupiter)\.order_/.test(c.name) && !/preview|status|state|reconcile/.test(c.name);
    describe.textContent = `${c.name === 'docs.search' ? 'Explicit search: every mode checks the idle index; semantic mode can start Ollama. ' : ''}${c.describe}${c.read_only ? ' · Read only.' : ' · Changes state.'}${c.long_running ? ' May take minutes; other tools stay available.' : ''}`;
    describe.className = live ? 'banner danger' : 'note';
    for (const p of c.params ?? []) {
      if (p.name === 'confirm') continue;
      const { label, input } = fieldFor(p);
      inputs.set(p.name, input);
      form.append(label);
    }
    const draft = drafts.get(c.name);
    setValues(draft?.values ?? {});
    for (const k of draft?.emptyFields ?? []) {
      const input = inputs.get(k);
      if (input?.clearBox) { input.clearBox.checked = true; input.disabled = true; }
    }
    if (c.requires_confirm) {
      const label = el('label', { class: 'full check' });
      confirmBox = el('input');
      confirmBox.type = 'checkbox';
      label.append(confirmBox, `I reviewed ${c.name} and its parameters. I authorize this action${live ? ' with real funds' : ''}.`);
      form.append(label);
    }
    runButton = el('button', { class: live ? 'danger' : 'primary', text: live ? 'Submit live order' : c.read_only ? 'Run / refresh' : 'Run action' });
    runButton.type = 'submit';
    runButton.disabled = pending.has(c.name) || !!confirmBox || !!commandBlock(c);
    if (commandBlock(c)) { describe.textContent = commandBlock(c); for (const input of inputs.values()) input.disabled = true; }
    if (confirmBox) confirmBox.addEventListener('change', () => { runButton.disabled = pending.has(c.name) || !confirmBox.checked || !!commandBlock(c); });
    form.append(runButton);
    poll.disabled = !POLLABLE.has(c.name) || c.read_only !== true || c.requires_confirm;
    poll.checked = false;
  }
  function choose(name, values = {}) {
    if (!commandNames(commands).has(name)) return;
    remember();
    if (name === 'forwardtest.start' && Object.hasOwn(values, 'snapshot')) drafts.delete(name);
    select.value = name;
    renderForm();
    if (results.has(name)) display(results.get(name));
    setValues(values);
  }
  function renderTools() {
    const spec = WORKSPACES.find((w) => w.id === workspace.value) ?? WORKSPACES.at(-1);
    $('#soltuiWorkspaceDetail').textContent = spec.detail;
    $('#soltuiLive').hidden = !['signal', 'now'].includes(spec.id);
    if (deskPage !== spec.id) { deskPage = spec.id; desk.route(spec.id); }
    if (!['signal', 'research', 'forward', 'bots'].includes(spec.id) && $('#soltuiToolbox')) $('#soltuiToolbox').open = true;
    if (commands.length && !predictionAttempted && liveVisible()) refreshLive();
    $('#soltuiNowSummary').hidden = spec.id !== 'now';
    if (spec.id === 'now' && commands.length && !nowLoaded) refreshNow();
    const filtered = filterCommands(commands, spec.id, search.value);
    clear(tools, ...filtered.map((c) => el('button', { class: 'tool-card', title: commandBlock(c) ?? c.describe, disabled: !!commandBlock(c), onclick: () => choose(c.name) },
      el('strong', { text: c.name }), el('small', { text: `${commandBlock(c) ? 'Archived / unavailable' : c.read_only ? 'Read' : 'Action'}${c.requires_confirm ? ' · Confirm' : ''} — ${c.describe}` }))));
    if (!filtered.length) tools.append(el('p', { class: 'empty', text: 'No matching tools in this workspace. Try All tools.' }));
  }
  function applyRoute() {
    const parts = location.hash.slice(1).split('/');
    if (parts[0] !== 'soltui' || !WORKSPACES.some((w) => w.id === parts[1])) return;
    workspace.value = parts[1];
    renderTools();
    const c = filterCommands(commands, workspace.value)[0];
    if (c && workspace.value !== workspaceFor(select.value)) choose(c.name);
  }
  async function openDocument(path) {
    if (editor && editor.value !== editorBase) {
      selected.textContent = 'Save your edited document before opening another document.';
      return;
    }
    const epoch = ++documentEpoch;
    const env = await ask('docs.read', { path });
    if (epoch !== documentEpoch || (editor && editor.value !== editorBase)) return;
    if (!env.ok) { selected.textContent = env.error?.message ?? 'Could not open document.'; return; }
    documentPath = path;
    editorBase = env.result.text;
    editor = $('#soltuiEditor');
    editor.value = editorBase;
    editor.readOnly = !env.result.editable;
    $('#soltuiEditorCard').hidden = false;
    $('#soltuiEditorPath').textContent = `${path} · ${env.result.editable ? 'Editable' : 'Read only'}`;
    $('#soltuiSave').disabled = !env.result.editable;
  }
  function useRow(row) {
    selected.textContent = JSON.stringify(row, null, 2);
    if (row.path && commandNames(commands).has('docs.read')) {
      openDocument(row.path).catch((e) => { selected.textContent = e.message; });
    }
    if (current()) setValues(valuesFromRow(current(), row));
    offerSubmit(row);
  }
  function offerSubmit(row) {
    $('#soltuiNext').replaceChildren();
    if (row.preview_id && /^(coinbase|jupiter)\.order_.*preview$/.test(lastEnvelope?.command ?? '')) {
      const venue = lastEnvelope.command.split('.')[0];
      $('#soltuiNext').append(el('button', { class: 'danger', text: `Review ${venue} submit form`, onclick: () => {
        choose(`${venue}.order_submit`, { preview_id: row.preview_id });
      } }));
    }
  }
  function display(env) {
    lastEnvelope = env;
    result.textContent = JSON.stringify(env, null, 2);
    rich.replaceChildren();
    $('#soltuiNext').replaceChildren();
    if (!env?.ok) {
      rich.append(el('p', { class: 'err', text: `${env?.error?.code ?? 'failed'}: ${env?.error?.message ?? 'No response'}` }));
      return;
    }
    const val = env.result;
    if (val !== null && typeof val !== 'object') rich.append(el('pre', { text: cellText(val) }));
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      const simple = Object.entries(val).filter(([, v]) => v === null || typeof v !== 'object');
      if (simple.length) {
        const dl = el('dl', { class: 'result-summary' });
        for (const [k, v] of simple) dl.append(el('dt', { text: k }), el('dd', { text: cellText(v) || '—' }));
        rich.append(dl);
      }
      if (val.preview_id) offerSubmit(val);
    }
    if (env.command === 'forwardtest.predictions') {
      const badge = el('div');
      paintAggregate(badge, aggregatePredictions(val?.rows ?? [], Date.now() / 1000, val?.voting ?? voting));
      rich.append(badge);
    }
    if (env.command === 'experiments.heatmap') renderHeatmap(rich, val, useRow);
    for (const t of resultTables(val)) renderResultTable(rich, t, useRow, stateFor(`${env.command}:${t.path}`));
    if (!rich.children.length) rich.append(el('p', { class: 'empty', text: 'No rows returned. See Raw response for the full envelope.' }));
    if (env.command === 'docs.read' && val?.path) openDocument(val.path).catch((e) => { selected.textContent = e.message; });
    $('#soltuiResultLabel').textContent = `${env.command} · ${new Date().toLocaleTimeString()}`;
  }
  function paintJobs() {
    desk.jobs([...pending.keys()]);
    clear($('#soltuiJobs'), ...[...pending.keys()].map((name) => el('span', { class: 'chip backtest', text: `${name} running` })));
  }
  async function run(c, params, polling = false) {
    if (pending.has(c.name) || commandBlock(c)) return;
    pending.set(c.name, true);
    paintJobs();
    if (select.value === c.name && runButton) runButton.disabled = true;
    if (!polling) result.textContent = 'Running…';
    $('#soltuiRunStatus').textContent = `${c.name} running…`;
    try {
      const env = await ask(c.name, params);
      if (disposed) return;
      $('#soltuiRunStatus').textContent = env?.ok ? `${c.name} completed.` : `${c.name}: ${env?.error?.message ?? 'No response'}`;
      results.set(c.name, env);
      desk.receive(env);
      if (results.size > 30) results.delete(results.keys().next().value);
      clear($('#soltuiHistory'), ...[...results].reverse().map(([name, saved]) => el('button', { class: 'small', text: `${name} ${saved?.ok ? '✓' : 'failed'}`, onclick: () => choose(name) })));
      // A response for a previous tool never replaces the current tool's view.
      if (select.value === c.name) display(env);
      if (!env?.ok) poll.checked = false;
    } catch (e) {
      poll.checked = false;
      $('#soltuiRunStatus').textContent = `${c.name} failed: ${e.message}. No automatic retry.`;
      if (select.value === c.name) result.textContent = `Failed: ${e.message}. Requests are never automatically retried.`;
    } finally {
      pending.delete(c.name);
      paintJobs();
      if (select.value === c.name) {
        if (confirmBox) confirmBox.checked = false;
        if (runButton) runButton.disabled = !!confirmBox || !!commandBlock(c);
      }
    }
  }
  async function refreshNow() {
    if (nowBusy || disposed) return;
    nowBusy = true;
    nowLoaded = true;
    const target = $('#soltuiNowSummary');
    clear(target);
    const names = WORKSPACES.find((w) => w.id === 'now').tools;
    try {
      await Promise.all(names.map(async (name) => {
        const c = commands.find((tool) => tool.name === name && tool.read_only && !tool.requires_confirm && !tool.long_running
          && !tool.params?.some((p) => p.required));
        if (!c) return;
        const value = el('div', { class: 'value', text: '…' });
        const sub = el('div', { class: 'sub' });
        const card = el('div', { class: 'kpi' }, el('div', { class: 'label', text: name }), value, sub,
          el('button', { class: 'small', text: 'Open tool', onclick: () => choose(name) }));
        target.append(card);
        try {
          const env = await ask(name);
          if (!env.ok) throw new Error(env.error?.message ?? 'Unavailable');
          const r = env.result;
          const running = r?.running;
          value.textContent = typeof running === 'boolean' ? (running ? 'Running' : 'Stopped')
            : (r?.phase ?? (r == null ? 'No saved data' : 'Available'));
          sub.textContent = r?.title ?? r?.message ?? r?.last_error ?? r?.label ?? 'Read only · open tool for details';
        } catch (e) { value.textContent = 'Unavailable'; sub.textContent = e.message; }
      }));
    } finally { nowBusy = false; }
  }
  function renderPredictionEvidence(target, rows, asset) {
    const input = el('input', { placeholder: 'Filter strategies', 'aria-label': 'Filter strategy evidence' });
    input.type = 'search';
    const state = stateFor(`live:${asset}`);
    input.value = state.query ?? '';
    const output = el('div', { class: 'table-wrap' });
    const count = el('p', { class: 'note', role: 'status' });
    const reset = el('button', { class: 'link', text: 'Clear filter' }); reset.type = 'button';
    const paint = () => {
      state.query = input.value;
      const shown = rows.filter((r) => String(r.label ?? '').toLowerCase().includes(input.value.toLowerCase()));
      const fmt = (n) => typeof n === 'number' && Number.isFinite(n) ? n.toFixed(1) : '—';
      const now = Date.now() / 1000;
      clear(output, table([
        { label: 'Strategy', value: (r) => r.label },
        { label: 'Prior accuracy', value: (r) => `${fmt(r.accuracy)}% · n=${r.resolved ?? '—'}` },
        ...[1, 5, 10, 30].map((h) => ({ label: `${h}m`, value: (r) => `${typeof r[`issued_${h}m`] === 'number' && typeof r[`expires_${h}m`] === 'number' && r[`issued_${h}m`] <= now && now < r[`expires_${h}m`] ? r[`pred_${h}m`] ?? 'Unavailable' : 'Unavailable / expired'} · ${fmt(r[`acc_${h}m`])}% · n=${r[`resolved_${h}m`] ?? '—'}` })),
        { label: 'Vote eligibility', value: (r) => eligibilityReason(r, voting, now) },
        { label: 'Evidence', value: (r) => { const button = el('button', { class: 'small', text: 'Inspect', onclick: () => desk.inspect('Strategy and horizon evidence', { asset, ...r, policy: voting, current: aggregatePredictions([r], Date.now() / 1000, voting) }) }); button.type = 'button'; return button; } },
      ], shown));
      count.textContent = shown.length ? `${shown.length} of ${rows.length} strategy rows · current eligibility uses both record and horizon floors` : 'No matching strategies. Clear the filter to recover.';
      reset.hidden = !input.value;
    };
    input.oninput = paint;
    reset.onclick = () => { input.value = ''; paint(); input.focus(); };
    target.append(el('div', { class: 'row' }, input, reset), count, output); paint();
  }
  function paintAggregate(target, aggregate) {
    target.className = `signal-score signal-score-${aggregate.color}`;
    target.textContent = `Aggregate score ${scoreText(aggregate)} / 100 · ${aggregate.available ? aggregate.label : 'Unavailable'} · ${aggregate.strategies} voting strategies / ${aggregate.votes} horizon votes · floor ${aggregate.min_accuracy}%, ${aggregate.min_resolved} resolved/horizon${aggregate.available ? '' : ' · No qualifying current predictions'}`;
    target.title = 'Average eligible current horizon votes within each strategy, then average strategies equally. Directional agreement, not a probability.';
  }
  async function refreshLive(force = false) {
    if (disposed) return;
    if (liveBusy || votingSaving) { if (force) liveRefreshRequested = true; return; }
    const contextGeneration = liveGeneration;
    const asset = $('#soltuiLiveAsset').value.trim().toUpperCase();
    if (!/^[A-Z0-9]{1,20}$/.test(asset)) { $('#soltuiLiveStatus').textContent = 'Enter a coin symbol such as SOL.'; return; }
    if (!['prices.status', 'forwardtest.predictions'].every((name) => commands.some((c) => c.name === name && c.read_only && !c.requires_confirm))) {
      $('#soltuiLiveStatus').textContent = 'This host does not expose the read-only live view tools.'; return;
    }
    liveBusy = true;
    try {
      if (asset !== liveAsset) {
        liveAsset = asset; livePoints = []; predictionRows = []; predictionsAt = 0; predictionAttempted = false;
        const unavailable = aggregatePredictions([]);
        paintAggregate($('#soltuiLiveScore'), unavailable);
        paintAggregate($('#soltuiPredictionsScore'), unavailable);
        $('#soltuiLiveStatus').textContent = `Loading ${asset} recorder and predictions…`;
        $('#soltuiLivePredictionStatus').textContent = `Loading ${asset} predictions · refresh every 10s`;
        $('#soltuiLiveChart').replaceChildren();
        $('#soltuiLivePredictions').replaceChildren();
      }
      // Resolve the prediction snapshot before observing a new tick. Later
      // prediction refreshes must never alter a tick's recorded score.
      if (force || !predictionAttempted) {
        predictionAttempted = true;
        $('#soltuiLivePredictionStatus').textContent = `Refreshing ${asset} predictions… · refresh every 10s`;
        try {
          const predictions = await ask('forwardtest.predictions', { asset });
          if (!predictions.ok) throw new Error(predictions.error?.message ?? 'Predictions failed.');
          if (disposed || asset !== $('#soltuiLiveAsset').value.trim().toUpperCase() || contextGeneration !== liveGeneration) return;
          predictionRows = predictions.result.rows ?? [];
          voting = predictions.result.voting ?? { min_accuracy: 60, min_resolved: 20 };
          if (document.activeElement !== $('#soltuiVoteMinScore')) $('#soltuiVoteMinScore').value = voting.min_accuracy;
          if (document.activeElement !== $('#soltuiVoteMinResolved')) $('#soltuiVoteMinResolved').value = voting.min_resolved;
          const target = $('#soltuiLivePredictions');
          const filtering = target.contains(document.activeElement) && document.activeElement.matches('input[type=search]');
          const cursor = filtering ? document.activeElement.selectionStart : null;
          target.replaceChildren();
          if (predictionRows.length) renderPredictionEvidence(target, predictionRows, asset);
          else target.append(el('p', { class: 'empty', text: 'No saved forward predictions for this coin yet.' }));
          if (filtering) { const input = target.querySelector('input[type=search]'); input?.focus({ preventScroll: true }); if (input && cursor !== null) input.setSelectionRange(cursor, cursor); }
          predictionsAt = Date.now();
          const updated = new Date(predictionsAt).toISOString().slice(11, 19);
          $('#soltuiLivePredictionStatus').textContent = `Updated ${updated} UTC · refresh every 10s · saved closed-candle predictions`;
        } catch (e) {
          if (disposed || contextGeneration !== liveGeneration || asset !== $('#soltuiLiveAsset').value.trim().toUpperCase()) return;
          predictionAttempted = true;
          predictionRows = [];
          $('#soltuiLivePredictions').replaceChildren();
          $('#soltuiLivePredictionStatus').textContent = `Prediction refresh failed: ${e.message} · retrying every 10s`;
        }
      }
      const env = await ask('prices.status');
      if (!env.ok) throw new Error(env.error?.message ?? 'Recorder status failed.');
      if (asset !== $('#soltuiLiveAsset').value.trim().toUpperCase() || contextGeneration !== liveGeneration) return;
      const aggregate = aggregatePredictions(predictionRows, Date.now() / 1000, voting);
      paintAggregate($('#soltuiLiveScore'), aggregate);
      paintAggregate($('#soltuiPredictionsScore'), aggregate);
      const q = env.result.prices?.[`${asset}-USD`];
      const age = q?.quote_age_s;
      desk.live({ asset, quote: q, aggregate, updated: predictionsAt, fresh: !!env.result.live && typeof age === 'number' && age >= 0 && age < 15 });
      const price = q?.mid ?? q?.last;
      if (typeof price === 'number' && Number.isFinite(price) && price > 0 && typeof age === 'number' && Number.isFinite(age) && age >= 0) {
        const at = typeof q.quote_ts === 'number' && Number.isFinite(q.quote_ts) ? q.quote_ts * 1000 : Math.round((Date.now() - age * 1000) / 1000) * 1000;
        const current = env.result.live && age < 15;
        if (at <= Date.now()) livePoints = appendScoreTick(livePoints, { at, price, aggregate: current && aggregate.available ? aggregate : { score: null, color: 'gray', label: 'Unavailable' } });
        const width = Math.max(320, Math.round($('#soltuiLiveChart').getBoundingClientRect().width) || 720);
        clear($('#soltuiLiveChart'), renderScoreChart(livePoints, { width }));
        $('#soltuiLiveStatus').textContent = `${asset}-USD $${price} · bid ${q.bid ?? '—'} · ask ${q.ask ?? '—'} · spread ${q.spread_bps ?? '—'} bps · ${age}s old · ${current ? 'LIVE' : 'STALE / recorder offline'} · chart scores are observed agreement, not win probability`;
      } else {
        $('#soltuiLiveStatus').textContent = 'No usable quote. The recorder may be stopped; start it explicitly in Bots & prices if needed.';
      }
    } catch (e) {
      if (disposed || contextGeneration !== liveGeneration || asset !== $('#soltuiLiveAsset').value.trim().toUpperCase()) return;
      const unavailable = aggregatePredictions([]);
      paintAggregate($('#soltuiLiveScore'), unavailable);
      paintAggregate($('#soltuiPredictionsScore'), unavailable);
      desk.live({ asset, quote: null, aggregate: unavailable, updated: null, fresh: false });
      $('#soltuiLiveStatus').textContent = `Live view unavailable: ${e.message} · automatic refresh will retry`;
    } finally {
      liveBusy = false;
      if (liveRefreshRequested && !votingSaving && !disposed) { liveRefreshRequested = false; refreshLive(true); }
    }
  }
  async function saveVoteFloor() {
    if (votingSaving) return;
    const rawScore = $('#soltuiVoteMinScore').value.trim();
    const rawSamples = $('#soltuiVoteMinResolved').value.trim();
    const min = Number(rawScore), count = Number(rawSamples);
    if (!rawScore || !rawSamples || !Number.isFinite(min) || min < 0 || min > 100 || !Number.isInteger(count) || count < 1) {
      $('#soltuiVoteStatus').textContent = 'Enter accuracy 0–100 and a positive whole resolved count.'; return;
    }
    liveGeneration += 1;
    votingSaving = true;
    $('#soltuiVoteMinScore').disabled = true;
    $('#soltuiVoteMinResolved').disabled = true;
    try {
      const env = await ask('settings.save', { live_vote_min_accuracy: min, live_vote_min_resolved: count });
      if (!env.ok) throw new Error(env.error?.message ?? 'Settings refused.');
      voting = { min_accuracy: min, min_resolved: count };
      predictionsAt = 0; predictionAttempted = false;
      $('#soltuiVoteStatus').textContent = 'Saved shared voting floor.';
      const aggregate = aggregatePredictions(predictionRows, Date.now() / 1000, voting);
      paintAggregate($('#soltuiLiveScore'), aggregate);
      paintAggregate($('#soltuiPredictionsScore'), aggregate);
      liveRefreshRequested = true;
    } catch (e) { $('#soltuiVoteStatus').textContent = `Voting floor not saved: ${e.message}`; }
    finally {
      votingSaving = false;
      $('#soltuiVoteMinScore').disabled = false;
      $('#soltuiVoteMinResolved').disabled = false;
      if (liveRefreshRequested && !disposed) { liveRefreshRequested = false; refreshLive(true); }
    }
  }
  async function renew() {
    try {
      const res = await transport({ type: 'soltuiSession', session, active: true });
      const state = res?.result;
      if (!res?.ok || !state?.available) { status.textContent = 'Dashboard session is unavailable. Reload the extension and native host.'; return; }
      if (generation !== null && (state.generation !== generation || (generation > 0 && !state.connected))) {
        poll.checked = false;
        $('#soltuiLiveStream').checked = false;
        status.textContent = 'The native session changed. Check saved status before resuming replay or jobs. No action was retried.';
      }
      generation = state.generation;
    } catch (e) { status.textContent = `Session unavailable: ${e.message}`; }
  }
  async function loadList() {
    await desk.restore;
    status.textContent = 'Connecting to SolTUI…';
    await renew();
    try {
      const res = await transport({ type: 'soltuiCommands' });
      const env = res?.result;
      if (!res?.ok || !env?.ok || !Array.isArray(env.result)) throw new Error(env?.error?.message ?? res?.error ?? 'SolTUI is not available.');
      commands = env.result;
      desk.commands(commands);
      deskPage = null;
      remember();
      const old = select.value;
      clear(select, ...commands.map((c) => el('option', { value: c.name, text: c.name })));
      if (commands.some((c) => c.name === old)) select.value = old;
      else select.value = filterCommands(commands, workspace.value)[0]?.name ?? commands[0]?.name ?? '';
      nowLoaded = false;
      status.textContent = `${commands.length} TUI tools connected · session retained while a dashboard is open`;
      renderForm();
      renderTools();
      applyRoute();
      await renew();
    } catch (e) { status.textContent = e.message; }
  }

  clear(workspace, ...WORKSPACES.map((w) => el('option', { value: w.id, text: w.title })));
  workspace.value = 'signal';
  select.addEventListener('change', () => { remember(); renderForm(); });
  search.addEventListener('input', renderTools);
  workspace.addEventListener('change', () => { location.hash = `soltui/${workspace.value}`; renderTools(); });
  $('#soltuiReload').addEventListener('click', loadList);
  form.addEventListener('input', (e) => { if (e.target !== confirmBox) clearConfirmation(); });
  form.addEventListener('change', (e) => { if (e.target !== confirmBox) clearConfirmation(); });
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const c = current();
    if (!c || pending.has(c.name) || (c.requires_confirm && !confirmBox?.checked)) return;
    remember();
    const values = Object.fromEntries([...inputs].map(([k, input]) => [k, input.value]));
    const built = buildParams(c, values, { confirmed: confirmBox?.checked === true, emptyFields: [...inputs].filter(([, input]) => input.clearBox?.checked).map(([k]) => k) });
    if (built.errors.length) { result.textContent = built.errors.join('\n'); $('#soltuiRunStatus').textContent = built.errors.join(' · '); return; }
    run(c, built.params);
  });
  $('#soltuiExportJson').addEventListener('click', () => {
    if (lastEnvelope) download(`${lastEnvelope.command}.json`, JSON.stringify(lastEnvelope, null, 2), 'application/json');
  });
  $('#soltuiSave').addEventListener('click', async () => {
    if (!editor || editor.readOnly) return;
    const save = $('#soltuiSave');
    save.disabled = true;
    try {
      const latest = await ask('docs.read', { path: documentPath });
      if (!latest.ok || !latest.result.editable || latest.result.text !== editorBase) throw new Error('The document changed or became read only. Export your draft, then reload it before saving.');
      const text = editor.value;
      const env = await ask('docs.write', { path: documentPath, text });
      if (!env.ok) throw new Error(env.error.message);
      editorBase = text;
      $('#soltuiEditorStatus').textContent = 'Saved to disk.';
    } catch (e) { $('#soltuiEditorStatus').textContent = `Save refused: ${e.message}`; }
    finally { save.disabled = editor.readOnly; }
  });
  $('#soltuiEditorExport').addEventListener('click', () => {
    if (editor) download('document-draft.txt', editor.value, 'text/plain;charset=utf-8');
  });
  $('#soltuiEditorReload').addEventListener('click', () => {
    if (editor && editor.value !== editorBase) { $('#soltuiEditorStatus').textContent = 'Export your draft before reloading. Clear your changes to the saved text to reload.'; return; }
    if (documentPath) openDocument(documentPath).catch((e) => { $('#soltuiEditorStatus').textContent = e.message; });
  });
  $('#soltuiLiveAsset').addEventListener('change', () => {
    liveGeneration += 1;
    desk.assetChanged();
    liveAsset = ''; livePoints = []; predictionRows = []; predictionsAt = 0; predictionAttempted = false;
    $('#soltuiLiveChart').replaceChildren();
    $('#soltuiLivePredictions').replaceChildren();
    const unavailable = aggregatePredictions([]);
    paintAggregate($('#soltuiLiveScore'), unavailable);
    paintAggregate($('#soltuiPredictionsScore'), unavailable);
    refreshLive(true);
  });
  $('#soltuiVoteMinScore').addEventListener('change', saveVoteFloor);
  $('#soltuiVoteMinResolved').addEventListener('change', saveVoteFloor);
  $('#soltuiLiveRefresh').addEventListener('click', () => refreshLive(true));
  $('#soltuiLiveStream').addEventListener('change', () => { if ($('#soltuiLiveStream').checked) refreshLive(true); });
  window.addEventListener('hashchange', applyRoute);
  heartbeat = setInterval(renew, 25_000);
  pollTimer = setInterval(() => {
    const c = current();
    if (disposed || document.hidden || $('#view-soltui').hidden || !poll.checked || !c || !POLLABLE.has(c.name) || c.read_only !== true) return;
    const values = Object.fromEntries([...inputs].map(([k, input]) => [k, input.value]));
    const built = buildParams(c, values);
    if (!built.errors.length) run(c, built.params, true);
  }, 10_000);
  function liveVisible() {
    return !disposed && !document.hidden && !$('#view-soltui').hidden && !$('#soltuiLive').hidden;
  }
  function pollLivePredictions() {
    // Use a separate fixed timer: read latency must not extend the ten-second
    // cadence, and a busy reader skips a tick rather than queuing a burst.
    if (liveVisible() && !liveBusy && !votingSaving) refreshLive(true);
  }
  predictionTimer = setInterval(pollLivePredictions, LIVE_PREDICTIONS_MS);
  liveTimer = setInterval(() => {
    if (disposed || document.hidden || $('#view-soltui').hidden || $('#soltuiLive').hidden) return;
    if ($('#soltuiLiveStream').checked || !predictionAttempted) refreshLive();
  }, 5000);
  function dispose() {
    disposed = true;
    desk.dispose();
    clearInterval(heartbeat);
    clearInterval(pollTimer);
    clearInterval(liveTimer);
    clearInterval(predictionTimer);
    transport({ type: 'soltuiSession', session, active: false }).catch(() => {});
  }
  window.addEventListener('pagehide', dispose, { once: true });
  window.addEventListener('beforeunload', (e) => {
    if (pending.size || (editor && editor.value !== editorBase)) { e.preventDefault(); e.returnValue = ''; }
  });
  return loadList();
}
