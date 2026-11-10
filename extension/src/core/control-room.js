/** Availability only: the managed suite owns processes and the control room owns stage decisions. */
import { soltuiSuite } from './soltui.js';

const STATES = new Set(['up', 'degraded', 'down', 'unknown']);
const COMPONENTS = ['suite', 'manager', 'control_room', 'market_data'];
const COMPONENT_LABELS = { suite: 'Managed suite', manager: 'Bot Manager', control_room: 'Control room', market_data: 'Market data' };
export const CONTROL_ROOM_ALERT_COOLDOWN_MS = 5 * 60_000;

/** Unknown measurements never become failure alerts. Remember only four fixed components. */
export function controlRoomTransitions(snapshot, previous, now) {
  const saved = previous?.schema_version === 1 ? previous.components ?? {} : {};
  const components = {};
  const alerts = [];
  for (const name of COMPONENTS) {
    const old = saved[name] ?? {};
    const current = snapshot.helper === 'available' ? snapshot.components?.find(item => item.name === name)?.state : 'unknown';
    if (!['up', 'down', 'degraded'].includes(current)) { components[name] = old; continue; }
    const row = { state: current, seen_up: old.seen_up === true || current === 'up',
      active: old.active === true, last_notified_at: Number.isFinite(old.last_notified_at) ? old.last_notified_at : null };
    if (current === 'up' && old.active === true) {
      alerts.push({ id: `control-room:${name}`, kind: 'availability', severity: 'info',
        title: `${COMPONENT_LABELS[name]} recovered. Open the control room for current health.` });
      row.active = false;
    } else if (current !== 'up' && row.seen_up && old.state !== current
        && (row.last_notified_at === null || now - row.last_notified_at >= CONTROL_ROOM_ALERT_COOLDOWN_MS)) {
      alerts.push({ id: `control-room:${name}`, kind: 'availability', severity: 'review',
        title: `${COMPONENT_LABELS[name]} is ${current}. Open the control room to inspect the component.` });
      row.active = true;
      row.last_notified_at = now;
    }
    components[name] = row;
  }
  return { state: { schema_version: 1, components }, alerts };
}

export function controlRoomUrl(value) {
  if (typeof value !== 'string') return null;
  const match = /^http:\/\/127\.0\.0\.1:([1-9][0-9]{0,4})\/?$/.exec(value);
  return match && match[0] === value && Number(match[1]) <= 65535 ? `http://127.0.0.1:${match[1]}` : null;
}

export async function controlRoomSnapshot(deps, action = 'status') {
  const envelope = await soltuiSuite(deps, action);
  const absent = (helper, reason) => ({ schema_version: 1, helper, state: 'unknown', ready: null,
    ui_url: null, components: [], reason, opened: false });
  if (!envelope.ok) {
    if (envelope.error?.code === 'busy') return { ...absent('available', 'starting'), state: 'starting' };
    return ['unknown_command', 'incompatible_helper'].includes(envelope.error?.code)
      ? absent('incompatible', 'helper_incompatible') : absent('unavailable', 'helper_unavailable');
  }
  const result = envelope.result;
  if (result?.schema_version !== 1 || result.capability !== 'control-room-v1'
      || !result.status || result.health?.schema_version !== 1) return absent('incompatible', 'helper_incompatible');
  const health = result.health;
  const source = Array.isArray(health.components) ? health.components : Object.entries(health.components ?? {})
    .map(([name, value]) => ({ name, ...value }));
  const components = COMPONENTS.map(name => {
    const item = source.find(value => (value.name ?? value.id ?? value.component) === name);
    return { name, state: STATES.has(item?.state) ? item.state : 'unknown' };
  });
  const starting = ['starting', 'pending'].includes(result.status.state);
  return { schema_version: 1, helper: 'available', state: starting ? 'starting'
    : STATES.has(health.overall) ? health.overall : 'unknown',
  ready: typeof health.ready === 'boolean' ? health.ready : null,
  ui_url: controlRoomUrl(result.status.ui_url), components,
  reason: starting ? 'starting' : null, opened: false };
}

/** A click may start the fixed local suite. Polls and page loads never do. */
export async function openControlRoom(deps) {
  let snapshot = await controlRoomSnapshot(deps);
  if (snapshot.helper === 'available' && !snapshot.ui_url && snapshot.state !== 'starting') {
    snapshot = await controlRoomSnapshot(deps, 'start');
  }
  if (snapshot.ui_url && typeof deps.openControlRoom === 'function') {
    await deps.openControlRoom(snapshot.ui_url);
    return { ...snapshot, opened: true };
  }
  return snapshot;
}
