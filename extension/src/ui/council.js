import { el, clear, table } from './ui-kit.js';

/** Persistent form: status polling never replaces a user's settings draft. */
export function mountCouncil({ ask, supports }) {
  const node = el('section', { class: 'card', id: 'councilBot' });
  const status = el('p', { role: 'status', text: 'Read Council status to begin.' });
  const summary = el('p', { class: 'note' });
  const fills = el('div', { class: 'table-wrap' });
  const form = el('form', { class: 'filters' });
  const fields = {};
  for (const [name, label, value, type] of [
    ['asset', 'Coin', 'SOL', 'text'], ['capital', 'Paper capital ($)', 10000, 'number'],
    ['min_accuracy', 'Strategy accuracy floor (%)', 60, 'number'], ['min_resolved', 'Minimum resolved per horizon', 20, 'number'],
    ['allow_short', 'Allow paper shorts', false, 'checkbox'], ['use_leverage', 'Use leverage', false, 'checkbox'],
    ['leverage', 'Leverage (×)', 2, 'number'], ['min_confidence', 'Entry confidence floor (0–1)', .8, 'number'],
  ]) {
    const input = el('input', { type, name, 'aria-label': label });
    if (type === 'checkbox') input.checked = value;
    else { input.value = value; if (type === 'number') { input.step = name === 'min_resolved' ? '1' : 'any'; input.min = '0'; } }
    fields[name] = input;
    form.append(el('label', { text: label }, input));
  }
  const save = el('button', { text: 'Save settings' });
  save.type = 'submit';
  const start = el('button', { class: 'primary', text: 'Start paper Council' });
  const stop = el('button', { text: 'Stop Council' });
  const refreshButton = el('button', { text: 'Refresh' });
  for (const button of [start, stop, refreshButton]) button.type = 'button';
  form.append(save);
  node.append(el('h2', { text: 'Council bot · paper' }),
    el('p', { class: 'note', text: 'Strong Buy opens long; Sell closes it. Optional shorts mirror this. Neutral votes hold the position.' }),
    status, summary, form, el('div', { class: 'row' }, start, stop, refreshButton),
    el('p', { class: 'note', text: 'Jupiter fee model; real Coinbase candles supply paper fills. Confidence warms up from 20 prospective outcomes. Stop pauses monitoring and retains an open paper position.' }), fills);
  let disposed = false, busy = false, initialized = false;
  async function request(name, params = {}) {
    const env = await ask(name, params);
    if (!env?.ok) throw new Error(env?.error?.message ?? 'Council request failed');
    return env.result;
  }
  function paint(s) {
    status.textContent = `${s.running ? 'Running' : 'Stopped'} · ${s.message ?? s.state}`;
    const p = s.position;
    const confidence = typeof s.confidence === 'number' ? `${(100 * s.confidence).toFixed(1)}%` : 'Warming up';
    summary.textContent = `${s.config?.asset ?? '—'} · ${p ? (p.direction > 0 ? 'Long' : 'Short') + ' @ $' + p.entry_price : 'Flat'} · Paper equity $${Number(s.equity ?? 0).toFixed(2)} · Confidence ${confidence} (${s.confidence_samples ?? 0} samples)${s.pending ? ' · Fill pending' : ''}`;
    const locked = !!s.running || !!s.position || !!s.pending;
    for (const input of Object.values(fields)) input.disabled = locked;
    save.disabled = locked; start.disabled = !!s.running; stop.disabled = !s.running;
    if (!initialized && s.config) {
      for (const [key, input] of Object.entries(fields)) {
        const value = s.config[key] ?? s.config.execution?.[key];
        if (input.type === 'checkbox') input.checked = !!value;
        else if (value != null) input.value = value;
      }
      initialized = true;
    }
    clear(fills);
    if (s.fills?.length) fills.append(table([
      { label: 'UTC', value: r => new Date(r.at * 1000).toISOString() },
      { label: 'Action', value: r => r.side }, { label: 'Fill price', value: r => r.price },
      { label: 'Reason', value: r => r.reason }, { label: 'Paper equity', value: r => r.equity },
    ], s.fills));
  }
  async function run(name, params) {
    if (busy || disposed) return;
    if (!supports('council.status')) { status.textContent = 'Council needs the updated native host.'; return; }
    busy = true;
    try {
      const result = await request(name, params);
      const state = name === 'council.config' ? await request('council.status') : result;
      if (!disposed) paint(state);
    } catch (error) { if (!disposed) status.textContent = error.message; }
    finally { busy = false; }
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    const config = { execution: {} };
    for (const [key, input] of Object.entries(fields)) {
      const value = input.type === 'checkbox' ? input.checked : input.type === 'number' ? Number(input.value) : input.value.trim().toUpperCase();
      (['allow_short', 'use_leverage', 'leverage', 'min_confidence'].includes(key) ? config.execution : config)[key] = value;
    }
    run('council.config', { config });
  });
  start.onclick = () => run('council.start');
  stop.onclick = () => run('council.stop');
  refreshButton.onclick = () => run('council.status');
  return { node, refresh: () => run('council.status'), dispose: () => { disposed = true; } };
}
