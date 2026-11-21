import { el, soltui } from '../ui/ui-kit.js';

const POLL_MS = 5000;
const MAX_AGE_SECONDS = 60;
const MAX_MARK_AGE_SECONDS = 20;
const WINDOW_SECONDS = 300;
const LEARNING_HEARTBEAT_SECONDS = 20;
const PERFORMANCE_MAX_AGE_SECONDS = 180;
const OWNER_STATES = Object.freeze({
  watching: 'Watching for signals', armed: 'Armed', paused: 'Entries paused',
  'data-unavailable': 'Waiting for fresh GUM data', checking: 'Reconciling with GUM',
  blocked: 'Blocked', stopped: 'Owner stopped',
});
const ORDER_STATES = Object.freeze({
  submitting: 'Submission in progress', acknowledged: 'Acknowledged', pending: 'Pending', filled: 'Confirmed fill',
  cancelled: 'Cancelled', refused: 'Refused', unknown: 'Outcome unknown',
});
const STATE_NOTES = Object.freeze({
  armed: 'Waiting for a fresh breakout crossing.',
  watching: 'Watching for Volty crossings in observe mode.',
  paused: 'New submissions are paused. The host can still reconcile outstanding orders.',
  checking: 'Reconciling the current signal with GUM.',
  blocked: 'Execution checks blocked new orders. See signal history and order receipts.',
  'data-unavailable': 'The bot is waiting for a fresh GUM mark and completed candles.',
  stopped: 'The local Volty process has stopped.',
});
const OUTCOMES = Object.freeze({
  already_held: 'Skipped · already holding this side',
  cancelled: 'Order cancelled',
  complete: 'Execution complete',
  evaluating: 'Evaluating',
  expired: 'Signal expired',
  owner_preflight_refused: 'Skipped · account or venue check failed',
  pending: 'Waiting for GUM',
  preceding_order_unresolved: 'Skipped · prior order unresolved',
  refused: 'Order refused',
  unknown: 'Order outcome unverified',
});

const stamp = seconds => new Date(seconds * 1000).toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
const direction = side => side === 'buy' ? 'Long' : 'Short';
const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 });
const pnl = new Intl.NumberFormat('en-US', { signDisplay: 'exceptZero', minimumFractionDigits: 2, maximumFractionDigits: 6 });
const percent = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 });
const count = new Intl.NumberFormat('en-US');
const eventLabel = event => `${direction(event.side)} · ${OUTCOMES[event.outcome] ?? 'Observed'}`;
const orderAction = ({ leg, side }) => leg === 'open'
  ? `Open ${direction(side).toLowerCase()}`
  : `Close ${direction(side === 'buy' ? 'sell' : 'buy').toLowerCase()}`;
const setText = (node, value) => {
  if (node.textContent !== value) node.textContent = value;
};

function verifiedPerformance(performance, now) {
  const { updated_at: updated, gross_pnl_usdc: gross, net_pnl_usdc: net,
    closed_trades: closed, profitable_trades: profitable } = performance ?? {};
  return Number.isFinite(updated) && updated > 0 && updated <= now + 5
    && Number.isFinite(gross) && Number.isFinite(net)
    && Number.isSafeInteger(closed) && Number.isSafeInteger(profitable)
    && profitable >= 0 && profitable <= closed
    && (closed > 0 || (gross === 0 && net === 0)) ? performance : null;
}

function setPnl(node, amount) {
  setText(node, amount === undefined ? '—' : `${pnl.format(amount)} USDC`);
  node.toggleAttribute('data-profit', amount > 0);
  node.toggleAttribute('data-loss', amount < 0);
}

function orderRow(order) {
  const verified = order.fills.length && order.state !== 'filled' ? ' · Venue fill transactions recorded' : '';
  const status = order.settlement_pending ? 'Filled · awaiting collateral settlement'
    : (ORDER_STATES[order.state] ?? 'Unverified') + verified;
  const quantities = `Requested ${order.requested_quantity} ZEC · ${order.filled_quantity === null ? 'filled size unverified' : `filled ${order.filled_quantity} ZEC`}`;
  const orderId = order.order_id === null ? 'Venue ID unavailable' : `GUM order ${order.order_id}`;
  const fills = order.fills.map(fill => el('li', {
    text: `${fill.size} ZEC at $${fill.price} · fee $${fill.fee} · ${stamp(fill.timestamp)} · transaction ${fill.signature}`,
  }));
  return el('li', { class: 'volty-order' },
    el('strong', { text: `${orderAction(order)} · ${status}` }),
    el('p', { text: `${quantities} · ${orderId}` }),
    el('p', { class: 'muted', text: `${stamp(order.updated_at)} · client order ${order.client_order_id} · signal ${order.event_id}` }),
    fills.length ? el('ul', { 'aria-label': 'Confirmed fill transactions' }, ...fills) : null);
}

export function mountVoltyStatus(section, { call = soltui, clock = Date.now } = {}) {
  const status = section.querySelector('[data-volty-status]');
  const updated = section.querySelector('[data-volty-updated]');
  const stateNote = section.querySelector('[data-volty-state-note]');
  const grossPnl = section.querySelector('[data-volty-gross]');
  const netPnl = section.querySelector('[data-volty-net]');
  const profitableTrades = section.querySelector('[data-volty-profitable]');
  const performanceNote = section.querySelector('[data-volty-performance-note]');
  const mark = section.querySelector('[data-volty-mark]');
  const upper = section.querySelector('[data-volty-upper]');
  const lower = section.querySelector('[data-volty-lower]');
  const marketNote = section.querySelector('[data-volty-market-note]');
  const signal = section.querySelector('[data-volty-signal]');
  const activityNote = section.querySelector('[data-volty-activity-note]');
  const activity = section.querySelector('[data-volty-activity]');
  const learning = section.querySelector('[data-volty-learning]');
  const horizons = section.querySelector('[data-volty-horizons]');
  const orderTitle = section.querySelector('[data-volty-orders-title]');
  const note = section.querySelector('[data-volty-orders-note]');
  const orders = section.querySelector('[data-volty-orders]');
  let current = null;
  let available = false;
  let closed = false;
  let busy = false;
  let renderedOrders = '';
  let renderedActivity = '';
  let renderedLearning = '';

  function render() {
    const now = clock() / 1000;
    const mode = current?.mode === 'live' ? 'Live' : 'Observe';
    const stale = current !== null && now - current.updated_at > MAX_AGE_SECONDS;
    const fresh = available && !stale;
    const recent = current?.orders ?? [];
    status.toggleAttribute('data-stale', !fresh);
    status.toggleAttribute('data-attention', ['blocked', 'data-unavailable'].includes(current?.state));
    const health = !available ? 'Local Volty status unavailable' : stale ? `${mode} · Status stale`
      : `${mode} · ${OWNER_STATES[current.state]}`;
    setText(status, health);
    setText(updated, current ? `Host reported ${stamp(current.updated_at)}` : 'Waiting for the local Volty host.');
    const settling = recent.some(order => order.settlement_pending === true);
    setText(stateNote, fresh
      ? current.state === 'checking' && settling ? 'Close filled. Waiting for collateral to settle back to the parent account.'
        : STATE_NOTES[current.state]
      : current ? 'Showing historical signals and order receipts.' : '');
    const performance = verifiedPerformance(current?.performance, now);
    setPnl(grossPnl, performance?.gross_pnl_usdc);
    setPnl(netPnl, performance?.net_pnl_usdc);
    const total = performance?.closed_trades;
    const wins = performance?.profitable_trades;
    setText(profitableTrades, performance
      ? `${count.format(wins)} of ${count.format(total)} (${total ? percent.format(wins / total) : '—'})` : '—');
    const oldPerformance = performance !== null && now - performance.updated_at > PERFORMANCE_MAX_AGE_SECONDS;
    performanceNote.toggleAttribute('data-stale', !available || oldPerformance);
    setText(performanceNote, performance
      ? `Closed trades as of ${stamp(performance.updated_at)} · Net includes fees and funding`
        + (oldPerformance ? ' · Performance stale' : '') + (available ? '' : ' · Local host unavailable')
      : available ? 'Closed-trade performance unavailable.' : 'Closed-trade performance unavailable · Local host unavailable');
    const telemetry = current?.telemetry;
    const learner = current?.learning;
    const learningStatus = !learner ? 'Unavailable'
      : !fresh || now - learner.updated_at > LEARNING_HEARTBEAT_SECONDS ? 'Historical'
        : ({ warming: 'Warming up', learning: 'Online', stale: 'Waiting for fresh ticks', waiting: 'Waiting for first tick',
          unavailable: 'Unavailable' }[learner.state] ?? 'Unavailable');
    const captureStatus = fresh && telemetry?.capture === 'unavailable' ? ' · Tick capture unavailable' : '';
    const counts = learner ? ` · ${learner.ticks.toLocaleString('en-US')} ticks` : '';
    setText(learning, `Tick learning · ${learningStatus}${counts}${captureStatus}`);
    const learningRows = learner?.horizons ?? [];
    const learningRevision = JSON.stringify(learningRows);
    if (learningRevision !== renderedLearning) {
      horizons.replaceChildren(...learningRows.map(h => el('li', { class: 'volty-activity' },
        el('strong', { text: `${h.seconds / 60}m · ${h.trained} trained · ${h.pending} pending` }),
        el('span', { class: 'muted', text: (h.candidate_brier === null ? ''
          : ` · Brier ${h.candidate_brier.toFixed(3)} vs ${h.frequency_brier.toFixed(3)} baseline`)
          + (h.expired ? ` · ${h.expired} expired` : '') + (h.capacity_drops ? ` · ${h.capacity_drops} at capacity` : '') }))));
      renderedLearning = learningRevision;
    }
    const market = telemetry?.market;
    const activeMarket = fresh && market && Number.isFinite(market.mark_at) && Number.isFinite(market.window_start)
      && now - market.mark_at <= MAX_MARK_AGE_SECONDS && now >= market.window_start && now < market.window_start + WINDOW_SECONDS;
    setText(mark, activeMarket ? usd.format(market.mark) : '—');
    setText(upper, activeMarket ? usd.format(market.upper) : '—');
    setText(lower, activeMarket ? usd.format(market.lower) : '—');
    setText(marketNote, activeMarket
      ? `Mark at ${stamp(market.mark_at)} · Window ends ${stamp(market.window_start + WINDOW_SECONDS)}`
      : telemetry && fresh ? 'Waiting for a current five-minute observation.' : 'Current trigger levels unavailable.');
    const events = Array.isArray(telemetry?.activity) ? telemetry.activity : [];
    const latest = current?.signal;
    const decision = events[0];
    // A new observe-mode crossing has no execution outcome in the live ledger.
    const showDecision = decision && (!latest || decision.at >= latest.at);
    setText(signal, showDecision ? `Last signal ${eventLabel(decision)} · ${stamp(decision.at)}`
      : latest ? `Last signal ${direction(latest.side)} · ${stamp(latest.at)} · mark ${usd.format(latest.mark)}`
        : 'No Volty signal reported.');
    setText(activityNote, events.length ? '' : telemetry?.activity ? 'No live decisions reported.' : 'Signal decisions unavailable.');
    const activityRevision = JSON.stringify(events);
    if (activityRevision !== renderedActivity) {
      activity.replaceChildren(...events.map(event => el('li', { class: 'volty-activity' },
        el('strong', { text: eventLabel(event) }),
        el('time', { class: 'muted', datetime: new Date(event.at * 1000).toISOString(), text: stamp(event.at) }),
        el('span', { class: 'muted', text: ` · ${usd.format(event.mark)}` }))));
      renderedActivity = activityRevision;
    }
    setText(orderTitle, `GUM order receipts (${recent.length})`);
    setText(note, current?.mode === 'observe'
      ? `Observe mode submits no orders.${recent.length ? ' Receipts below are from prior live runs.' : ''}`
      : recent.length ? '' : 'No GUM order receipts reported.');
    const revision = JSON.stringify(recent);
    if (revision !== renderedOrders) {
      orders.replaceChildren(...recent.map(orderRow));
      renderedOrders = revision;
    }
  }

  async function refresh() {
    if (closed || busy) return;
    busy = true;
    try {
      const next = await call('zec.volty.status');
      const seconds = clock() / 1000;
      available = next?.schema === 1 && ['live', 'observe'].includes(next.mode)
        && Object.hasOwn(OWNER_STATES, next.state) && Number.isFinite(next.updated_at)
        && next.updated_at > 0 && next.updated_at <= seconds + 5 && Array.isArray(next.orders);
      if (available) current = next;
    } catch {
      // Keep the last reported receipts visible if the native bridge drops.
      available = false;
    } finally {
      busy = false;
      if (!closed) render();
    }
  }

  section.hidden = false;
  const timer = setInterval(() => {
    render();
    void refresh();
  }, POLL_MS);
  void refresh();
  return { close() { closed = true; clearInterval(timer); } };
}
