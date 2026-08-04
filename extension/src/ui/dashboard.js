/**
 * Dashboard: configuration, risk rails, journal, and P&L.
 *
 * Charts are hand-built SVG rather than a charting library, because the
 * extension CSP forbids remote script and bundling one for two charts is not
 * worth the weight. Both carry text alternatives so the numbers are reachable
 * without reading the picture.
 */

import { snapshot, equityCurve, maxDrawdown, fillsToCsv } from '../core/pnl.js';
import { gridLevels, capitalRequirement } from '../core/grid.js';

const $ = (sel) => document.querySelector(sel);
const send = (msg) => chrome.runtime.sendMessage(msg);
const usd = (n) => (n == null ? '—' : `${n < 0 ? '−' : ''}$${Math.abs(n).toFixed(2)}`);

let cache = { config: null, limits: null, fills: [], intents: [], carry: [], events: [], price: null };

/* ------------------------------------------------------------------- charts -- */

function svg(children, { width, height, label }) {
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="${escapeAttr(label)}">${children}</svg>`;
}

function equitySvg(points) {
  const W = 720;
  const H = 200;
  const PAD = 28;
  if (points.length < 2) return '<p class="note">No closed round trips yet.</p>';

  const xs = points.map((p) => p.tsMs);
  const ys = points.map((p) => p.equityUsd);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const spanX = x1 - x0 || 1;
  const spanY = y1 - y0 || 1;

  const sx = (x) => PAD + ((x - x0) / spanX) * (W - PAD * 2);
  const sy = (y) => H - PAD - ((y - y0) / spanY) * (H - PAD * 2);

  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.tsMs).toFixed(1)},${sy(p.equityUsd).toFixed(1)}`).join(' ');
  const last = points.at(-1).equityUsd;
  const stroke = last >= points[0].equityUsd ? '#15803d' : '#b91c1c';

  // Zero line only when the curve actually crosses it.
  const zero = y0 < 0 && y1 > 0 ? `<line x1="${PAD}" y1="${sy(0)}" x2="${W - PAD}" y2="${sy(0)}" stroke="#9ca3af" stroke-dasharray="3 3"/>` : '';

  return svg(
    `${zero}<path d="${path}" fill="none" stroke="${stroke}" stroke-width="2"/>
     <text x="${PAD}" y="16" class="axis">${usd(y1)}</text>
     <text x="${PAD}" y="${H - 8}" class="axis">${usd(y0)}</text>`,
    { width: W, height: H, label: `Equity curve, ${points.length} points, ending at ${usd(last)}` },
  );
}

function ladderSvg({ levels, intents, fills, price }) {
  const W = 720;
  const rowH = 22;
  const H = levels.length * rowH + 20;
  const maxLevel = Math.max(...levels, price ?? 0);
  const minLevel = Math.min(...levels, price ?? Infinity);
  const span = maxLevel - minLevel || 1;
  const sx = (v) => 60 + ((v - minLevel) / span) * (W - 140);

  const restingByLevel = new Map();
  for (const i of intents) {
    if (i.status === 'resting') restingByLevel.set(round4(i.level), i.side);
  }
  const fillsByLevel = new Map();
  for (const f of fills) {
    if (f.level == null) continue;
    const k = round4(f.level);
    fillsByLevel.set(k, (fillsByLevel.get(k) ?? 0) + 1);
  }

  const rows = levels
    .slice()
    .reverse()
    .map((level, idx) => {
      const y = 12 + idx * rowH;
      const k = round4(level);
      const side = restingByLevel.get(k);
      const nFills = fillsByLevel.get(k) ?? 0;
      const colour = side === 'buy' ? '#2563eb' : side === 'sell' ? '#b45309' : '#d1d5db';
      const dot = side
        ? `<circle cx="${sx(level).toFixed(1)}" cy="${y}" r="5" fill="${colour}"/>`
        : `<circle cx="${sx(level).toFixed(1)}" cy="${y}" r="3" fill="${colour}"/>`;
      const fillMark = nFills
        ? `<text x="${(sx(level) + 10).toFixed(1)}" y="${y + 4}" class="axis">${nFills}×</text>`
        : '';
      return `<text x="4" y="${y + 4}" class="axis">$${level.toFixed(2)}</text>
              <line x1="60" y1="${y}" x2="${W - 80}" y2="${y}" stroke="#f3f4f6"/>${dot}${fillMark}`;
    })
    .join('');

  const marker =
    price != null
      ? `<line x1="${sx(price).toFixed(1)}" y1="6" x2="${sx(price).toFixed(1)}" y2="${H - 6}" stroke="#111827" stroke-dasharray="4 2"/>
         <text x="${(sx(price) + 4).toFixed(1)}" y="${H - 6}" class="axis">mark $${price.toFixed(2)}</text>`
      : '';

  return svg(`${rows}${marker}`, {
    width: W,
    height: H,
    label: `Grid ladder with ${restingByLevel.size} resting orders across ${levels.length} rungs`,
  });
}

const round4 = (n) => Number(Number(n).toFixed(4));
const escapeAttr = (s) => String(s).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');

/* -------------------------------------------------------------------- render -- */

function fillForm(form, values) {
  for (const el of form.elements) {
    if (!el.name || values[el.name] == null) continue;
    el.value = values[el.name];
  }
}

function readForm(form) {
  const out = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === 'number') {
      // A blank numeric field must be omitted, not sent as 0. `Number('')` is 0,
      // which would silently set notionalPerRungUsd or a risk cap to zero.
      const raw = el.value.trim();
      if (raw === '') continue;
      const n = Number(raw);
      if (!Number.isFinite(n)) continue;
      out[el.name] = n;
    } else {
      out[el.name] = el.value;
    }
  }
  return out;
}

function renderBanner() {
  const el = $('#banner');
  const { config } = cache;
  if (!config) return;
  if (config.mode === 'dry-run') {
    el.textContent = 'Dry run — real prices, simulated fills, nothing placed on chain.';
    el.className = 'banner ok';
  } else {
    el.textContent = `LIVE (${config.mode}) — orders are real and spend real funds.`;
    el.className = 'banner warn';
  }
}

function renderPnl() {
  const { fills, carry, price } = cache;
  if (!fills.length) {
    $('#equityChart').innerHTML = '<p class="note">No fills yet.</p>';
    return;
  }
  // Without a mark price, open inventory would be valued at zero and the page
  // would show a catastrophic fake unrealized loss. Say so instead.
  if (!(price > 0)) {
    $('#equityChart').innerHTML =
      '<p class="note">Waiting for the first price tick — P&amp;L needs a mark to value open inventory.</p>';
    return;
  }
  const pnl = snapshot({ fills, markPriceUsd: price, carryEntries: carry });
  const curve = equityCurve({ roundTrips: pnl.roundTrips, carryEntries: carry });
  const dd = maxDrawdown(curve);

  $('#net').textContent = usd(pnl.totalNetUsd);
  $('#realized').textContent = usd(pnl.realizedNetUsd);
  $('#unrealized').textContent = usd(pnl.unrealizedNetUsd);
  $('#fees').textContent = usd(pnl.feeTotalUsd);
  $('#trips').textContent = String(pnl.roundTripCount);
  $('#winRate').textContent = `${(pnl.winRate * 100).toFixed(0)}%`;
  $('#drawdown').textContent = `${usd(dd.drawdownUsd)} (${dd.drawdownPct.toFixed(1)}%)`;
  $('#inventory').textContent = `${pnl.openBaseQty.toFixed(4)} @ ${usd(pnl.avgEntryUsd)} avg`;

  $('#equityChart').innerHTML = equitySvg(curve);

  if (cache.config) {
    const levels = gridLevels(cache.config);
    $('#ladderChart').innerHTML = ladderSvg({
      levels,
      intents: cache.intents,
      fills,
      price: cache.price,
    });
  }
}

/**
 * Build a row with DOM APIs, never innerHTML.
 *
 * Order IDs and error strings come from the venue, and this page holds
 * extension privileges (chrome.storage, runtime messaging) — so a single missed
 * escape would be XSS with real reach. textContent removes the question.
 */
function appendRow(tbody, cells, className) {
  const tr = document.createElement('tr');
  if (className) tr.className = className;
  for (const cell of cells) {
    const td = document.createElement('td');
    td.textContent = cell == null || cell === '' ? '—' : String(cell);
    tr.append(td);
  }
  tbody.append(tr);
}

function emptyRow(tbody, span, text) {
  const tr = document.createElement('tr');
  const td = document.createElement('td');
  td.colSpan = span;
  td.textContent = text;
  tr.append(td);
  tbody.append(tr);
}

function renderTables() {
  const intentBody = $('#intents tbody');
  intentBody.replaceChildren();
  const intents = cache.intents.slice().sort((a, b) => (b.level ?? 0) - (a.level ?? 0));
  if (!intents.length) {
    emptyRow(intentBody, 6, 'No orders yet.');
  } else {
    for (const i of intents) {
      appendRow(
        intentBody,
        [
          i.intentKey,
          i.side,
          i.level != null ? `$${Number(i.level).toFixed(4)}` : null,
          i.status,
          i.venueOrderId,
          i.error ?? (i.adoptedFromVenue ? 'adopted from venue' : ''),
        ],
        `status-${String(i.status ?? '').replace(/[^a-z-]/gi, '')}`,
      );
    }
  }

  const fillBody = $('#fills tbody');
  fillBody.replaceChildren();
  const fills = cache.fills.slice().sort((a, b) => b.tsMs - a.tsMs);
  if (!fills.length) {
    emptyRow(fillBody, 5, 'No fills yet.');
  } else {
    for (const f of fills) {
      appendRow(fillBody, [
        new Date(f.tsMs).toLocaleString(),
        f.side,
        f.baseQty.toFixed(6),
        `$${f.priceUsd.toFixed(4)}`,
        usd(f.feeUsd),
      ]);
    }
  }

  $('#events').textContent = cache.events
    .map((e) => `${new Date(e.tsMs).toISOString()}  ${e.type}  ${JSON.stringify(e.summary ?? e.reason ?? '')}`)
    .join('\n');
}

function renderCapital() {
  const { config, price } = cache;
  if (!config || !price) return;
  const req = capitalRequirement({ config, price });
  $('#capital').textContent =
    `At $${price.toFixed(2)} this grid needs about $${req.quoteUsd.toFixed(2)} of ${config.quoteSymbol} ` +
    `plus ${req.baseQty.toFixed(4)} ${config.baseSymbol} ($${req.baseValueUsd.toFixed(2)}) — ` +
    `$${req.totalUsd.toFixed(2)} total. Trigger V2 rejects any order under $10.`;
}

/* --------------------------------------------------------------------- wiring -- */

async function refresh() {
  const status = await send({ type: 'status' });
  if (!status?.ok) return;
  const data = await send({ type: 'data' });

  cache = {
    config: status.config,
    limits: status.limits,
    price: status.lastTick?.price ?? null,
    fills: data?.fills ?? [],
    intents: data?.intents ?? [],
    carry: data?.carry ?? [],
    events: data?.events ?? [],
  };

  fillForm($('#configForm'), cache.config);
  fillForm($('#limitsForm'), cache.limits);
  renderBanner();
  renderPnl();
  renderTables();
  renderCapital();
}

$('#configForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  await send({ type: 'setConfig', patch: readForm($('#configForm')) });
  await refresh();
});

$('#limitsForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  await send({ type: 'setLimits', patch: readForm($('#limitsForm')) });
  await refresh();
});

$('#keyForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = $('#keyForm input[name="apiKey"]');
  await send({ type: 'setApiKey', apiKey: input.value });
  input.value = ''; // do not leave the key sitting in the DOM
  await refresh();
});

$('#exportCsv').addEventListener('click', () => {
  const csv = fillsToCsv(cache.fills);
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `solmargintrader-fills-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});

refresh().catch((err) => {
  $('#banner').textContent = `Dashboard failed to load: ${err.message}`;
  $('#banner').className = 'banner danger';
});
