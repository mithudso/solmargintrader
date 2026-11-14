import { el, clear } from './ui-kit.js';
import { renderStrategyChart, disposeChart } from './charts.js';
import { utc } from './live-panel.js';

let nextHint = 0;
export function explanationLines(value) {
  if (!value?.available) return [value?.message ?? 'Saved vote explanation unavailable.'];
  const lines = [];
  for (const call of value.calls ?? []) {
    if (!call.eligible) continue;
    lines.push(`${call.horizon_minutes}m ${call.direction} · prior ${call.accuracy}% / ${call.resolved} resolved`, call.rule,
      `Issued ${utc(call.issued_at)} · expires ${utc(call.expires_at)}`);
    const basis = call.recorded_signal_basis;
    if (basis?.features_available) lines.push((basis.features ?? []).map(f => `${f.name}${f.period ? '(' + f.period + ')' : ''}: ${f.value}`).join(' · '));
    else lines.push(basis?.reason ?? 'Numeric indicator state was not saved.');
  }
  if (!lines.length) lines.push('This saved strategy currently has no eligible horizon vote.');
  return lines.filter(Boolean);
}

/** Lazy, escaped, keyboard-accessible rationale from the native saved vote. */
export function voteHint({ row, asset, read, select = null }) {
  const button = el('button', { class: 'strategy-vote', text: row.label, 'aria-label': `${row.label}: explain vote${select ? ' or select chart' : ''}` }); button.type = 'button';
  let tooltip = null, disposed = false, generation = 0, cached = null, pending = null;
  const id = `vote-hint-${++nextHint}`;
  const eligibleUntil = Math.max(...[1, 5, 10, 30].map(h => typeof row[`expires_${h}m`] === 'number' ? row[`expires_${h}m`] : 0));
  async function load() {
    if (cached && Date.now() / 1000 < Math.min(eligibleUntil, cached.at + 10)) return cached.value;
    pending ??= Promise.resolve().then(() => read('forwardtest.explain', { asset, label: row.label }))
      .then(value => { cached = { value, at: Date.now() / 1000 }; return value; }).finally(() => { pending = null; });
    return pending;
  }
  function hide() { generation++; tooltip?.remove(); tooltip = null; button.removeAttribute('aria-describedby'); }
  async function show() {
    if (disposed) return;
    hide(); const token = generation;
    tooltip = el('div', { class: 'vote-tooltip', role: 'tooltip', id, text: 'Reading saved vote…' });
    button.ownerDocument.body.append(tooltip); button.setAttribute('aria-describedby', id);
    const rect = button.getBoundingClientRect(), win = button.ownerDocument.defaultView;
    tooltip.style.left = `${Math.max(8, Math.min(rect.left, win.innerWidth - 390))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(rect.bottom + 6, win.innerHeight - 280))}px`;
    try { const value = await load(); if (!disposed && generation === token && tooltip) clear(tooltip, el('strong', { text: `${asset} · ${row.label}` }), ...explanationLines(value).map(text => el('p', { text }))); }
    catch (error) { if (generation === token && tooltip) tooltip.textContent = error.message; }
  }
  const click = () => select ? select(row, load) : show();
  const key = event => { if (event.key === 'Escape') hide(); };
  button.addEventListener('pointerenter', show); button.addEventListener('pointerleave', hide);
  button.addEventListener('focus', show); button.addEventListener('blur', hide);
  button.addEventListener('click', click); button.addEventListener('keydown', key);
  return { button, load, dispose() { disposed = true; hide(); button.removeEventListener('pointerenter', show); button.removeEventListener('pointerleave', hide); button.removeEventListener('focus', show); button.removeEventListener('blur', hide); button.removeEventListener('click', click); button.removeEventListener('keydown', key); } };
}

export function mountVoteCharts({ host, controls, reference, follow, read, asset }) {
  let epoch = 0, disposed = false, drawing = 0;
  const selected = new Map(), hints = new Set();
  const message = el('p', { class: 'note', role: 'status' });
  const chips = el('div', { class: 'row' });
  const reset = el('button', { text: 'Clear strategy graphics', onclick: () => clearSelection() }); reset.type = 'button';
  const switcher = el('button', { text: 'TradingView reference', onclick: () => { reference.hidden = !reference.hidden; switcher.setAttribute('aria-pressed', String(!reference.hidden)); } }); switcher.type = 'button';
  controls.replaceChildren(chips, message, el('div', { class: 'row' }, reset, switcher));
  function sync() {
    controls.hidden = selected.size === 0; host.hidden = selected.size === 0;
    reference.hidden = selected.size > 0;
    switcher.setAttribute('aria-pressed', String(!reference.hidden));
    clear(chips, ...[...selected.keys()].map(label => {
      const b = el('button', { class: 'chip plain', text: `${label} ×`, 'aria-label': `Remove ${label} chart`, onclick: () => remove(label) }); b.type = 'button'; return b;
    }));
    for (const hint of hints) hint.button.setAttribute('aria-pressed', String(selected.has(hint.button.dataset.label)));
  }
  function draw() {
    const token = ++drawing;
    const values = [...selected.values()].filter(s => s.value).map(s => s.value);
    if (!values.length) return;
    renderStrategyChart(host, values, { follow: follow(), asset: asset() }).then(result => {
      if (!disposed && token === drawing && selected.size && result === 'unavailable') message.textContent = 'The original candles are unavailable; no indicator graphics were invented.';
    }).catch(error => { if (!disposed && token === drawing) message.textContent = error.message; });
  }
  function remove(label) { selected.delete(label); disposeChart(host); sync(); if (selected.size) draw(); }
  function clearSelection() { epoch++; selected.clear(); disposeChart(host); host.replaceChildren(); sync(); }
  async function select(row, load) {
    const label = row.label;
    if (selected.has(label)) { remove(label); return; }
    if (selected.size >= 2) { message.textContent = 'Two strategies are selected. Remove one to add another.'; return; }
    const slot = { request: 0 }; selected.set(label, slot); const generation = epoch, coin = asset(), request = ++slot.request; sync();
    message.textContent = 'Loading saved forecast graphics…';
    try {
      const value = await load();
      if (disposed || epoch !== generation || coin !== asset() || selected.get(label) !== slot || request !== slot.request) return;
      slot.value = value;
      message.textContent = 'Saved closed-candle forecast · at most two strategies · no TradingView account quota.';
      draw();
    } catch (error) { if (!disposed && epoch === generation && coin === asset() && selected.get(label) === slot && request === slot.request) { selected.delete(label); sync(); message.textContent = error.message; } }
  }
  return {
    button(row, coin) {
      const hint = voteHint({ row, asset: coin, read, select }); hints.add(hint);
      hint.button.dataset.label = row.label; hint.button.setAttribute('aria-pressed', String(selected.has(row.label)));
      return hint.button;
    },
    rendered() { for (const hint of hints) if (!hint.button.isConnected) { hint.dispose(); hints.delete(hint); } },
    changed: clearSelection,
    refresh() { for (const [label, slot] of selected) {
      const generation = epoch, coin = asset(), request = ++slot.request;
      const current = () => !disposed && epoch === generation && coin === asset() && selected.get(label) === slot && request === slot.request;
      read('forwardtest.explain', { asset: coin, label }).then(value => {
        if (current()) { slot.value = value; message.textContent = 'Saved forecast refreshed.'; draw(); }
      }).catch(() => { if (current()) { ++drawing; message.textContent = 'Refresh failed; retained strategy graphics are stale.'; } });
    } },
    dispose() { disposed = true; clearSelection(); for (const hint of hints) hint.dispose(); hints.clear(); },
  };
}
