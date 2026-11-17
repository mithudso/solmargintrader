/** Present supplied committed advisory data only; this view performs no I/O. */
const HORIZONS = [60, 300, 600, 900, 1200, 3600];
const finite = n => typeof n === 'number' && Number.isFinite(n);
const pct = n => finite(n) ? `${(n * 100).toFixed(1)}%` : 'unavailable';
const time = ms => finite(ms) && Number.isFinite(new Date(ms).getTime()) ? `${new Date(ms).toISOString().slice(11, 19)} UTC` : 'unknown time';
const label = seconds => seconds === 3600 ? '1h' : `${seconds / 60}m`;
const count = n => Number.isSafeInteger(n) && n >= 0 ? n : 0;
const directions = { UP: '↑ UP', DOWN: '↓ DOWN', FLAT: '↔ NEUTRAL' };
const reasons = { below_threshold: 'fell below 80%', side_flip: 'reversed', stale: 'feed expired', publisher_changed: 'publisher changed' };

function validScores(s) {
  return s && ['up', 'down', 'flat'].every(k => finite(s[k]) && s[k] >= 0 && s[k] <= 1)
    && Math.abs(s.up + s.down + s.flat - 1) < 0.001;
}
function direction(row) {
  if (!validScores(row?.scores)) return null;
  const scores = row.scores, max = Math.max(scores.up, scores.down, scores.flat);
  const winners = ['up', 'down', 'flat'].filter(k => scores[k] === max);
  return winners.length !== 1 || winners[0] === 'flat' ? 'FLAT' : winners[0].toUpperCase();
}
function paint(card, row, historical) {
  const side = historical ? 'FLAT' : direction(row);
  const score = validScores(row?.scores) ? Math.max(row.scores.up, row.scores.down, row.scores.flat) : 0;
  const intensity = Math.max(0, Math.min(1, (score - 1 / 3) / (2 / 3)));
  const palette = side === 'UP' ? [195, 245, 215] : side === 'DOWN' ? [255, 215, 215] : [229, 231, 235];
  card.style.backgroundColor = `rgb(${palette.map(c => Math.round(255 - (255 - c) * (0.55 + 0.45 * intensity))).join(', ')})`;
  card.style.color = '#111827';
  card.dataset.direction = side || 'FLAT';
}
function resultText(row) {
  const side = direction(row);
  if (!side) return 'Waiting for 30 seconds of fresh observations · no estimate yet';
  const s = row.scores, max = Math.max(s.up, s.down, s.flat);
  const tie = [s.up, s.down, s.flat].filter(x => x === max).length > 1;
  return `${directions[side]}${tie ? ' · tied' : ''} · model estimate ${pct(max)} · UP ${pct(s.up)} / DOWN ${pct(s.down)} / FLAT ${pct(s.flat)} · learning n=${count(row.samples)}`;
}

export function liveOracleView(container, { clock = Date.now } = {}) {
  const node = (tag, text, id) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (id) el.id = id; return el; };
  const section = node('section'); section.setAttribute('aria-label', 'Live Oracle direction estimates');
  const heading = node('h2', 'Live Oracle · direction estimates');
  const announcement = node('p', '', 'live-oracle-announcement'); announcement.setAttribute('role', 'status'); announcement.setAttribute('aria-live', 'polite');
  const status = node('p', '', 'live-oracle-status');
  const primary = node('div', '', 'live-oracle-primary');
  const rows = node('div', undefined, 'live-oracle-horizons');
  const windowInfo = node('p', '', 'live-oracle-window');
  const details = node('details'), summary = node('summary', 'Evidence and recent windows');
  const evidence = node('div', undefined, 'live-oracle-evidence'); details.append(summary, evidence);
  section.append(heading, announcement, status, primary, rows, windowInfo, details); container.append(section);
  let previousAnnouncement = null, closed = false;
  return {
    render(view = {}) {
      if (closed) return;
      const now = clock(), local = view.local, shared = view.shared;
      const matches = !local || (local.source === shared?.source && local.model === shared?.model && local.target === shared?.target && (!view.asset || local.market === view.asset));
      const available = !['unavailable', 'source_changed', 'source-changed', 'stale', 'error'].includes(view.status);
      const sharedFresh = !!shared && matches && available && shared.fresh === true && finite(shared.as_of_ms) && finite(shared.expires_at_ms) && now >= shared.as_of_ms && now <= shared.expires_at_ms;
      const localFresh = !!local && available && local.market === view.asset && local.status !== 'stale' && finite(local.asOfMs) && finite(view.localExpiresAtMs) && now >= local.asOfMs && now <= view.localExpiresAtMs;
      const source = sharedFresh ? shared : local && local.market === view.asset ? local : null;
      const fresh = sharedFresh || localFresh;
      const selected = HORIZONS.includes(Number(view.selectedHorizon)) ? Number(view.selectedHorizon) : 600;
      const row = source?.horizons?.[selected];
      const name = sharedFresh ? 'Shared · fresh' : localFresh ? 'This browser · sharing offline' : source ? 'Historical · current feed unavailable' : 'Unavailable · waiting for this source';
      const statusText = `${name} · ${view.asset || 'asset unavailable'} · ${source?.status || (sharedFresh ? 'learning' : 'waiting')}`;
      status.textContent = statusText;
      const asOf = sharedFresh ? source.as_of_ms : source?.asOfMs;
      const age = finite(asOf) && now >= asOf ? `${Math.floor((now - asOf) / 1000)}s old` : 'age unavailable';
      primary.textContent = `${label(selected)} · ${fresh ? '' : 'Historical · '}${resultText(row)} · ${age}`;
      paint(primary, row, !fresh);
      rows.replaceChildren();
      for (const h of HORIZONS) {
        const item = node('div', `${label(h)} · ${fresh ? '' : 'Historical · '}${resultText(source?.horizons?.[h])}`);
        item.dataset.horizon = String(h); paint(item, source?.horizons?.[h], !fresh); rows.append(item);
      }
      const w = sharedFresh ? row?.window : null;
      const duration = w && finite(w.start_ms) && finite(w.last_ms) ? Math.max(0, w.last_ms - w.start_ms) : null;
      const transition = `${statusText}|${w?.id || ''}|${w?.direction || ''}`;
      if (transition !== previousAnnouncement) {
        announcement.textContent = `${statusText}${w ? ` · 80% window ${directions[w.direction] || 'direction unavailable'}` : ' · no current shared 80% window'}`;
        previousAnnouncement = transition;
      }
      windowInfo.textContent = w && ['UP', 'DOWN'].includes(w.direction) && duration !== null
        ? `80% window · ${directions[w.direction]} · opened ${time(w.start_ms)} · observed ${(duration / 1000).toFixed(1)}s · peak ${pct(w.peak)}${duration >= 15000 ? ' · sustained 15s' : ''}`
        : 'No current shared 80% window';
      evidence.replaceChildren();
      const quote = source?.quote;
      if (finite(quote?.price)) evidence.append(node('p', `Last observed quote ${quote.price}`));
      for (const h of HORIZONS) {
        const v = source?.horizons?.[h]; if (!v) continue;
        const n = count(v.resolved), metrics = ['candidate', 'uniform', 'frequency'].map(k => {
          const m = v[k], hits = finite(m?.hits) && n ? pct(m.hits / n) : 'unavailable', brier = finite(m?.brier) && n ? (m.brier / n).toFixed(3) : 'unavailable';
          return `${k}: accuracy ${hits}, Brier ${brier}`;
        }).join(' · ');
        evidence.append(node('p', `${label(h)} · issued ${count(v.issued)} · resolved ${n} · pending ${count(v.pending)} · expired ${count(v.expired)} · capacity drops ${count(v.capacityDrops)} · ${metrics}`));
        for (const event of Array.isArray(v.history) ? v.history.slice(-5).reverse() : []) {
          evidence.append(node('p', `${label(h)} · ${directions[event.direction] || 'direction unavailable'} · opened ${time(event.start_ms)} · ended ${time(event.end_ms)} · ${reasons[event.reason] || 'end reason unavailable'} · ${(Math.max(0, finite(event.duration_ms) ? event.duration_ms : 0) / 1000).toFixed(1)}s · peak ${pct(event.peak)}`));
        }
      }
    },
    close() { closed = true; section.remove(); },
  };
}
