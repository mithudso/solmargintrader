/** The extension is a launcher and availability view for the same local control room. */
import { el } from './ui-kit.js';

const LABELS = { suite: 'Managed suite', manager: 'Bot Manager', control_room: 'Control room', market_data: 'Market data' };
export function controlRoomPresentation(snapshot) {
  if (snapshot?.helper === 'incompatible') return { title: 'Native helper update required', tone: 'unknown',
    detail: 'The installed helper does not support the managed suite. Update its local registration, then refresh.' };
  if (snapshot?.helper !== 'available') return { title: 'Native helper unavailable', tone: 'unknown',
    detail: 'Health is unknown. Install or repair the local native helper, then refresh.' };
  const options = {
    starting: ['Starting servers', 'starting', 'Startup is pending. Health refreshes do not start another server.'],
    up: ['Servers healthy', 'up', 'Open Bot Manager, Backtester, Oracle, bot stages and server logs.'],
    degraded: ['Servers need attention', 'degraded', 'Inspect component health and durable monitor alerts in the control room.'],
    down: ['Servers down', 'down', 'Start the configured managed suite to bring up the local servers.'],
    unknown: ['Health unknown', 'unknown', 'Refresh health or inspect the local managed-suite logs.'],
  };
  const [title, tone, detail] = options[snapshot.state] ?? options.unknown;
  return { title, tone, detail };
}

export function mountControlRoom(root = document.getElementById('controlRoom'), {
  send = message => chrome.runtime.sendMessage(message),
} = {}) {
  if (!root) return;
  const heading = el('h2', { text: 'Sol · Bot control room' });
  const state = el('span', { class: 'control-room-state', text: 'Checking health…', role: 'status' });
  const detail = el('p', { class: 'note', text: 'Reading local availability through the native helper.' });
  const address = el('code', { class: 'control-room-address', hidden: true });
  const components = el('div', { class: 'control-room-components', 'aria-label': 'Component health' });
  const readiness = el('p', { class: 'note', text: 'Availability readiness: unknown' });
  const feedback = el('p', { class: 'note', role: 'status' });
  const open = el('button', { id: 'controlRoomOpen', class: 'primary', text: 'Open control room', disabled: true });
  const start = el('button', { id: 'controlRoomStart', text: 'Start servers', disabled: true });
  const refresh = el('button', { id: 'controlRoomRefresh', text: 'Refresh health' });
  root.replaceChildren(el('div', { class: 'control-room-heading' }, heading, state), detail, address,
    components, readiness, el('div', { class: 'control-room-actions' }, open, start, refresh), feedback,
    el('p', { class: 'control-room-workflow', text: 'Configure → Backtest → Forward paper → Review readiness' }),
    el('p', { class: 'note', text: 'Each bot’s current stage and trading gates appear in the control room. Server startup preserves those gates.' }));
  let busy = false, timer, attempts = 0, closed = false;
  function paint(snapshot) {
    const copy = controlRoomPresentation(snapshot);
    state.textContent = copy.title;
    root.dataset.state = copy.tone;
    detail.textContent = copy.detail;
    address.textContent = snapshot.ui_url ?? '';
    address.hidden = !snapshot.ui_url;
    readiness.textContent = `Availability readiness: ${snapshot.ready === true ? 'ready' : snapshot.ready === false ? 'not ready' : 'unknown'}`;
    components.replaceChildren(...Object.entries(LABELS).map(([name, label]) => {
      const health = snapshot.components?.find(item => item.name === name)?.state ?? 'unknown';
      return el('span', { class: 'control-room-component', dataset: { state: health } },
        el('strong', { text: label }), el('span', { text: health }));
    }));
    open.disabled = busy || snapshot.helper !== 'available';
    start.disabled = busy || snapshot.helper !== 'available' || snapshot.state === 'starting';
    refresh.disabled = busy;
    if (snapshot.state === 'starting' && attempts < 5 && !closed) {
      const delay = Math.min(1000 * 2 ** attempts++, 10000);
      timer = setTimeout(() => run('controlRoomStatus'), delay);
    }
  }
  async function run(command) {
    if (busy || closed) return;
    clearTimeout(timer);
    busy = true;
    open.disabled = start.disabled = refresh.disabled = true;
    feedback.textContent = command === 'controlRoomStart' || command === 'controlRoomOpen' ? 'Contacting the local managed suite…' : '';
    let snapshot;
    try {
      const response = await send({ type: command });
      if (!response?.ok) throw new Error('availability request failed');
      snapshot = response.result;
      if (!snapshot || typeof snapshot !== 'object') throw new Error('invalid availability response');
      if (command === 'controlRoomOpen' && snapshot.opened) feedback.textContent = 'Control room opened in a new tab.';
      else if (command === 'controlRoomOpen' && snapshot.state === 'starting') feedback.textContent = 'Servers are starting. Click Open control room when its verified address appears.';
      else if (command === 'controlRoomStart') feedback.textContent = snapshot.ui_url ? 'Servers answered. Open the control room to inspect bot stages.' : 'Startup requested. Check component health for the result.';
    } catch {
      snapshot = { helper: 'unavailable', state: 'unknown', ready: null, components: [], ui_url: null };
      feedback.textContent = 'The helper did not answer. Refresh to retry this read.';
    } finally {
      busy = false;
      if (!closed) paint(snapshot);
    }
  }
  open.addEventListener('click', () => { attempts = 0; run('controlRoomOpen'); });
  start.addEventListener('click', () => { attempts = 0; run('controlRoomStart'); });
  refresh.addEventListener('click', () => { attempts = 0; run('controlRoomStatus'); });
  globalThis.addEventListener?.('pagehide', () => { closed = true; clearTimeout(timer); }, { once: true });
  run('controlRoomStatus');
}
