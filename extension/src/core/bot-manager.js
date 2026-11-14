/** Durable browser-owner protocol helpers; public actions live in commands.js. */
export const MANAGER_KEY = 'browserManager';
export const MANAGER_PROTOCOL = 1;
const CONTROL_KEYS = ['schema_version', 'request_id', 'installation_id', 'native_id', 'operation', 'expected_generation', 'expected_config_hash', 'expected_config_revision', 'expected_runtime_id', 'sequence', 'expires_at'];
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const SHA = /^[0-9a-f]{64}$/;
const terminal = new Set(['acknowledged', 'failed', 'skipped', 'unknown']);

export async function digest(value) {
  const bytes = new TextEncoder().encode(value);
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2, '0')).join('');
}
function stable(value) {
  if (!value || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
}

export async function managerSnapshot(deps, { initialize = false } = {}) {
  const config = await deps.configStore.getConfig();
  const runtime = await deps.configStore.getRuntime();
  let state = await deps.configStore.get(MANAGER_KEY, null);
  if (!state && !initialize) return null;
  const source = typeof deps.loadedSourceHash === 'function' ? await deps.loadedSourceHash({ revoke: initialize }) : deps.loadedSourceHash;
  if (!SHA.test(source ?? '')) throw new Error('loaded browser source identity unavailable');
  if (!state) {
    state = { schema_version: 1, installation_id: crypto.randomUUID(), generation: 0, config_revision: 1,
      config_hash: await digest(stable(config)), source_hash: source, extension_version: deps.extensionVersion, running: false, runtime_id: null, requests: {}, last_sequence: 0 };
    await deps.configStore.set(MANAGER_KEY, state);
  }
  if (!UUID.test(state.installation_id) || state.schema_version !== 1) throw new Error('browser identity integrity failed');
  const hash = await digest(stable(config));
  // Reads report the loaded settings but never initialize or rewrite identity.
  if (initialize && (state.source_hash !== source || state.extension_version !== deps.extensionVersion || state.config_hash !== hash || (state.running && (config.mode !== 'dry-run' || runtime.armed || runtime.killSwitch)))) {
    state = { ...state, running: false, generation: state.generation + 1,
      config_revision: state.config_revision + (state.config_hash !== hash ? 1 : 0), config_hash: hash,
      source_hash: source, extension_version: deps.extensionVersion };
    await deps.configStore.set(MANAGER_KEY, state);
  }
  return { installation_id: state.installation_id, native_id: 'grid', generation: state.generation,
    config_revision: state.config_revision, config_hash: hash, runtime_id: state.runtime_id,
    running: state.running && state.source_hash === source && state.extension_version === deps.extensionVersion && state.config_hash === hash && config.mode === 'dry-run' && runtime.armed === false && runtime.killSwitch !== true,
    mode: config.mode, armed: runtime.armed === true, kill_switch: runtime.killSwitch === true,
    extension_version: deps.extensionVersion, source_hash: source };
}

function validateControl(control, state) {
  if (!control || typeof control !== 'object' || Array.isArray(control)
      || Object.keys(control).length !== CONTROL_KEYS.length || CONTROL_KEYS.some(key => !Object.hasOwn(control, key))
      || control.schema_version !== 1 || !UUID.test(control.request_id) || control.installation_id !== state.installation_id
      || control.native_id !== 'grid' || !['start', 'stop'].includes(control.operation)
      || !Number.isSafeInteger(control.expected_config_revision) || control.expected_config_revision < 1
      || !Number.isSafeInteger(control.expected_generation) || control.expected_generation < 0 || !SHA.test(control.expected_config_hash)
      || !(control.expected_runtime_id === null || UUID.test(control.expected_runtime_id))
      || !Number.isSafeInteger(control.sequence) || control.sequence <= 0
      || !Number.isFinite(control.expires_at) || control.expires_at <= 0) throw new Error('invalid owner control');
}
function receipt(control, state, outcome, reason) {
  return { request_id: control.request_id, outcome, reason, generation: state.generation,
    runtime_id: state.runtime_id, config_hash: control.expected_config_hash };
}

export async function applyManagerControl(deps, control) {
  let state = await deps.configStore.get(MANAGER_KEY, null);
  validateControl(control, state);
  const binding = stable(control);
  if (state.requests[control.request_id]) {
    const old = state.requests[control.request_id];
    if (old.binding !== binding) throw new Error('owner request binding conflict');
    return old.receipt;
  }
  // Delivered historical receipts may be compacted only behind the durable
  // sequence fence. Keep unresolved outcomes and the receipt binding the active
  // grant, which a previously fetched stop may still need to match.
  const retained = Object.entries(state.requests).filter(([, item]) => item.delivered && !item.prepared
    && terminal.has(item.receipt.outcome) && item.request.sequence <= state.last_sequence
    && !(state.running && item.request.operation === 'start' && item.receipt.outcome === 'acknowledged'
      && item.receipt.generation === state.generation && item.receipt.runtime_id === state.runtime_id))
    .sort((a, b) => b[1].request.sequence - a[1].request.sequence);
  if (retained.length > 256) {
    const requests = { ...state.requests };
    for (const [id] of retained.slice(256)) delete requests[id];
    state = { ...state, requests };
  }
  if (Object.keys(state.requests).length >= 10000) throw new Error('browser owner receipt capacity exhausted');
  const snapshot = await managerSnapshot(deps);
  let outcome = 'acknowledged';
  let reason = control.operation === 'start' ? 'paper_started' : 'paper_stopped';
  if (Date.now() / 1000 > control.expires_at) { outcome = 'failed'; reason = 'browser_owner_expired'; }
  else if (control.sequence <= state.last_sequence) { outcome = 'skipped'; reason = 'revoked_by_later_stop'; }
  else if ((control.expected_generation !== state.generation || control.expected_runtime_id !== state.runtime_id)
      && !(control.operation === 'stop' && Object.values(state.requests).some(item => item.request.operation === 'start'
        && item.request.sequence < control.sequence && item.request.expected_generation === control.expected_generation
        && item.receipt.outcome === 'acknowledged' && item.receipt.generation === state.generation
        && item.receipt.runtime_id === state.runtime_id))
      || control.expected_config_hash !== snapshot.config_hash || control.expected_config_revision !== snapshot.config_revision) { outcome = 'failed'; reason = 'browser_owner_context_changed'; }
  else if (snapshot.mode !== 'dry-run' || snapshot.armed || (control.operation === 'start' && snapshot.kill_switch)) {
    outcome = 'failed'; reason = 'browser_paper_slot_unavailable';
  } else if (state.running === (control.operation === 'start')) {
    outcome = 'skipped'; reason = state.running ? 'already_running' : 'already_stopped';
  }
  // Write-ahead context lands before an owner action. A restart never retries a
  // prepared action: it reports unknown and requires explicit reconciliation.
  const prepared = { binding, request: control, receipt: receipt(control, state, 'unknown', 'outcome_unknown'), prepared: true, delivered: false };
  state = { ...state, requests: { ...state.requests, [control.request_id]: prepared } };
  await deps.configStore.set(MANAGER_KEY, state);
  if (outcome === 'acknowledged') {
    state = { ...state, running: control.operation === 'start', generation: state.generation + 1,
      runtime_id: control.operation === 'start' ? crypto.randomUUID() : state.runtime_id };
  }
  // A validated stop revokes older fetched starts even when execution is
  // already stopped. Refused controls and receipt replays never gain a fence.
  const revokesEarlierStarts = control.operation === 'stop' && reason === 'already_stopped';
  if (outcome === 'acknowledged' || revokesEarlierStarts) state.last_sequence = Math.max(state.last_sequence, control.sequence);
  const result = receipt(control, state, outcome, reason);
  state.requests[control.request_id] = { ...prepared, receipt: result, prepared: false };
  await deps.configStore.set(MANAGER_KEY, state);
  return result;
}

export async function managerPoll(deps) {
  await managerSnapshot(deps, { initialize: true });
  let state = await deps.configStore.get(MANAGER_KEY, null);
  for (const item of Object.values(state.requests)) {
    if (item.prepared) { item.prepared = false; item.receipt.outcome = 'unknown'; item.receipt.reason = 'outcome_unknown'; }
  }
  await deps.configStore.set(MANAGER_KEY, state);
  const pending = Object.values(state.requests).filter(item => !item.delivered).slice(0, 128).map(item => item.receipt);
  const envelope = await deps.soltui.request({ op: 'browserManager', message: { schema_version: 1,
    snapshot: await managerSnapshot(deps), receipts: pending } }, { timeoutMs: 3000 });
  const result = envelope?.result;
  if (envelope?.ok !== true || !result || Object.keys(result).sort().join(',') !== 'acknowledged,controls,origin,schema_version,transfer'
      || result.schema_version !== 1 || !Array.isArray(result.controls) || result.controls.length > 32
      || !Array.isArray(result.acknowledged) || result.acknowledged.length > 128
      || !/^chrome-extension:\/\/[a-p]{32}$/.test(result.origin)) throw new Error('browser native registration unavailable');
  state = await deps.configStore.get(MANAGER_KEY, null);
  for (const id of result.acknowledged) {
    if (!state.requests[id] || !terminal.has(state.requests[id].receipt.outcome)) throw new Error('invalid native receipt acknowledgment');
    state.requests[id].delivered = true;
  }
  await deps.configStore.set(MANAGER_KEY, state);
  for (const control of result.controls) await applyManagerControl(deps, control);
  return { available: true, native_origin: result.origin, controls: result.controls.length,
    snapshot: await managerSnapshot(deps), transfer: { available: false, reason: 'owner_prepare_quiesce_snapshot_commit_unavailable' } };
}

/** Explicit paper grant cannot authorize any live venue or persist an armed flag. */
export function paperConfigStore(configStore, verifySource = async () => {}) {
  async function permissionSnapshot() {
    await verifySource();
    const runtime = await configStore.getRuntime();
    const config = await configStore.getConfig();
    const state = await configStore.get(MANAGER_KEY, null);
    const allowed = config.mode === 'dry-run' && state?.running === true
      && state.config_hash === await digest(stable(config)) && runtime.armed === false && !runtime.killSwitch;
    return { runtime, allowed };
  }
  return {
    get: (...args) => configStore.get(...args),
    set: (...args) => configStore.set(...args),
    getConfig: () => configStore.getConfig(),
    async getRuntime() {
      const { runtime, allowed } = await permissionSnapshot();
      return { ...runtime, armed: runtime.armed === true || allowed };
    },
    async withExecutionPermission(invoke, permitted) {
      const { runtime, allowed } = await permissionSnapshot();
      if (typeof configStore.withExecutionPermission !== 'function') throw new Error('atomic execution permission is unavailable');
      // Snapshot reads may yield. The underlying gate rechecks the current
      // stop epoch and kill latch after those reads, for every venue mode.
      return configStore.withExecutionPermission(invoke, permitted,
        { paperGrant: allowed, expectedStopGeneration: runtime.stopGeneration });
    },
    setRuntime: patch => configStore.setRuntime(Object.fromEntries(Object.entries(patch).filter(([key]) => key !== 'armed'))),
  };
}
