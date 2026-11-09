import { aggregatePredictions } from './live-score.js';
import { el } from './ui-kit.js';

export function hasCurrentPrediction(snapshot, now = Date.now() / 1000) {
  return (snapshot?.rows ?? []).some((row) => {
    return [1, 5, 10, 30].some((h) =>
      ['UP', 'DOWN', 'FLAT'].includes(row?.[`pred_${h}m`]) &&
      Number.isFinite(row[`issued_${h}m`]) && Number.isFinite(row[`expires_${h}m`]) &&
      row[`issued_${h}m`] <= now && now < row[`expires_${h}m`]);
  });
}

/** Recovery is an explicit paper-only command, separate from snapshot reads. */
export function predictionRecovery({ ask, supports = () => true, changed = () => {}, clock = Date.now }) {
  const pending = new Map(), attempts = new Map();
  let asset = '', snapshot = null, disposed = false, generation = 0;
  let state = { state: 'checking', running: null, can_start: false, message: 'Checking prediction process…' };
  const needed = () => !aggregatePredictions(snapshot?.rows ?? [], clock() / 1000, snapshot?.voting).available;
  function emit(value = state) {
    state = value;
    if (!disposed) changed({ ...state, asset, needed: needed() });
  }
  async function command(name, params) {
    const result = await ask(name, params);
    if (!result?.ok) throw new Error(result?.error?.message ?? 'Prediction process unavailable');
    return result.result;
  }
  function recover(manual) {
    if (disposed) return Promise.resolve(null);
    const requestedAsset = asset, requestedGeneration = generation;
    if (pending.has(requestedAsset)) return pending.get(requestedAsset);
    const current = () => !disposed && asset === requestedAsset && generation === requestedGeneration;
    const operation = (async () => {
      try {
        if (!supports('forwardtest.health') || !supports('forwardtest.ensure')) {
          if (current()) emit({ state: 'unsupported', running: null, can_start: false,
            message: 'Reconnect to an updated prediction host.' });
          return null;
        }
        if (manual) {
          attempts.set(requestedAsset, clock());
          emit({ ...state, state: 'starting', can_start: false, message: 'Starting predictions…' });
          const result = await command('forwardtest.ensure', { asset: requestedAsset, manual: true });
          if (current()) emit(result);
          return result;
        }
        const health = await command('forwardtest.health', { asset: requestedAsset });
        if (!current()) return null;
        emit(health);
        const due = clock() - (attempts.get(requestedAsset) ?? -Infinity) >= 30_000;
        const automatic = needed() && !health.paused && !health.cooldown_seconds && due &&
          (!health.running || !hasCurrentPrediction(snapshot, clock() / 1000));
        if (!manual && !automatic) return health;
        if (health.can_start === false && !health.running) return health;
        attempts.set(requestedAsset, clock());
        emit({ ...health, state: health.running ? 'running' : 'starting', can_start: false,
          message: health.running ? 'Requesting fresh predictions…' : 'Starting predictions…' });
        const result = await command('forwardtest.ensure', { asset: requestedAsset, manual });
        if (current()) emit(result);
        return result;
      } catch (error) {
        attempts.set(requestedAsset, clock());
        if (current()) emit({ state: 'failed', running: null, can_start: true,
          message: `Prediction recovery failed: ${error.message}`, last_error: error.message });
        return null;
      }
    })();
    pending.set(requestedAsset, operation);
    operation.finally(() => { if (pending.get(requestedAsset) === operation) pending.delete(requestedAsset); });
    return operation;
  }
  return {
    update(nextAsset, nextSnapshot) {
      if (disposed) return Promise.resolve(null);
      if (nextAsset !== asset) { asset = nextAsset; generation += 1; state = { state: 'checking', can_start: false, message: 'Checking prediction process…' }; }
      snapshot = nextSnapshot;
      emit();
      return needed() ? recover(false) : Promise.resolve(state);
    },
    start: () => recover(true),
    dispose() { disposed = true; generation += 1; },
  };
}

export function renderPredictionRecovery(target, state, { start, href = '#soltui/forward', newTab = false } = {}) {
  if (!target) return;
  target.hidden = !state.needed;
  if (!state.needed) return;
  const status = el('p', { class: 'note', role: 'status', text: state.message ?? 'Checking prediction process…' });
  const link = el('a', { href, text: 'Forward testing →' });
  if (newTab) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
  const actions = el('div', { class: 'row' }, link);
  if (state.can_start && !state.running && state.state !== 'starting') {
    const button = el('button', { class: 'small primary', text: 'Start predictions', onclick: start });
    button.type = 'button'; actions.append(button);
  }
  target.replaceChildren(status, actions);
}
