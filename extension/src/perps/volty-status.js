import { el, soltui } from '../ui/ui-kit.js';

const POLL_MS = 5000;
const MAX_AGE_SECONDS = 60;
const OWNER_STATES = Object.freeze({
  watching: 'Watching for signals', armed: 'Armed', paused: 'Entries paused',
  'data-unavailable': 'Waiting for fresh GUM data', checking: 'Reconciling with GUM',
  blocked: 'Blocked', stopped: 'Owner stopped',
});
const ORDER_STATES = Object.freeze({
  submitting: 'Submission in progress', acknowledged: 'Acknowledged', pending: 'Pending', filled: 'Confirmed fill',
  cancelled: 'Cancelled', refused: 'Refused', unknown: 'Outcome unknown',
});

const stamp = seconds => new Date(seconds * 1000).toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
const direction = side => side === 'buy' ? 'Long' : 'Short';
const orderAction = ({ leg, side }) => leg === 'open'
  ? `Open ${direction(side).toLowerCase()}`
  : `Close ${direction(side === 'buy' ? 'sell' : 'buy').toLowerCase()}`;
const setText = (node, value) => {
  if (node.textContent !== value) node.textContent = value;
};

function orderRow(order) {
  const verified = order.fills.length && order.state !== 'filled' ? ' · Venue fill transactions recorded' : '';
  const status = (ORDER_STATES[order.state] ?? 'Unverified') + verified;
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
  const signal = section.querySelector('[data-volty-signal]');
  const note = section.querySelector('[data-volty-orders-note]');
  const orders = section.querySelector('[data-volty-orders]');
  let current = null;
  let available = false;
  let closed = false;
  let busy = false;
  let renderedOrders = '';

  function render() {
    const mode = current?.mode === 'live' ? 'Live' : 'Observe';
    const stale = current !== null && clock() / 1000 - current.updated_at > MAX_AGE_SECONDS;
    status.toggleAttribute('data-stale', !available || stale);
    const health = !available ? 'Local Volty status unavailable' : stale ? `${mode} · Status stale`
      : `${mode} · ${OWNER_STATES[current.state]}`;
    setText(status, health);
    setText(updated, current ? `Last report ${stamp(current.updated_at)}` : 'Start the local Volty owner to receive status.');
    const last = current?.signal;
    setText(signal, last
      ? `Last signal ${direction(last.side)} · ${stamp(last.at)} · mark $${last.mark} · bands $${last.lower} / $${last.upper} · ${last.event_id}`
      : 'No Volty signal reported.');
    const recent = current?.orders ?? [];
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
