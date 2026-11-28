/**
 * The 1s scalp window: a compact read-out of the next 30 seconds from one-second
 * oracle bars, and a take-profit / stop-loss guard for one listed position.
 * The call weighs each reading by its running hit rate, and the Experiments tab
 * keeps testing other settings of every reading (scalp-experiments.js).
 *
 * Market data is the public Jupiter oracle stream (the same validated feed the
 * indicator panel uses). The only things this window can do to the Jupiter page
 * go through the background worker: read its positions table and order form,
 * press one position's own Close button, and press the order form's own size
 * and Long or Short buttons. See exit-guard.js, entry-plan.js and page-bridge.js.
 */
import { JupiterFeed, JUPITER_ENDPOINTS } from './feed.js';
import { SecondBars, realizedVolBps } from './scalp-indicators.js';
import { SCALP_MODEL, HORIZON_S, readSlopes, SlopeHistory, SlopeScore, SCORE_HORIZONS, cone, ScoreBook, payoutPercent, bustFraction } from './scalp-model.js';
import { SCALP_EXPERIMENTS, VARIANTS, HORIZONS, DEFAULT_ASSIGNMENTS, PROMOTION, ExperimentBook, variantById, validAssignments, readSlots, weightedCall,
  findPromotions, leaderboard } from './scalp-experiments.js';
import { ExitGuard, parseLevel, parseDistance, resolveLevels, priceLike, positionKey, quoteFresh } from './exit-guard.js';
import { EntryTracker, validateEntry } from './entry-plan.js';
import { POWERED_BY } from '../jupiter/attribution.js';
import { MARKETS as PERPS_MARKETS } from '../perps/model.js';
import { createChart, CandlestickSeries, LineSeries, LineStyle } from '../../vendor/lightweight-charts/lightweight-charts.standalone.production.mjs';

const $ = id => document.getElementById(id);
const PARAMS = new URLSearchParams(location.hash.slice(1));
const SYMBOL = PARAMS.get('market') || '';
// Opened from the Jupiter Perps page: read-outs only. That page's order form and positions are never read or pressed.
const VIEW_ONLY = PARAMS.get('venue') === 'perps';
const STORAGE = 'jupiter1000xScalp';
const LOG_STORAGE = 'jupiter1000xScalpLog';
const EXPERIMENT_STORAGE = 'jupiter1000xScalpExperiments';
const SYMBOL_OK = /^[A-Z][A-Z0-9]{0,11}$/.test(SYMBOL);
const COLORS = { up: '#61dbac', down: '#f69b9b', flat: '#8796b0', band: '#8fa3c7', warm: '#27344a' };
const FEED_TEXT = {
  unsupported_market_or_timeframe: 'This market is not supported', market_unavailable: 'Market is unavailable', market_closed: 'Market is closed',
  public_read_failed: 'Public market request failed; retrying', subscription_refused: 'Live subscription was refused',
  reconnect_exhausted: 'Price stream lost; starting it again', stream_disconnected: 'Live stream disconnected; reconnecting',
  stale_quote: 'Price is stale; waiting for a fresh update',
};
const REASONS = {
  ambiguous_position: 'two listed positions look identical', position_not_listed: 'the position is not in the Jupiter list',
  positions_table_not_found: 'the positions table is not visible on the Jupiter tab (English layout, wide window)',
  close_unavailable: 'the row has no usable Close button', close_window_elapsed: 'the Close button stayed unavailable for 30 seconds',
  close_locked: 'the page still shows the minimum-hold countdown', close_disabled: 'the page has Close disabled',
  opened_positions_tab: 'switching the Jupiter page to its Positions tab', jupiter_tab_unavailable: 'the Jupiter 1000x tab is gone',
  page_timeout: 'the Jupiter tab did not answer', page_unreachable: 'the Jupiter tab could not be reached (reload it)',
  page_no_reply: 'the Jupiter tab did not answer', not_on_1000x: 'the Jupiter tab left the 1000x page',
  position_market_mismatch: 'the position is not in this window’s market', extension_error: 'the extension refused the request',
  extension_unreachable: 'the extension background did not answer', page_read_failed: 'the Jupiter page could not be read',
  no_reply: 'no reply from the Jupiter tab', still_listed: 'the position is still listed',
  market_mismatch: 'the Jupiter tab is showing another market', mode_not_classic: 'the Jupiter page is not in Classic mode',
  page_busy: 'the Jupiter page is busy with another request', size_button_unavailable: 'the page’s size button is unavailable (no balance read yet?)',
  amount_not_set: 'the page did not fill in an amount', amount_not_accepted: 'the page did not accept the three-quarter amount',
  amount_rejected: 'the page rejected the amount', side_disabled: 'the page has that button disabled',
  recently_opened: 'an entry was pressed moments ago', order_form_not_found: 'the order form is not visible on the Jupiter tab',
  position_not_seen: 'no new position was listed', invalid_request: 'the request was not valid', pending: 'an entry request is already out',
  amount_unexpected: 'the amount the page showed was not the chosen share of the balance', balance_unreadable: 'the available balance could not be read',
  too_slow: 'the Jupiter page took too long to accept the size (is its tab hidden?)',
  leverage_button_unavailable: 'the page has no such leverage preset', leverage_not_set: 'the page did not switch leverage',
  guard_live: 'a take profit or stop loss is live', page_changed: 'the Jupiter page changed market or mode',
  page_unreadable: 'the Jupiter page can no longer be read',
};
const TRANSIENT = new Set(['page_timeout', 'page_unreachable', 'page_no_reply', 'extension_unreachable']);
const FEED_RESTART = new Set(['reconnect_exhausted', 'subscription_refused']);
const LIVE_STATES = ['armed', 'triggered', 'clicked'];
const numeric = value => typeof value === 'number' && Number.isFinite(value);
const signed = (value, digits) => `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value).toFixed(digits)}`;
const small = value => { const v = Number(Math.abs(value).toPrecision(2)); return `${value > 0 ? '+' : value < 0 ? '−' : ''}${v}`; };
const arrow = vote => vote > 0 ? '▲' : vote < 0 ? '▼' : '◆';
const voteName = vote => vote === null || vote === undefined ? 'warming' : vote > 0 ? 'up' : vote < 0 ? 'down' : 'flat';
const clock = ms => new Date(ms).toLocaleTimeString(undefined, { hour12: false });
const windowLabel = seconds => seconds >= 60 && seconds % 60 === 0 ? `${seconds / 60}m` : `${seconds}s`;

const seconds = new SecondBars(), book = new ScoreBook(), slopeHistory = new SlopeHistory(), slopeScore = new SlopeScore();
const experiments = new ExperimentBook();
// Which setting each tile of the grid uses. The Experiments tab may switch a clear winner in.
let assignments = { ...DEFAULT_ASSIGNMENTS }, slotLocks = {}, tuneLog = [], autoApply = true, activeTab = 'live';
let experimentsSavedMs = Date.now(), experimentsDrawnMs = 0, rankHorizon = HORIZON_S, boardOrder = '', forgetArmedMs = 0;
/** The oracle clock of the last closed bar, which is what the switch rule's locks are kept in. */
const barClock = () => seconds.bars.at(-1)?.time ?? Math.floor(Date.now() / 1000);
const warmupBars = () => Math.max(...Object.values(assignments).map(id => variantById(id).need));
const emptyTiles = () => readSlots(assignments, new Map(), 0);
const guard = new ExitGuard(), entry = new EntryTracker(), events = [];
let feed, latest = null, lastQuoteMs = 0, view = null, disposed = false, drawQueued = false, barsVersion = 0, drawnVersion = -1;
let attached = false, linked = false, pageState = { ok: false, reason: 'not_started' }, positions = [], polling = false, lastPollMs = 0, closing = false;
// Only these are remembered between windows. Unlock, Confirm and the size are never stored:
// every window starts locked, confirming and at a quarter, whatever the last one was left at.
const DEFAULT_SETTINGS = Object.freeze({ mode: 'alert', unit: 'bp', takeProfit: '', stopLoss: '' });
let settings = { ...DEFAULT_SETTINGS }, audio = null, priceLines = [], lastStatus = '', opening = false, logCount = -1;
let lastFeedStartMs = 0, unprotectedAlertMs = 0, reportedLive = null, releaseLock = null, readoutError = '';

/* ------------------------------------------------------------------ chart -- */

const chart = createChart($('chart'), {
  autoSize: true, handleScroll: false, handleScale: false,
  layout: { background: { color: '#101723' }, textColor: '#b2bfd4', attributionLogo: true },
  grid: { vertLines: { color: '#202c40' }, horzLines: { color: '#202c40' } },
  timeScale: { timeVisible: true, secondsVisible: true, borderColor: '#46536c' },
  rightPriceScale: { borderColor: '#46536c' },
  crosshair: { horzLine: { labelVisible: true }, vertLine: { labelVisible: true } },
});
const candles = chart.addSeries(CandlestickSeries, { upColor: COLORS.up, downColor: COLORS.down, borderVisible: false,
  wickUpColor: COLORS.up, wickDownColor: COLORS.down, priceLineVisible: true });
const quiet = { priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false };
const bands = {
  outerHigh: chart.addSeries(LineSeries, { ...quiet, color: '#8fa3c766', lineWidth: 1, lineStyle: LineStyle.Dotted }),
  outerLow: chart.addSeries(LineSeries, { ...quiet, color: '#8fa3c766', lineWidth: 1, lineStyle: LineStyle.Dotted }),
  innerHigh: chart.addSeries(LineSeries, { ...quiet, color: COLORS.band, lineWidth: 1 }),
  innerLow: chart.addSeries(LineSeries, { ...quiet, color: COLORS.band, lineWidth: 1 }),
  // The most likely price line: labelled on the price axis with where it ends in 30 seconds.
  mid: chart.addSeries(LineSeries, { ...quiet, color: COLORS.flat, lineWidth: 3, lastValueVisible: true, title: 'likely' }),
};

function drawChart() {
  const bars = seconds.bars.slice(-180), developing = seconds.developing;
  const rows = bars.map(({ time, open, high, low, close }) => ({ time, open, high, low, close }));
  if (developing && (!rows.length || developing.time > rows.at(-1).time)) rows.push(developing);
  candles.setData(rows);
  const last = bars.at(-1);
  const steps = last && view?.call.ready && numeric(view.sigma)
    // The centre line follows the average path after weighted calls of this tier; with none measured it stays flat.
    ? cone({ price: last.close, sigmaBps: view.sigma, direction: view.call.direction, tier: view.call.tier, path: view.call.measured?.path_bps ?? [] }) : [];
  for (const [key, series] of Object.entries(bands)) {
    series.setData(steps.length ? [{ time: last.time, value: last.close }, ...steps.map(step => ({ time: last.time + step.seconds, value: step[key] }))] : []);
  }
  bands.mid.applyOptions({ color: COLORS[view?.call.direction ?? 'flat'] ?? COLORS.flat });
  if (rows.length) {
    const end = (last?.time ?? rows.at(-1).time) + HORIZON_S + 2;
    try { chart.timeScale().setVisibleRange({ from: end - 180, to: end }); } catch { /* fewer bars than the range yet */ }
  }
}

function drawPriceLines() {
  for (const line of priceLines) candles.removePriceLine(line);
  priceLines = [];
  const position = selectedPosition();
  const snap = guard.snapshot();
  const active = LIVE_STATES.includes(snap.state);
  const levels = active ? snap.levels : fieldLevels(position);
  const add = (price, color, title, style = LineStyle.Solid) => {
    if (numeric(price) && price > 0) priceLines.push(candles.createPriceLine({ price, color, title, lineWidth: 1, lineStyle: style, axisLabelVisible: true }));
  };
  const shown = active ? snap.position : position;
  if (shown) {
    add(shown.entry, '#b2bfd4', 'entry', LineStyle.Dashed);
    add(shown.bust, '#ffb454', 'bust', LineStyle.Dotted);
  }
  add(levels.takeProfit, COLORS.up, active ? 'TP armed' : 'TP');
  add(levels.stopLoss, COLORS.down, active ? 'SL armed' : 'SL');
}

function drawRibbon() {
  const canvas = $('ribbon'), ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth, height = canvas.clientHeight;
  if (canvas.width !== Math.round(width * ratio)) { canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio); }
  const context = canvas.getContext('2d');
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  const entries = book.recent(120), cell = width / 120, half = height / 2;
  let up = 0, down = 0, hit = 0, miss = 0;
  entries.forEach((entry, i) => {
    const x = width - (entries.length - i) * cell;
    context.globalAlpha = entry.tier === 'strong' ? 1 : entry.tier === 'lean' ? 0.55 : 1;
    context.fillStyle = entry.tier === 'warming' ? COLORS.warm : entry.direction === 'flat' ? '#4a5870' : COLORS[entry.direction];
    context.fillRect(x, 0, Math.max(1, cell - 0.5), half - 1);
    context.globalAlpha = 1;
    context.fillStyle = entry.outcome === 'hit' ? COLORS.up : entry.outcome === 'miss' ? COLORS.down : entry.outcome === null ? '#27344a' : '#1d2738';
    context.fillRect(x, half + 1, Math.max(1, cell - 0.5), half - 1);
    if (entry.direction === 'up') up++; else if (entry.direction === 'down') down++;
    if (entry.outcome === 'hit') hit++; else if (entry.outcome === 'miss') miss++;
  });
  canvas.setAttribute('aria-label', `Last ${entries.length} seconds: ${up} up calls, ${down} down calls; of ${hit + miss} settled, ${hit} right`);
}

/* ------------------------------------------------------------- read-outs -- */

const tileNodes = new Map();
const pct = value => `${(value * 100).toFixed(1)}%`;
const CALL_AT = HORIZONS.indexOf(HORIZON_S);
const tone = rate => rate >= 0.52 ? 'up' : rate <= 0.48 ? 'down' : 'flat';
/** The hover text of a tile: what it measures, how it votes, its record and its say in the call. */
function tileHelp(tile, share) {
  const recorded = variantById(tile.variant).prior[CALL_AT], live = experiments.stats(tile.variant);
  const record = (numeric(recorded) ? ` On the recording, following it over the next 30 seconds was right ${pct(recorded)} of the time.` : '')
    + (live.rate === null ? ' None of its own calls has settled yet in live testing.'
      : ` In live testing it has been right ${pct(live.rate)} of the time, over about ${Math.max(1, Math.round(live.eff))} independent calls’ worth of seconds.`);
  const say = numeric(share) ? ` Its say in the call right now: ${Math.round(share * 100)}%${share === 0 ? ', because its hit rate is not above 50%' : ''}.` : '';
  const tuned = tile.tuned ? ' The Experiments tab switched this setting in for the starting one (marked ★).' : '';
  return `${tile.label}. ${tile.describe} It votes up (green) when the reading is positive and down (red) when negative; grey is neutral.${record}${say}${tuned} Needs ${tile.need} closed one-second bars.`;
}
function buildTiles() {
  for (const slot of SCALP_EXPERIMENTS.slots) {
    const node = document.createElement('div');
    node.className = 'tile'; node.setAttribute('role', 'listitem'); node.dataset.vote = 'warming';
    const name = document.createElement('span'); name.className = 'name';
    const value = document.createElement('span'); value.className = 'value'; value.textContent = 'warming';
    // A bar for this tile's say in the call, relative to the tile with the most.
    const weight = document.createElement('span'); weight.className = 'weight'; weight.setAttribute('aria-hidden', 'true'); weight.append(document.createElement('i'));
    // One cell per horizon: this setting's own running hit rate over the next 5 s, 10 s, ... 5 min.
    const hits = document.createElement('span'); hits.className = 'hits';
    const cells = SCORE_HORIZONS.map(() => { const cell = document.createElement('i'); cell.textContent = '·'; hits.append(cell); return cell; });
    node.append(name, value, weight, hits); $('tiles').append(node); tileNodes.set(slot.key, { node, name, value, weight: weight.firstElementChild, cells });
  }
}
function tileText(tile) {
  if (!tile.ready) return `${tile.have}/${tile.need}s`;
  const mark = arrow(tile.vote);
  if (tile.kind === 'breakout') return tile.vote > 0 ? '▲ above' : tile.vote < 0 ? '▼ below' : '◆ inside';
  if (['zigzag', 'psar', 'supertrend'].includes(tile.kind)) return tile.vote > 0 ? '▲ up' : '▼ down';
  if (tile.unit === 'bars') return `${mark} ${Math.abs(tile.value)}`;
  return `${mark} ${signed(tile.value, 2)}${tile.unit ? ' ' + tile.unit : ''}`;
}
function drawTiles() {
  const tiles = view?.tiles ?? emptyTiles(), call = view?.call, weights = call?.ready ? call.weights : null;
  const top = weights ? Math.max(...weights) : 0;
  for (const [index, tile] of tiles.entries()) {
    const { node, name, value, weight, cells } = tileNodes.get(tile.key), share = weights ? weights[index] : null;
    node.dataset.vote = voteName(tile.ready ? tile.vote : null);
    node.toggleAttribute('data-tuned', tile.tuned);
    name.textContent = tile.tuned ? `${tile.label} ★` : tile.label;
    value.textContent = tileText(tile);
    weight.style.width = `${share !== null && top > 0 ? Math.round(share / top * 100) : 0}%`;
    node.title = tileHelp(tile, share);
    for (const [i, horizon] of SCORE_HORIZONS.entries()) {
      const score = experiments.stats(tile.variant, horizon), cell = cells[i], label = windowLabel(horizon), shown = score.rate !== null && score.n >= 10;
      cell.textContent = shown ? String(Math.round(score.rate * 100)) : '·';
      cell.dataset.vote = shown ? tone(score.rate) : 'warming';
      cell.title = shown ? `${label}: following ${tile.label} was right ${Math.round(score.rate * 100)}% of the time over the next ${label} (about ${Math.round(score.n)} calls counted, recent ones weighing most; seconds overlap).`
        : `${label}: too few ${tile.label} calls have settled at this interval yet.${numeric(score.prior) ? ` On the recording it was right ${pct(score.prior)} of the time.` : ''}`;
    }
    node.setAttribute('aria-label', `${tile.label}: ${tile.ready ? `${voteName(tile.vote)}, ${tileText(tile)}` : 'warming up'}. ${tile.describe}`);
  }
  $('tiles-count').textContent = call ? `${call.up} up · ${call.down} down · ${call.flat} flat` : '';
  const switched = tiles.filter(tile => tile.tuned).length;
  $('tab-experiments-count').textContent = switched ? `${switched} switched in` : '';
}

const slopeRows = new Map();
function buildSlopes() {
  for (const row of SCALP_MODEL.slopes) {
    const tr = document.createElement('tr'); tr.dataset.state = 'warming';
    const head = document.createElement('th'); head.scope = 'row'; head.textContent = windowLabel(row.window_s);
    const cells = ['slope', 'slopeRange', 'change', 'changeRange', 'held', 'runs', 'hit'].map(key => {
      const td = document.createElement('td'); td.dataset.cell = key; if (key.endsWith('Range')) td.className = 'range'; if (key === 'runs') td.className = 'runs';
      if (key === 'hit') { td.className = 'hit'; const gauge = document.createElement('span'); gauge.className = 'gauge'; gauge.append(document.createElement('i')); const text = document.createElement('span'); td.append(gauge, text); }
      return td;
    });
    const pct = stat => stat ? `${(stat.hit * 100).toFixed(1)}%` : 'n/a';
    head.title = `Recorded baseline for the ${windowLabel(row.window_s)} slope: it kept its sign ${row.runs.mean_s.toFixed(1)} s on average and ${row.runs.max_s.toFixed(0)} s at most `
      + `(${row.runs.count.toLocaleString()} runs). Following the slope was right ${pct(row.slope)} over the next 30 s; ${pct(row.accelerating)} while it steepened, ${pct(row.fading)} while it faded.`;
    tr.append(head, ...cells); $('slopes').tBodies[0].append(tr);
    slopeRows.set(row.window_s, { tr, cells: Object.fromEntries(cells.map(td => [td.dataset.cell, td])) });
  }
}
function drawSlopes() {
  const rows = view?.slopes ?? readSlopes([]), stats = new Map(slopeHistory.stats().map(row => [row.window, row])), scores = slopeScore.stats();
  for (const row of rows) {
    const { tr, cells } = slopeRows.get(row.window), history = stats.get(row.window);
    tr.dataset.state = row.state;
    if (!row.ready) {
      cells.slope.textContent = `${row.have}/${row.window}s`; delete cells.slope.dataset.vote; delete cells.change.dataset.vote;
      for (const key of ['slopeRange', 'change', 'changeRange', 'held', 'runs']) cells[key].textContent = '—';
      drawGauge(cells.hit, null, row);
      continue;
    }
    cells.slope.dataset.vote = voteName(row.slopeVote);
    cells.slope.textContent = `${arrow(row.slopeVote)} ${small(row.slope)}`;
    cells.slope.title = { accelerating: 'Slope and its change agree: the move is steepening', fading: 'The slope is losing steepness',
      steady: 'Slope is steady', flat: 'No slope' }[row.state] ?? '';
    cells.change.dataset.vote = voteName(row.changeVote);
    cells.change.textContent = `${arrow(row.changeVote)} ${small(row.change)}`;
    cells.change.title = row.changeVote > 0 ? 'The slope is increasing' : row.changeVote < 0 ? 'The slope is decreasing' : 'The slope is not changing';
    cells.slopeRange.textContent = history?.samples ? `${small(history.slope.min)} / ${small(history.slope.max)}` : '—';
    cells.changeRange.textContent = history?.samples ? `${small(history.change.min)} / ${small(history.change.max)}` : '—';
    const current = history?.current;
    cells.held.textContent = current?.sign ? `${arrow(current.sign)} ${current.sinceFlip ? '' : '≥'}${current.ageS}s` : '—';
    cells.runs.textContent = history?.runs.count ? `${history.runs.meanS.toFixed(0)} / ${history.runs.maxS}s` : 'none yet';
    cells.runs.title = history?.runs.count ? `${history.runs.count} completed runs this session. Up: ${history.runs.up.count ? `${history.runs.up.meanS.toFixed(0)} s avg, ${history.runs.up.maxS} s max` : 'none'}. `
      + `Down: ${history.runs.down.count ? `${history.runs.down.meanS.toFixed(0)} s avg, ${history.runs.down.maxS} s max` : 'none'}.` : 'No completed slope run yet in this session';
    drawGauge(cells.hit, scores.get(row.window), row);
  }
}

/** The running-accuracy cell of a ladder row: a bar centred on 50% and the count behind it. */
function drawGauge(cell, score, row) {
  const [gauge, text] = cell.children, rate = score?.rate ?? null;
  gauge.firstElementChild.style.width = `${rate === null ? 0 : Math.round(rate * 100)}%`;
  gauge.dataset.vote = rate === null ? 'flat' : rate >= 0.52 ? 'up' : rate <= 0.48 ? 'down' : 'flat';
  text.textContent = rate === null ? '—' : `${Math.round(rate * 100)}% · ${score.n}`;
  const baseline = row.measured?.slope ? ` Recorded baseline for this window: ${(row.measured.slope.hit * 100).toFixed(1)}%.` : '';
  cell.title = rate === null ? `No ${windowLabel(row.window)} slope call has settled yet: each needs 30 seconds.${baseline}`
    : `${score.hit} of ${score.n} settled ${windowLabel(row.window)} slope calls in the last ten minutes matched the move over the next 30 seconds.${baseline} Seconds overlap, so this is a gauge and not a trade record.`;
}

function drawCall(live) {
  const section = $('call'), call = view?.call, have = seconds.bars.length, need = warmupBars();
  const percent = stat => `${(stat.hit * 100).toFixed(1)}%`;
  // The only sample that played no part in choosing the grid; short, so it carries its error bar.
  const liveCheck = stat => stat.live ? ` On a separate short live check: ${percent(stat.live)} ± ${(stat.live.hit_se * 100).toFixed(1)}.` : '';
  // The weighted tiers' own replay figures; a tier too rare to measure shows none, never the unweighted one.
  const measured = call?.ready ? call.measured ?? null : null;
  let direction = 'flat', tier = 'warming', mark = '·', text, detail;
  if (!live) {
    text = 'No live price'; detail = 'The read-out resumes when the oracle stream is fresh again.';
  } else if (readoutError) {
    text = 'Read-out unavailable'; detail = readoutError;
  } else if (!call?.ready) {
    text = `Warming up · ${Math.min(have, need)} / ${need} s`;
    detail = `One-second bars come only from the live stream, so the grid needs ${need} seconds after opening or after a gap.`;
  } else {
    ({ direction, tier } = call);
    const score = `${signed(call.score * 100, 0)}%`, basis = 'On the later part of the recording, replayed without looking ahead, a weighted call like this';
    if (tier === 'mixed') {
      mark = '◆'; text = 'MIXED';
      detail = `Readings disagree once weighed (${call.up} up, ${call.down} down, weighted score ${score}). `
        + (measured ? `${basis} was a coin flip: ${percent(measured)} right.${liveCheck(measured)}` : 'This tier was too rare on the recording to measure.');
    } else {
      mark = direction === 'up' ? '▲' : '▼';
      text = tier === 'strong' ? `${direction.toUpperCase()} · strong` : `${direction} · lean`;
      detail = `The weighted score is ${score} (${call.up} readings up, ${call.down} down). `
        + (measured ? `${basis} was right ${percent(measured)} of the time over the next 30 s (average move ${signed(measured.mean_follow_bps, 2)} bp).${liveCheck(measured)}`
          : 'This tier was too rare on the recording to measure.');
      const breakout = view.tiles.find(tile => tile.kind === 'breakout' && tile.vote && (tile.vote > 0) === (direction === 'up'));
      if (breakout) detail += ` ${breakout.label} is in play; breakouts have the best record and the most say.`;
    }
    const switched = view.tiles.filter(tile => tile.tuned).length;
    if (switched) detail += ` ${switched} reading${switched === 1 ? ' uses' : 's use'} a setting the Experiments tab switched in; the recorded figures were measured on the starting settings, so read them as a guide.`;
    if (numeric(view.sigma)) detail += ` Typical 30 s move now: ±${(SCALP_MODEL.cone.p50 * view.sigma * Math.sqrt(HORIZON_S)).toFixed(1)} bp.`;
  }
  section.dataset.direction = direction; section.dataset.tier = tier;
  $('call-arrow').textContent = mark; $('call-text').textContent = text;
  // The explanation lives in the hover text; the line under the call keeps only the numbers.
  section.title = `${detail} The call weighs each of the sixteen readings by how far its running 30 second hit rate is above 50%; a reading at or under 50% has no say. `
    + 'A weighted score of 75% or more one way is strong, 37.5% or more is a lean, less is mixed. '
    + (VIEW_ONLY ? 'It is a lean: the average move after a strong call was under one basis point on the recording, less than the fees to open and close a Perps position (about 7 bp of position size on HYPE and ZEC, more on SOL, ETH and BTC). The figures were measured on the 1000x oracle price, not on the Perps mark price.'
      : 'It is a lean: the 1000x payout needs a hit rate far above these figures.');
  $('call-meta').textContent = !live || readoutError || !call?.ready ? ''
    : `${call.up}▲ ${call.down}▼ · weighted ${signed(call.score * 100, 0)}%`
      + (measured ? ` · recorded ${percent(measured)}${measured.live ? ` · live check ${percent(measured.live)} ± ${(measured.live.hit_se * 100).toFixed(1)}` : ''}` : ' · not measured')
      + `${numeric(view.sigma) ? ` · typical move ±${(SCALP_MODEL.cone.p50 * view.sigma * Math.sqrt(HORIZON_S)).toFixed(1)} bp` : ''}`;
  const stats = book.stats(), rate = row => `${row.hit}/${row.n} ${(row.rate * 100).toFixed(0)}%`;
  $('call-score').textContent = stats.all.n ? `session: ${stats.strong.n ? `strong ${rate(stats.strong)} · ` : ''}all ${rate(stats.all)}` : '';
  return { mark, text };
}

/* ------------------------------------------------------------ experiments -- */

const boardRows = new Map(), slotRows = new Map();
const element = (tag, text = '', title = '') => { const node = document.createElement(tag); node.textContent = text; if (title) node.title = title; return node; };
/** A hit-rate cell: filled when enough live calls have settled, plain coloured text when it is the recorded rate. */
function hitCell(cell, stats, horizon, label) {
  const live = stats.rate !== null && stats.eff >= 2 && stats.n >= 30, rate = live ? stats.rate : stats.prior, span = windowLabel(horizon);
  cell.textContent = numeric(rate) ? String(Math.round(rate * 100)) : '·';
  cell.dataset.vote = numeric(rate) ? tone(rate) : 'warming';
  cell.classList.toggle('rec', !live);
  cell.title = live ? `${label}, next ${span}: right ${pct(stats.rate)} of the time in live testing (about ${Math.round(stats.n)} calls counted, worth about ${Math.round(stats.eff)} independent ones).${numeric(stats.prior) ? ` Recorded: ${pct(stats.prior)}.` : ''}`
    : `${label}, next ${span}: ${numeric(stats.prior) ? `right ${pct(stats.prior)} of the time on the recording (shown as a plain number)` : 'no live figure yet'}. Live testing has ${Math.round(stats.n)} calls at this interval so far; a live figure is shown after about ${Math.max(30, 2 * horizon)} calls.`;
  cell.setAttribute('aria-label', `${numeric(rate) ? `${Math.round(rate * 100)} percent` : 'no figure'}, ${live ? 'live' : numeric(stats.prior) ? 'recorded' : 'waiting for calls'}`);
}
function buildExperiments() {
  const select = $('exp-horizon');
  for (const horizon of HORIZONS) { const option = element('option', windowLabel(horizon)); option.value = String(horizon); select.append(option); }
  select.value = String(rankHorizon);
  const head = $('exp-board').tHead.rows[0];
  for (const horizon of HORIZONS) {
    const th = element('th', windowLabel(horizon), `Hit rate, in percent, of following the setting over the next ${windowLabel(horizon)}. Filled cells are live results; plain coloured numbers are from the recording until enough live calls settle.`);
    th.scope = 'col'; th.dataset.horizon = String(horizon); head.append(th);
  }
  const calls = element('th', 'Calls', 'Live calls counted at the ranking interval, recent ones weighing most. Seconds overlap, so the number of independent calls is this divided by the interval length.'); calls.scope = 'col'; head.append(calls);
  for (const variant of VARIANTS) {
    const tr = document.createElement('tr'), name = element('th', variant.label, `${variant.label}. ${variant.describe} Needs ${variant.need} closed one-second bars.`); name.scope = 'row';
    const cells = HORIZONS.map(() => document.createElement('td')), count = document.createElement('td');
    tr.append(name, ...cells, count); boardRows.set(variant.id, { tr, name, cells, count });
  }
  for (const slot of SCALP_EXPERIMENTS.slots) {
    const tr = document.createElement('tr'), head = element('th', variantById(slot.variant).kindName); head.scope = 'row';
    const cells = Object.fromEntries(['setting', 'weight', 'live', 'recorded', 'rival'].map(key => [key, document.createElement('td')]));
    tr.append(head, ...Object.values(cells)); $('exp-slots').tBodies[0].append(tr); slotRows.set(slot.key, { tr, cells });
  }
}
function drawExperiments() {
  experimentsDrawnMs = Date.now();
  const tiles = view?.tiles ?? emptyTiles(), weights = view?.call?.ready ? view.call.weights : null, inUse = new Set(Object.values(assignments));
  const board = leaderboard(experiments, HORIZON_S), minutes = Math.floor(experiments.seconds / 60);
  const status = `Testing ${VARIANTS.length} settings at ${HORIZONS.length} intervals each second · ${minutes >= 120 ? `${(minutes / 60).toFixed(1)} h` : `${minutes} min`} of ${SYMBOL || 'no'} ticks scored so far`
    + ` · ${tiles.filter(tile => tile.tuned).length} of ${tiles.length} readings switched`;
  // A status region is announced when it changes, so it is written only then.
  if ($('exp-status').textContent !== status) $('exp-status').textContent = status;
  // What the switch rule itself would do at this moment, so the table never says otherwise.
  const pending = new Map(findPromotions({ assignments, book: experiments, locks: slotLocks, nowS: barClock() }).map(change => [change.slot, change.to]));
  $('exp-auto').checked = autoApply;
  for (const [index, tile] of tiles.entries()) {
    const { tr, cells } = slotRows.get(tile.key), stats = experiments.stats(tile.variant), share = weights ? weights[index] : null;
    tr.toggleAttribute('data-tuned', tile.tuned);
    cells.setting.textContent = tile.tuned ? `${tile.label} ★` : tile.label;
    cells.setting.title = tile.tuned ? `Switched in for ${variantById(DEFAULT_ASSIGNMENTS[tile.key]).label}, the starting setting.` : 'The starting setting.';
    cells.weight.textContent = share === null ? '—' : `${Math.round(share * 100)}%`;
    hitCell(cells.live, { ...stats, prior: null }, HORIZON_S, tile.label);
    cells.recorded.textContent = numeric(stats.prior) ? pct(stats.prior) : '—';
    // The setting the rule is about to switch in, else the unused one of the same kind with the best current estimate.
    const rival = board.find(row => row.id === pending.get(tile.key)) ?? board.find(row => row.kind === tile.kind && !inUse.has(row.id) && variantById(row.id).need <= PROMOTION.maxNeed);
    if (!rival) { cells.rival.textContent = '—'; cells.rival.title = 'No other setting of this kind can take this slot.'; continue; }
    const short = rival.eff < PROMOTION.minEff || stats.eff < PROMOTION.minEff, clear = pending.get(tile.key) === rival.id;
    cells.rival.textContent = rival.rate === null ? `${rival.label} · no live calls yet`
      : `${rival.label} · ${Math.round(rival.rate * 100)}%${clear ? (autoApply ? ' · clear winner, switching' : ' · clear winner') : short ? ' · needs more calls' : ' · not clearly ahead'}`;
    cells.rival.title = `${rival.label}: ${rival.rate === null ? 'no live calls yet' : `right ${pct(rival.rate)} live over about ${Math.round(rival.eff)} independent calls’ worth; its cautious estimate is ${pct(rival.lower)}`}. `
      + `It takes this slot when both it and the setting in use have ${PROMOTION.minEff} independent calls’ worth, its cautious estimate is above the setting in use’s live rate, it is at least ${Math.round(PROMOTION.minRate * 100)}% right, the recording does not say the opposite, and the slot has not changed in the last ${PROMOTION.lockS / 60} minutes. Settings that need more than ${PROMOTION.maxNeed} bars are tested but never switched in.`;
  }
  const ranked = rankHorizon === HORIZON_S ? board : leaderboard(experiments, rankHorizon), order = ranked.map(row => row.id).join(' '), body = $('exp-board').tBodies[0];
  for (const row of ranked) {
    const node = boardRows.get(row.id), variant = variantById(row.id);
    node.tr.toggleAttribute('data-in-use', inUse.has(row.id));
    node.name.textContent = inUse.has(row.id) ? `● ${variant.label}` : variant.label;
    for (const [i, horizon] of HORIZONS.entries()) hitCell(node.cells[i], experiments.stats(row.id, horizon), horizon, variant.label);
    node.count.textContent = String(Math.round(row.n));
  }
  // Rows are moved only when the ranking changed, so a hover is not interrupted every refresh.
  if (order !== boardOrder) { boardOrder = order; body.replaceChildren(...ranked.map(row => boardRows.get(row.id).tr)); }
  for (const th of $('exp-board').tHead.rows[0].cells) th.toggleAttribute('data-rank', th.dataset.horizon === String(rankHorizon));
  const list = $('exp-log').querySelector('ol');
  list.replaceChildren(...tuneLog.slice(-20).reverse().map(entry => element('li',
    `${clock(entry.at)} ${variantById(entry.from).kindName}: ${variantById(entry.from).label} → ${variantById(entry.to).label}`
    + (numeric(entry.rate) && numeric(entry.incumbentRate) ? ` (${Math.round(entry.rate * 100)}% against ${Math.round(entry.incumbentRate * 100)}% live)` : ''))));
  if (!tuneLog.length) list.append(element('li', 'No setting has been switched yet.'));
}
function showTab(name) {
  activeTab = name;
  for (const tab of ['live', 'experiments']) {
    $(`tab-${tab}`).setAttribute('aria-selected', String(tab === name)); $(`tab-${tab}`).tabIndex = tab === name ? 0 : -1;
    $(`panel-${tab}`).hidden = tab !== name;
  }
  if (name === 'experiments') drawExperiments(); else { drawRibbon(); queueDraw(); }
}
/** Switch in every setting that is clearly ahead of the one its tile uses. */
function tune(nowS) {
  if (!autoApply) return;
  const changes = findPromotions({ assignments, book: experiments, locks: slotLocks, nowS });
  for (const change of changes) {
    assignments = { ...assignments, [change.slot]: change.to };
    slotLocks[change.slot] = nowS;
    tuneLog.push({ at: Date.now(), slot: change.slot, from: change.from, to: change.to, rate: change.rate, incumbentRate: change.incumbentRate });
  }
  if (changes.length) { tuneLog = tuneLog.slice(-50); void saveExperiments(); }
}
/**
 * Keep what live testing has learned for this coin, so the next window carries on from it.
 * One key per coin and one write: two windows on different coins never overwrite each other.
 */
const coinKey = () => `${EXPERIMENT_STORAGE}.${SYMBOL}`;
async function saveExperiments() {
  experimentsSavedMs = Date.now();
  if (!SYMBOL_OK) return;
  try {
    await chrome.storage.local.set({ [coinKey()]: { savedAt: Date.now(), book: experiments.toJSON(), assignments, log: tuneLog.slice(-50) }, [EXPERIMENT_STORAGE]: { auto: autoApply } });
  } catch { /* learning is a convenience: the read-outs and the guard run without it */ }
}
async function loadExperiments() {
  try {
    const stored = await chrome.storage.local.get(SYMBOL_OK ? [EXPERIMENT_STORAGE, coinKey()] : [EXPERIMENT_STORAGE]);
    const shared = stored[EXPERIMENT_STORAGE], coin = SYMBOL_OK ? stored[coinKey()] : null;
    autoApply = !(shared && typeof shared === 'object' && shared.auto === false);
    // Saved rates that do not fit this version's grid are dropped, and the settings chosen from them with them.
    if (!coin || typeof coin !== 'object' || !experiments.restore(coin.book)) return;
    assignments = validAssignments(coin.assignments);
    tuneLog = (Array.isArray(coin.log) ? coin.log : []).filter(entry => entry && numeric(entry.at) && variantById(entry.from) && variantById(entry.to)).slice(-50)
      .map(entry => ({ at: entry.at, slot: String(entry.slot).slice(0, 24), from: entry.from, to: entry.to, rate: numeric(entry.rate) ? entry.rate : null, incumbentRate: numeric(entry.incumbentRate) ? entry.incumbentRate : null }));
  } catch { /* start from the recorded rates */ }
}

/* ------------------------------------------------------------------ guard -- */

const send = async (action, extra = {}) => {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'jupiterScalpWindow', action, ...extra });
    // The worker spreads a command's result over its envelope, so a relayed
    // { ok: false, reason } arrives with ok false and the result still attached.
    if (response?.result && typeof response.result === 'object') return response.result;
    return { ok: false, reason: 'extension_error', detail: response?.error };
  } catch {
    return { ok: false, reason: 'extension_unreachable' };
  }
};
const reasonText = reason => REASONS[reason] ?? String(reason ?? 'unknown reason').replaceAll('_', ' ');
const selectedPosition = () => positions.find(position => positionKey(position) === $('guard-position').value) ?? null;
const currentPrice = () => latest?.quote && quoteFresh(latest.quote, Date.now()) ? latest.quote.price : null;
const mode = () => document.querySelector('input[name="guard-mode"]:checked').value;
const decimalsOf = position => Math.max(4, (/\.(\d+)$/.exec(position?.entryText ?? '')?.[1].length) ?? 4);
const unit = () => $('guard-unit').value;
const size = () => Number(document.querySelector('input[name="entry-size"]:checked').value);
const form = () => pageState?.ok ? pageState.form ?? null : null;
/** Leverage chosen for the next entry: 500, 1000, or null to use what the page shows. */
const chosenLeverage = () => Number(document.querySelector('input[name="entry-leverage"]:checked').value) || null;
/** The fields read as price levels for a position; null for an empty or unusable field. */
const fieldLevels = position => {
  const levels = resolveLevels({ unit: unit(), takeProfitText: $('guard-tp').value, stopLossText: $('guard-sl').value, position });
  return { takeProfit: levels.takeProfit, stopLoss: levels.stopLoss };
};
/** Leverage the levels are judged against: the selected position's, else what the page's form shows. */
const planLeverage = () => selectedPosition()?.leverage ?? chosenLeverage() ?? form()?.leverage ?? null;
/** In bp mode, the fields whose number looks like this market's price rather than a distance. */
const priceLikeErrors = () => {
  if (unit() !== 'bp') return [];
  const price = latest?.quote?.price ?? null;
  return [['Take profit', 'guard-tp'], ['Stop loss', 'guard-sl']].flatMap(([label, id]) => {
    const distance = parseDistance($(id).value.trim());
    return distance !== null && priceLike(distance, price)
      ? [`${label} ${$(id).value.trim()} would be read as ${distance} bp from entry, but it looks like a price (${SYMBOL} is ${price}). Switch “as” to price to type prices, or enter the distance in basis points.`] : [];
  });
};
const note = (event, detail = {}) => {
  events.push({ at: Date.now(), event, ...detail });
  if (events.length > 60) events.shift();
  void chrome.storage.local.get(LOG_STORAGE).then(stored => {
    const log = Array.isArray(stored[LOG_STORAGE]) ? stored[LOG_STORAGE] : [];
    return chrome.storage.local.set({ [LOG_STORAGE]: [...log, { ...events.at(-1), symbol: SYMBOL }].slice(-200) });
  }).catch(() => {});
};

async function persist() {
  try { await chrome.storage.local.set({ [STORAGE]: settings }); } catch { /* the guard still runs; only the draft is lost */ }
}
async function record(snapshot) {
  try {
    const stored = (await chrome.storage.local.get(LOG_STORAGE))[LOG_STORAGE];
    const log = Array.isArray(stored) ? stored : [];
    const entry = snapshot.journal.at(-1);
    if (entry) log.push({ ...entry, symbol: SYMBOL, key: snapshot.position?.key ?? null });
    await chrome.storage.local.set({ [LOG_STORAGE]: log.slice(-200) });
  } catch { /* storage is a record, never a gate on a protective close */ }
}
function alertOwner(title, message) {
  try {
    chrome.notifications?.create(`smt-scalp-${Date.now()}`, { type: 'basic', iconUrl: chrome.runtime.getURL('icons/icon-128.png'),
      title, message, priority: 2, requireInteraction: true });
  } catch { /* the status line and the sound still report it */ }
  try {
    audio ??= new AudioContext();
    for (let i = 0; i < 3; i++) {
      const tone = audio.createOscillator(), gain = audio.createGain();
      tone.frequency.value = 880; gain.gain.value = 0.15; tone.connect(gain).connect(audio.destination);
      tone.start(audio.currentTime + i * 0.25); tone.stop(audio.currentTime + i * 0.25 + 0.15);
    }
  } catch { /* no audio device */ }
}

async function pressClose() {
  if (closing) return;
  closing = true;
  try {
    while (guard.snapshot().state === 'triggered' && !disposed) {
      const reply = await send('closePosition', { expect: guard.expect });
      const result = reply?.ok === false ? { clicked: false, retry: TRANSIENT.has(reply.reason), reason: reply.reason } : reply;
      const again = guard.onCloseResult(result, Date.now());
      void record(guard.snapshot());
      drawGuard();
      if (!again) break;
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    const snap = guard.snapshot();
    if (snap.state === 'clicked') alertOwner(`${SYMBOL} close pressed`, 'Approve in your wallet if it asks. Waiting for the position to leave the Jupiter list.');
    if (snap.state === 'failed') alertOwner(`${SYMBOL} guard could not close`, `Reason: ${reasonText(snap.note)}. The position may still be open.`);
  } finally {
    closing = false;
    drawGuard();
  }
}

function handleGuard(action) {
  if (!action) return;
  const snap = guard.snapshot(), label = action.reason === 'takeProfit' ? 'Take profit' : 'Stop loss';
  void record(snap);
  if (action.type === 'alert') alertOwner(`${SYMBOL} ${label.toLowerCase()} reached`, `Price ${action.price}. Alert only: nothing was pressed.`);
  else { alertOwner(`${SYMBOL} ${label.toLowerCase()} reached`, `Price ${action.price}. Pressing Close on the Jupiter page.`); void pressClose(); }
  drawGuard();
}

async function pollPositions() {
  if (polling || !attached || disposed) return;
  polling = true; lastPollMs = Date.now();
  try {
    pageState = await send('positions');
    const readable = pageState?.ok && pageState.recognized;
    const listed = readable ? pageState.positions : null;
    positions = readable ? listed.filter(position => position.coin === SYMBOL) : positions;
    const change = guard.onPositions(listed, Date.now(), readable && !pageState.pending && !pageState.unreadable);
    {
      // Every poll, readable or not: the wait for a new position must end even when the page cannot be read.
      const whole = readable && !pageState.pending && !pageState.unreadable, was = entry.snapshot().state;
      const opened = entry.onPositions({ positions: whole ? listed : null, coin: SYMBOL, keyOf: positionKey, nowMs: Date.now() });
      if (opened) onOpened(opened);
      else if (was === 'sent' && entry.snapshot().state === 'unseen') { note('entry-unseen', {}); alertOwner(`${SYMBOL} entry not confirmed`, 'No new position was listed within 60 seconds. Check your wallet and the Jupiter tab.'); }
    }
    if (change) {
      void record(guard.snapshot());
      if (change === 'closed') alertOwner(`${SYMBOL} position closed`, 'It left the Jupiter list. Check History for the fill.');
      if (change === 'unconfirmed') alertOwner(`${SYMBOL} close not confirmed`, `Close was pressed but ${reasonText(guard.snapshot().note)}. Check your wallet and the Jupiter tab.`);
      if (change === 'position_gone') alertOwner(`${SYMBOL} guard disarmed`, 'The position is no longer listed on the Jupiter page.');
    }
    drawPositions();
    drawGuard();
  } finally {
    polling = false;
  }
}

function drawPositions() {
  const select = $('guard-position'), keep = select.value;
  const keys = positions.map(positionKey);
  if (keys.join('\n') !== [...select.options].map(option => option.value).join('\n')) {
    select.replaceChildren(...positions.map(position => {
      const option = document.createElement('option');
      option.value = positionKey(position);
      option.textContent = `${position.coin} · ${position.leverage.toLocaleString()}× ${position.side} · entry ${position.entryText}`;
      return option;
    }));
    if (keys.includes(keep)) select.value = keep;
  }
  const readable = pageState?.ok && pageState.recognized;
  $('guard-page').textContent = VIEW_ONLY ? `Opened from the Jupiter Perps page for ${SYMBOL || 'no market'}.`
    : !attached ? 'Open this window from the “1s scalp” button on the Jupiter 1000x tab to use the guard.'
    : !readable ? `Cannot read positions: ${reasonText(pageState?.reason)}.`
      : positions.length ? `${positions.length} open ${SYMBOL} position${positions.length > 1 ? 's' : ''} on the Jupiter tab.`
        : `No open ${SYMBOL} position is listed on the Jupiter tab${pageState.pending ? ' (one is still opening)' : ''}.`;
  const order = form();
  if (attached && readable) {
    $('guard-page').textContent += !order?.recognized ? ' Order form not readable.'
      : order.market !== SYMBOL ? ` The Jupiter tab is on ${order.market || 'another market'}.`
        : ` Available ${order.balanceText ?? 'n/a'} · page leverage ${order.leverage ? `${order.leverage.toLocaleString()}×` : 'n/a'} · ${order.mode ?? 'mode n/a'}.`;
  }
  if (readable && pageState.unreadable) $('guard-page').textContent += ` ${pageState.unreadable} listed row${pageState.unreadable > 1 ? 's' : ''} could not be read (${pageState.problems.map(reasonText).join(', ')}).`;
  const position = selectedPosition();
  $('guard-position-detail').textContent = position
    ? `Mark ${numeric(position.mark) ? position.mark : 'n/a'} · bust ${numeric(position.bust) ? position.bust : 'n/a'} · collateral ${position.collateral || 'n/a'} · ${position.mode || 'mode n/a'} · Close button: ${position.close.state}${position.close.label && position.close.state !== 'ready' ? ` (${position.close.label})` : ''}`
    : '';
}

/** The computed line under a level field: its price or distance and the page formula's estimate. */
function levelNote(position, text, kind) {
  if (!text.trim()) return kind === 'tp' ? 'No take profit.' : 'No stop loss.';
  const bp = unit() === 'bp', leverage = planLeverage();
  if (bp) {
    const distance = parseDistance(text);
    if (distance === null) return 'Enter a distance in basis points, for example 10.';
    if (priceLike(distance, latest?.quote?.price ?? null)) return `Looks like a price. Read as ${distance} bp from entry: switch “as” to price.`;
    const move = (kind === 'tp' ? 1 : -1) * distance;
    // Before a position exists the estimate uses a unit entry: the formula depends only on the move.
    const estimate = leverage ? payoutPercent({ entry: 1e6, mark: 1e6 * (1 + move / 1e4), side: 'long', leverage }) : null;
    let text2 = position ? `at ${(position.entry * (1 + (position.side === 'long' ? 1 : -1) * move / 1e4)).toFixed(decimalsOf(position))}` : 'from the fill';
    if (estimate) text2 += estimate.liquidated ? ' · beyond bust' : ` · est. ${signed(estimate.percent, 0)}%`;
    if (kind === 'sl' && leverage) text2 += ` · ${Math.round(distance / (bustFraction(leverage) * 1e4) * 100)}% to bust`;
    return text2;
  }
  const level = parseLevel(text);
  if (level === null) return 'Enter a plain price, for example 71.85.';
  if (!position) return 'Price levels need an open position.';
  const favourable = (position.side === 'long' ? 1 : -1) * (level / position.entry - 1) * 1e4;
  const estimate = payoutPercent({ entry: position.entry, mark: level, side: position.side, leverage: position.leverage });
  let text2 = `${signed(favourable, 1)} bp from entry`;
  if (estimate) text2 += estimate.liquidated ? ' · beyond bust' : ` · est. ${signed(estimate.percent, 0)}%`;
  if (kind === 'sl' && numeric(position.bust)) text2 += ` · ${Math.round(Math.abs(level - position.entry) / Math.abs(position.bust - position.entry) * 100)}% to bust`;
  return text2;
}

/** Tell the worker when a guard is live, and hold a Web Lock so Chrome does not freeze this window under it. */
function reportLive(live) {
  if (live === reportedLive) return;
  reportedLive = live;
  if (attached) void send('guardState', { live });
  if (live && !releaseLock) void navigator.locks?.request('smt-1000x-scalp-guard', () => new Promise(resolve => { releaseLock = resolve; }));
  if (!live && releaseLock) { releaseLock(); releaseLock = null; }
}

function drawGuard() {
  const snap = guard.snapshot(), now = Date.now(), position = selectedPosition();
  const live = currentPrice() !== null, readable = pageState?.ok && pageState.recognized;
  const busy = LIVE_STATES.includes(snap.state);
  $('guard').dataset.state = snap.state;
  reportLive(busy);
  $('guard-badge').textContent = { idle: 'Disarmed', armed: snap.mode === 'close' ? 'Armed · will press Close' : 'Armed · alert only', triggered: 'Triggered',
    clicked: 'Close pressed', closed: 'Closed', alerted: 'Level reached', unconfirmed: 'Not confirmed', failed: 'Failed' }[snap.state];
  for (const id of ['guard-position', 'guard-tp', 'guard-sl', 'guard-unit']) $(id).disabled = busy;
  for (const input of document.querySelectorAll('input[name="guard-mode"], .chips button')) input.disabled = busy;
  drawEntry(busy);
  $('guard-arm').hidden = busy; $('guard-disarm').hidden = !busy; $('guard-disarm').disabled = snap.state !== 'armed';
  $('guard-arm').disabled = !attached || !position;
  $('guard-arm').textContent = mode() === 'close' ? 'Arm · press Close' : 'Arm · alert only';
  $('guard-show').disabled = !linked;
  for (const id of ['guard-tp-unit', 'guard-sl-unit']) $(id).textContent = unit() === 'bp' ? '(bp from entry)' : '(price)';
  $('guard-tp-note').textContent = levelNote(position, $('guard-tp').value, 'tp');
  $('guard-sl-note').textContent = levelNote(position, $('guard-sl').value, 'sl');
  const levels = [snap.levels.takeProfit !== null ? `TP ${snap.levels.takeProfit}` : null, snap.levels.stopLoss !== null ? `SL ${snap.levels.stopLoss}` : null].filter(Boolean).join(' · ');
  const which = snap.trigger?.reason === 'takeProfit' ? 'Take profit' : 'Stop loss';
  const unprotected = snap.state === 'armed' && (!live || (snap.mode === 'close' && !readable));
  $('guard').toggleAttribute('data-unprotected', unprotected);
  let status;
  if (snap.state === 'idle') status = snap.note === 'position_gone' ? 'Disarmed: the position is no longer listed on the Jupiter page.' : 'Disarmed. Nothing is watched.';
  else if (snap.state === 'armed') status = unprotected
    ? `ARMED BUT NOT PROTECTED: ${!live ? 'no fresh price' : `cannot read the Jupiter page (${reasonText(pageState?.reason)})`}. ${levels}`
    : `Armed · ${levels} · ${snap.mode === 'close' ? 'will press Close on the Jupiter page' : 'alert only'} · price ${((now - latest.quote.exchangeMs) / 1000).toFixed(1)} s old`;
  else if (snap.state === 'triggered') status = `${which} reached at ${snap.trigger.price}. Pressing Close on the Jupiter page…${snap.note ? ` (${reasonText(snap.note)})` : ''}`;
  else if (snap.state === 'clicked') status = `${which} reached at ${snap.trigger.price}. Close pressed at ${clock(snap.clickedAt)}. Approve in your wallet if it asks; waiting for the position to leave the list.`;
  else if (snap.state === 'closed') status = `Closed: the position left the Jupiter list after the ${which.toLowerCase()} at ${snap.trigger.price}. Check History for the fill.`;
  else if (snap.state === 'alerted') status = `${which} reached at ${snap.trigger.price} (${clock(snap.trigger.at)}). Alert only: nothing was pressed.`;
  else if (snap.state === 'unconfirmed') status = `Close was pressed but ${snap.note === 'page_unreadable' ? 'the Jupiter page can no longer be read, so the outcome is unknown' : 'the position is still listed'}. Check the wallet prompt and the Jupiter tab. The guard will not press again.`;
  else status = `COULD NOT CLOSE: ${reasonText(snap.note)}. The position may still be open; act on the Jupiter tab.`;
  if (status !== lastStatus) { $('guard-status').textContent = status; lastStatus = status; }
  const merged = [...snap.journal, ...events].sort((a, b) => a.at - b.at);
  if (merged.length !== logCount) {
    logCount = merged.length;
    $('guard-log').querySelector('ol').replaceChildren(...merged.map(row => {
      const item = document.createElement('li');
      const { at, event, ...rest } = row;
      item.textContent = `${clock(at)} ${event} ${Object.entries(rest).filter(([, value]) => value !== null && value !== undefined).map(([key, value]) => `${key}=${value}`).join(' ')}`;
      return item;
    }));
  }
  drawPriceLines();
}

function arm(event) {
  if (!event.isTrusted) return;
  const errors = [], position = selectedPosition();
  const levels = resolveLevels({ unit: unit(), takeProfitText: $('guard-tp').value, stopLossText: $('guard-sl').value, position });
  errors.push(...(position ? levels.errors : []), ...priceLikeErrors());
  const { takeProfit, stopLoss } = levels;
  if (position && positions.filter(row => positionKey(row) === positionKey(position)).length !== 1) {
    errors.push('Two listed positions look identical (same market, side, leverage and entry), so the guard could not tell them apart.');
  }
  if (mode() === 'close' && position && !['ready', 'locked', 'disabled'].includes(position.close.state)) {
    errors.push('This position has no Close button the guard can press (it may be a locked mode or already closing).');
  }
  if (!errors.length) {
    const result = guard.arm({ position, price: currentPrice(), takeProfit, stopLoss, mode: mode(), nowMs: Date.now() });
    errors.push(...result.errors);
    if (result.ok) {
      saveSettings(); void record(guard.snapshot());
      // Arming is the gesture that lets the alert sound play later.
      try { audio ??= new AudioContext(); void audio.resume(); } catch { /* no audio device */ }
    }
  }
  $('guard-errors').textContent = errors.join(' ');
  drawGuard();
}

function fillLevel(button) {
  $('guard-errors').textContent = '';
  if (button.dataset.clear) {
    if (button.dataset.clear !== 'sl') $('guard-tp').value = '';
    if (button.dataset.clear !== 'tp') $('guard-sl').value = '';
  } else if (unit() === 'bp') {
    const leverage = planLeverage();
    if (button.dataset.tp) $('guard-tp').value = button.dataset.tp;
    else if (!leverage) $('guard-errors').textContent = 'The leverage could not be read from the Jupiter page, so the bust distance is unknown.';
    else $('guard-sl').value = (Number(button.dataset.sl) * bustFraction(leverage) * 1e4).toFixed(2);
  } else {
    const position = selectedPosition(), price = currentPrice();
    if (!position || price === null) $('guard-errors').textContent = 'Price levels need an open position and a live price.';
    else if (button.dataset.tp) $('guard-tp').value = (price * (1 + (position.side === 'long' ? 1 : -1) * Number(button.dataset.tp) / 1e4)).toFixed(decimalsOf(position));
    else if (!numeric(position.bust)) $('guard-errors').textContent = 'The bust price could not be read from the page.';
    else $('guard-sl').value = (price + Number(button.dataset.sl) * (position.bust - price)).toFixed(decimalsOf(position));
  }
  saveSettings();
  drawGuard();
}

/* ------------------------------------------------------------------ entry -- */

function saveSettings() {
  settings = { mode: mode(), unit: unit(), takeProfit: $('guard-tp').value.trim(), stopLoss: $('guard-sl').value.trim() };
  void persist();
}

/** Why Long or Short cannot be pressed right now, or '' when they can. */
function entryBlock(guardLive) {
  const order = form();
  if (!attached) return 'Open this window from the Jupiter 1000x tab.';
  if (!$('entry-unlock').checked) return 'Tick Unlock to enable Long and Short.';
  if (guardLive) return 'A take profit or stop loss is live. Disarm it first.';
  if (entry.pending || opening) return 'An entry request is out.';
  // The new position is found by comparing the list before and after, so the list must be whole now.
  if (!pageState?.ok || !pageState.recognized) return `Cannot read the positions list: ${reasonText(pageState?.reason)}. Show the Positions tab on the Jupiter page.`;
  if (pageState.pending || pageState.unreadable) return 'A listed position is still opening or could not be read.';
  if (!order?.recognized) return `Cannot read the order form: ${reasonText(order?.reason ?? pageState?.reason)}.`;
  if (order.market !== SYMBOL) return `The Jupiter tab is on ${order.market || 'another market'}, not ${SYMBOL}.`;
  if (order.mode !== 'Classic') return 'Switch the Jupiter page to Classic mode.';
  if (!order.leverage) return 'The page’s leverage could not be read.';
  if (currentPrice() === null) return 'No fresh price.';
  return '';
}

function drawEntry(guardLive) {
  const snap = entry.snapshot(), block = entryBlock(guardLive), order = form();
  const label = { 0.25: '¼', 0.5: '½', 0.75: '¾', 1: 'all' };
  for (const side of ['long', 'short']) {
    const button = $(`entry-${side}`), confirming = snap.state === 'confirming' && snap.request.side === side;
    button.disabled = Boolean(block) || (order?.recognized && !order[`${side}Enabled`]);
    // A disabled button says why on hover, ahead of its standing description.
    button.dataset.help ??= button.title;
    const why = block || (button.disabled ? `The Jupiter page has its ${side} button disabled.` : '');
    button.title = why ? `${why} — ${button.dataset.help}` : button.dataset.help;
    button.toggleAttribute('data-confirming', confirming);
    button.textContent = confirming ? `Confirm ${side} ${label[snap.request.fraction]}` : side;
  }
  for (const input of document.querySelectorAll('input[name="entry-size"], input[name="entry-leverage"]')) input.disabled = entry.pending || opening;
  const request = snap.request, status = $('entry-status');
  status.dataset.state = snap.state;
  const planned = chosenLeverage() ?? order?.leverage;
  status.textContent = snap.state === 'confirming' ? `Press ${request.side} again within 4 s to open ${label[request.fraction]} of the available funds at ${planned ? `${planned.toLocaleString()}×` : 'the page’s leverage'}.`
    : snap.state === 'sent' ? (request.uncertain
      ? `The Jupiter tab did not answer (${reasonText(snap.note)}), so the ${request.side} may or may not have been pressed. Check the Jupiter tab; watching for a new position.`
      : request.clickedAt
        ? `${request.side} pressed for ${request.amountText ?? '?'} at ${request.leverage ? `${request.leverage.toLocaleString()}×` : 'the page’s leverage'}. Approve in your wallet if it asks; waiting for the position to be listed.`
        : `Asking the Jupiter page to open a ${request.side}…`)
      : snap.state === 'opened' ? `Opened ${request.side}. ${guard.snapshot().state === 'armed' ? 'Levels armed from its entry.' : 'No take profit or stop loss is armed.'}`
        : snap.state === 'unseen' ? `No new ${request.side} was listed within 60 s. Check the wallet prompt and the Jupiter tab; a position listed in the next ten minutes still gets its levels.`
          : snap.state === 'failed' ? `NOT OPENED: ${reasonText(snap.note)}. The page’s ${request.side} button was not pressed.`
            : block && $('entry-unlock').checked ? block : '';
}

async function pressSide(event) {
  // detail counts clicks in one burst: the second half of a double-click is not a new decision.
  if (!event.isTrusted || event.detail > 1 || opening) return;
  const side = event.currentTarget.dataset.side, errors = [], guardLive = LIVE_STATES.includes(guard.snapshot().state);
  const block = entryBlock(guardLive);
  if (block) errors.push(block);
  const takeProfitText = $('guard-tp').value.trim(), stopLossText = $('guard-sl').value.trim();
  // A new position has no entry until it fills, so its levels must be distances.
  if ((takeProfitText || stopLossText) && unit() !== 'bp') errors.push('A new position needs its levels as distances: switch “as” to bp from entry, or clear them.');
  const takeProfitBps = takeProfitText ? parseDistance(takeProfitText) : null, stopLossBps = stopLossText ? parseDistance(stopLossText) : null;
  if (takeProfitText && takeProfitBps === null) errors.push('Take profit is not a plain distance in basis points.');
  if (stopLossText && stopLossBps === null) errors.push('Stop loss is not a plain distance in basis points.');
  errors.push(...priceLikeErrors());
  const order = form(), leverage = chosenLeverage() ?? order?.leverage ?? null;
  if (!errors.length) {
    errors.push(...validateEntry({ side, fraction: size(), takeProfitBps, stopLossBps, bustBps: leverage ? bustFraction(leverage) * 1e4 : null,
      form: order, guardLive, pending: entry.pending }).errors);
  }
  $('guard-errors').textContent = errors.join(' ');
  if (errors.length) { drawGuard(); return; }
  const before = (pageState.positions ?? []).map(positionKey);
  const step = entry.begin({ side, fraction: size(), takeProfitBps, stopLossBps, mode: mode(), before, confirm: $('entry-confirm').checked, nowMs: Date.now() });
  saveSettings();
  try { audio ??= new AudioContext(); void audio.resume(); } catch { /* no audio device */ }
  if (!step.send) { drawGuard(); return; }
  opening = true;
  note('entry-requested', { side, fraction: size(), leverage, takeProfitBps, stopLossBps, mode: mode() });
  drawGuard();
  try {
    // One request, never repeated: a missing reply is reported, and the owner checks the Jupiter tab.
    const reply = await send('openPosition', { side, fraction: size(), ...(chosenLeverage() ? { leverage: chosenLeverage() } : {}) });
    entry.onReply(reply?.ok === false ? { clicked: false, reason: reply.reason } : reply, Date.now());
    const snap = entry.snapshot();
    if (snap.state === 'failed') { note('entry-failed', { reason: snap.note, detail: reply?.detail }); alertOwner(`${SYMBOL} ${side} was not opened`, `Reason: ${reasonText(snap.note)}.`); }
    else if (snap.request.uncertain) { note('entry-unknown', { reason: snap.note }); alertOwner(`${SYMBOL} ${side}: outcome unknown`, 'The Jupiter tab did not answer. Check it: the position may have opened.'); }
    else note('entry-pressed', { side, amount: snap.request.amountText, leverage: snap.request.leverage });
  } finally {
    opening = false;
    drawGuard();
  }
}

/** A position this window opened has been listed: select it and arm its levels from the real entry. */
function onOpened({ position, request }) {
  note('entry-listed', { key: positionKey(position), entry: position.entryText });
  positions = pageState.positions.filter(row => row.coin === SYMBOL);
  drawPositions();
  $('guard-position').value = positionKey(position);
  if (request.takeProfitBps === null && request.stopLossBps === null) { alertOwner(`${SYMBOL} ${request.side} opened`, `Entry ${position.entryText}. No take profit or stop loss is armed.`); return; }
  const levels = resolveLevels({ unit: 'bp', takeProfitText: request.takeProfitBps === null ? '' : String(request.takeProfitBps),
    stopLossText: request.stopLossBps === null ? '' : String(request.stopLossBps), position });
  const result = levels.errors.length ? { ok: false, errors: levels.errors }
    // Price may already be past a level set before the fill. Arm anyway and let the next line act on it.
    : guard.arm({ position, price: currentPrice(), takeProfit: levels.takeProfit, stopLoss: levels.stopLoss, mode: request.mode, allowCrossed: true, nowMs: Date.now() });
  if (result.ok) {
    void record(guard.snapshot());
    alertOwner(`${SYMBOL} ${request.side} opened`, `Entry ${position.entryText}. Levels armed (${request.mode === 'close' ? 'will press Close' : 'alert only'}).`);
    if (latest?.quote) handleGuard(guard.onQuote(latest.quote, Date.now()));
  }
  else {
    // The position is open with no protection: say so as loudly as a failed close.
    $('guard-errors').textContent = `The position opened but its levels could not be armed: ${result.errors.join(' ')}`;
    note('arm-failed', { reason: result.errors.join(' ') });
    alertOwner(`${SYMBOL} ${request.side} opened WITHOUT its levels`, result.errors.join(' '));
  }
}

/* ------------------------------------------------------------------- loop -- */

function onClosed(count) {
  const bars = seconds.bars;
  for (let k = count; k >= 1; k--) {
    const prefix = k === 1 ? bars : bars.slice(0, bars.length - k + 1);
    const bar = prefix.at(-1), readings = experiments.observe(prefix);
    if (bar.time % PROMOTION.everyS === 0) tune(bar.time);
    const tiles = readSlots(assignments, readings, prefix.length), call = weightedCall(tiles, experiments), slopes = readSlopes(prefix);
    book.observe(bar, call);
    slopeHistory.observe(slopes);
    slopeScore.observe(bar, slopes);
    if (k === 1) view = { tiles, call, slopes, sigma: realizedVolBps(bars, 30) };
  }
  barsVersion++;
  if (Date.now() - experimentsSavedMs >= 60_000) void saveExperiments();
}

function onUpdate(snapshot) {
  latest = snapshot;
  const quote = snapshot.quote;
  if (quote && quote.exchangeMs > lastQuoteMs) {
    lastQuoteMs = quote.exchangeMs;
    // The guard comes first: a fault in the read-outs must never cost a trigger.
    handleGuard(guard.onQuote(quote, Date.now()));
    try {
      const closed = seconds.push(quote);
      if (closed === -1) { book.reset(); slopeHistory.reset(); slopeScore.reset(); experiments.reset(); view = null; barsVersion++; }
      else if (closed > 0) onClosed(closed);
      readoutError = '';
    } catch (error) {
      seconds.reset(); book.reset(); slopeHistory.reset(); slopeScore.reset(); experiments.reset(); view = null; barsVersion++;
      readoutError = `The read-out failed and restarted (${String(error?.message ?? error).slice(0, 80)}). The guard is unaffected.`;
    }
    // Quotes keep arriving in a hidden window where timers are throttled; use them as the clock too.
    tick();
  }
  queueDraw();
}

/** (Re)start the public feed. A terminal feed is replaced, never left dead under an armed guard. */
async function startFeed() {
  lastFeedStartMs = Date.now();
  feed?.stop();
  feed = new JupiterFeed({ symbol: SYMBOL, intervalSec: 60, onUpdate });
  try { await feed.start(); } catch { $('feed').textContent = 'Jupiter data unavailable'; $('feed').dataset.state = 'error'; }
}

/** Guard timeouts, the positions poll, the feed watchdog and the repeated unprotected alarm. */
function tick() {
  if (disposed) return;
  const now = Date.now(), snap = guard.snapshot();
  if (guard.onTimeout(now)) { void record(guard.snapshot()); alertOwner(`${SYMBOL} guard could not close`, 'The Close button stayed unavailable. The position may still be open.'); }
  if (entry.onTick(now)) drawGuard();
  if (now - lastPollMs >= (snap.state === 'idle' && !entry.pending ? 1000 : 400)) void pollPositions();
  if (feed && FEED_RESTART.has(latest?.error) && now - lastFeedStartMs >= 15_000) void startFeed();
  const unprotected = snap.state === 'armed' && (currentPrice() === null || (snap.mode === 'close' && !(pageState?.ok && pageState.recognized)));
  if (!unprotected) unprotectedAlertMs = 0;
  else if (unprotectedAlertMs === 0) unprotectedAlertMs = now + 4000; // ride out a one-quote hiccup before sounding
  else if (now >= unprotectedAlertMs) {
    unprotectedAlertMs = now + 30_000;
    alertOwner(`${SYMBOL} guard is NOT protecting`, currentPrice() === null ? 'No fresh price is arriving. The levels are not being watched.'
      : `The Jupiter page cannot be read (${reasonText(pageState?.reason)}). A level could not be acted on.`);
  }
}

function draw() {
  drawQueued = false;
  if (disposed) return;
  const quote = latest?.quote, live = Boolean(quote && latest.streamStatus === 'live' && quoteFresh(quote, Date.now()));
  $('coin').disabled = LIVE_STATES.includes(guard.snapshot().state) || entry.pending || opening;
  $('price').textContent = quote ? `$${quote.price.toLocaleString(undefined, { maximumFractionDigits: 6 })}` : '—';
  const state = live ? 'live' : latest?.status === 'error' || latest?.status === 'unsupported' ? 'error' : quote ? 'stale' : 'connecting';
  $('feed').dataset.state = state;
  $('feed').textContent = live ? `Live oracle price · ${((Date.now() - quote.exchangeMs) / 1000).toFixed(1)} s old · ${seconds.bars.length} one-second bars`
    : FEED_TEXT[latest?.error] ?? (quote ? 'Price is stale; waiting for a fresh update' : 'Connecting to Jupiter…');
  // A fault in drawing a read-out must never keep the order panel from refreshing.
  try {
    const { mark, text } = drawCall(live);
    document.title = `${mark} ${SYMBOL} ${quote ? quote.price : ''} · ${text}`;
    if (activeTab === 'live') drawChart();
    if (drawnVersion !== barsVersion) { drawnVersion = barsVersion; drawRibbon(); drawTiles(); drawSlopes(); }
    if (activeTab === 'experiments' && Date.now() - experimentsDrawnMs >= 2000) drawExperiments();
  } catch (error) {
    readoutError = `A read-out could not be drawn (${String(error?.message ?? error).slice(0, 80)}). The guard is unaffected.`;
  }
  drawGuard();
}
function queueDraw() {
  if (drawQueued || disposed) return;
  drawQueued = true;
  // A hidden window gets no animation frames; the guard does not depend on drawing.
  if (document.hidden) setTimeout(draw, 200); else requestAnimationFrame(draw);
}

$('version').textContent = `v${chrome.runtime.getManifest().version}`;

/** The coin dropdown: the public catalog's markets, with the watched one selected. */
async function loadCoins() {
  const select = $('coin');
  const option = (symbol, text = symbol) => { const node = document.createElement('option'); node.value = symbol; node.textContent = text; return node; };
  select.replaceChildren(option(SYMBOL || '', SYMBOL || 'No market'));
  try {
    const response = await fetch(JUPITER_ENDPOINTS.markets, { credentials: 'omit', cache: 'no-store' });
    const markets = (await response.json())?.markets;
    if (!response.ok || !Array.isArray(markets)) return;
    const listed = markets.filter(market => /^[A-Z][A-Z0-9]{0,11}$/.test(market?.symbol ?? '')).slice(0, 40);
    if (!listed.some(market => market.symbol === SYMBOL)) return;
    select.replaceChildren(...listed.map(market => option(market.symbol, market.closed ? `${market.symbol} (closed)` : market.symbol)));
    select.value = SYMBOL;
  } catch { /* the list is a convenience; the watched coin stays selected */ }
}
/** Watch another coin: the worker re-binds this window to it, then the window reloads clean. */
async function changeCoin() {
  const next = $('coin').value;
  if (next === SYMBOL || !/^[A-Z][A-Z0-9]{0,11}$/.test(next)) return;
  if (LIVE_STATES.includes(guard.snapshot().state) || entry.pending || opening) { $('coin').value = SYMBOL; return; }
  if (linked) {
    const reply = await send('setMarket', { market: next });
    if (reply?.ok !== true) { $('coin').value = SYMBOL; $('guard-errors').textContent = `Could not switch coin: ${reasonText(reply?.reason)}.`; return; }
  }
  const url = new URL(location.href);
  url.hash = VIEW_ONLY ? `market=${next}&venue=perps` : `market=${next}`;
  location.replace(url.href);
  location.reload();
}
$('coin').addEventListener('change', () => void changeCoin());
void loadCoins();
$('api-attribution').textContent = `${POWERED_BY} — 1000x public catalog; Pyth oracle stream.`;
await loadExperiments();
// The read-outs are built inside a guard of their own: a fault here must not stop the order panel being wired below.
try { buildTiles(); buildSlopes(); buildExperiments(); }
catch (error) { readoutError = `The read-outs could not be built (${String(error?.message ?? error).slice(0, 80)}). The guard is unaffected.`; }
for (const tab of ['live', 'experiments']) {
  $(`tab-${tab}`).addEventListener('click', () => showTab(tab));
  $(`tab-${tab}`).addEventListener('keydown', event => {
    const other = { ArrowLeft: tab === 'live' ? 'experiments' : 'live', ArrowRight: tab === 'live' ? 'experiments' : 'live', Home: 'live', End: 'experiments' }[event.key];
    if (!other) return;
    event.preventDefault();
    showTab(other); $(`tab-${other}`).focus();
  });
}
$('exp-auto').addEventListener('change', () => { autoApply = $('exp-auto').checked; void saveExperiments(); });
$('exp-horizon').addEventListener('change', () => { rankHorizon = HORIZONS.includes(Number($('exp-horizon').value)) ? Number($('exp-horizon').value) : HORIZON_S; drawExperiments(); });
$('exp-defaults').addEventListener('click', () => {
  // Back to the starting settings; each tile is then left alone for the usual lock time.
  const nowS = barClock();
  assignments = { ...DEFAULT_ASSIGNMENTS }; slotLocks = Object.fromEntries(Object.keys(assignments).map(key => [key, nowS]));
  view = null; barsVersion++; void saveExperiments(); drawExperiments(); queueDraw();
});
$('exp-forget').addEventListener('click', event => {
  const button = $('exp-forget'), now = Date.now();
  // Two separate presses within four seconds: this throws away everything live testing has learned for this coin.
  // A double-click is one decision, not two.
  if (event.detail > 1 || (forgetArmedMs && now - forgetArmedMs < 600)) return;
  if (now - forgetArmedMs > 4000) { forgetArmedMs = now; button.textContent = 'Press again to forget'; setTimeout(() => { if (Date.now() - forgetArmedMs >= 4000) button.textContent = 'Forget results'; }, 4100); return; }
  forgetArmedMs = 0; button.textContent = 'Forget results';
  experiments.clear(); assignments = { ...DEFAULT_ASSIGNMENTS }; slotLocks = {}; tuneLog = [];
  view = null; barsVersion++; void saveExperiments(); drawExperiments(); queueDraw();
});
try {
  const stored = (await chrome.storage.local.get(STORAGE))[STORAGE];
  if (stored && typeof stored === 'object') {
    settings = { mode: ['alert', 'close'].includes(stored.mode) ? stored.mode : 'alert', unit: ['bp', 'price'].includes(stored.unit) ? stored.unit : 'bp',
      takeProfit: typeof stored.takeProfit === 'string' ? stored.takeProfit.slice(0, 24) : '', stopLoss: typeof stored.stopLoss === 'string' ? stored.stopLoss.slice(0, 24) : '' };
  }
} catch { /* defaults: alert only */ }
document.querySelector(`input[name="guard-mode"][value="${settings.mode}"]`).checked = true;
$('guard-unit').value = settings.unit;
$('guard-tp').value = settings.takeProfit; $('guard-sl').value = settings.stopLoss;

$('guard-arm').addEventListener('click', arm);
$('guard-disarm').addEventListener('click', event => { if (event.isTrusted && guard.disarm('user', Date.now())) { void record(guard.snapshot()); drawGuard(); } });
$('guard-show').addEventListener('click', () => void send('showJupiter'));
$('guard-position').addEventListener('change', () => { drawPositions(); drawGuard(); });
for (const id of ['guard-tp', 'guard-sl']) $(id).addEventListener('input', () => { $('guard-errors').textContent = ''; saveSettings(); drawGuard(); });
for (const input of document.querySelectorAll('input[name="guard-mode"], input[name="entry-size"], input[name="entry-leverage"], #entry-unlock, #entry-confirm, #guard-unit')) {
  input.addEventListener('change', () => {
    // A number typed as a price must not be re-read as a distance, or the reverse.
    if (input.id === 'guard-unit') { $('guard-tp').value = ''; $('guard-sl').value = ''; }
    entry.reset(); saveSettings(); drawGuard();
  });
}
for (const side of ['long', 'short']) $(`entry-${side}`).addEventListener('click', pressSide);
for (const button of document.querySelectorAll('.chips button')) button.addEventListener('click', () => fillLevel(button));
// Closing the window ends the guard, so ask first while one is live.
window.addEventListener('beforeunload', event => {
  // An entry that is out would open with nothing watching it if this window went away.
  if (LIVE_STATES.includes(guard.snapshot().state) || entry.pending || opening) { event.preventDefault(); event.returnValue = ''; }
});
window.addEventListener('resize', drawRibbon);
window.addEventListener('pagehide', () => { void saveExperiments(); disposed = true; clearInterval(timer); releaseLock?.(); feed?.stop(); chart.remove(); }, { once: true });

const timer = setInterval(() => { tick(); queueDraw(); }, 250);

linked = (await send('status'))?.attached === true;
// The guard and the entry buttons need the 1000x page bridge; a Perps view never gets one.
attached = linked && !VIEW_ONLY;
if (VIEW_ONLY) {
  $('guard').dataset.venue = 'perps';
  $('guard-title').firstChild.textContent = 'Perps page ';
  $('perps-note').hidden = false;
  // Jupiter's own take profit and stop loss exist only on the JLP markets; the page says so itself on the beta ones.
  const venue = Object.hasOwn(PERPS_MARKETS, SYMBOL) ? PERPS_MARKETS[SYMBOL].venue : null;
  $('perps-note').textContent = 'Read-outs only. On the Jupiter Perps page this window presses nothing: it does not open or close a position there and runs no take profit or stop loss. Use the page’s own order form. '
    + (venue === 'GUM' ? `Jupiter’s own take profit and stop loss are NOT offered on ${SYMBOL}: the page’s positions list shows “Take Profit / Stop Loss is not available for ${SYMBOL}”. The venue takes market, limit and post-only orders only, so nothing on the page acts as a stop loss. A position there is protected only by what you do yourself.`
      : venue === 'JLP' ? `On ${SYMBOL} the page’s positions list has its own Add TP / SL, which Jupiter runs without this window (seen in the page’s code; not exercised).`
        : 'Check on the page whether its positions list offers Add TP / SL for this market.');
  $('market').textContent = '1s scalp · Perps view';
  $('guard-page').textContent = `Opened from the Jupiter Perps page for ${SYMBOL || 'no market'}.`;
}
drawPositions(); draw();
if (SYMBOL_OK) {
  await startFeed();
} else {
  $('feed').textContent = 'Open this window from the “1s scalp” button on a Jupiter 1000x market.'; $('feed').dataset.state = 'error';
}
