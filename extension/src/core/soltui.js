/**
 * The soltui bridge, transport-free.
 *
 * soltui (Python) owns its own command registry and answers every call with one
 * JSON envelope:
 *
 *   {"ok": true,  "command": "x.y", "result": <json>, "error": null}
 *   {"ok": false, "command": "x.y", "result": null, "error": {"code", "message"}}
 *
 * This module forwards a call to an injected transport and hands that envelope
 * back UNCHANGED, so the extension, the extension's node CLI and its HTTP API
 * return byte-for-byte what `soltui call` prints. It adds no fields, no timing
 * and no request id.
 *
 * The transport is `deps.soltui`:
 *
 *   request({ op, command?, params? }, { timeoutMs }) => Promise<envelope>
 *
 * It owns the request id, the framing and the process or port. It resolves with
 * the host's envelope and REJECTS with a SoltuiTransportError when the host is
 * missing, dies, answers out of protocol, or does not answer in time. This file
 * turns every such rejection into an envelope with the same shape, so a missing
 * host is a normal, clean result on every surface and never an exception.
 *
 * Nothing here reaches chrome.* or node:*. It never decides what soltui may do:
 * access control (requires_confirm, kill switches) lives in soltui and holds on
 * every surface. The confirm flag is an ordinary entry in `params`, forwarded
 * untouched.
 */

/** Error codes soltui itself uses. The bridge adds nothing outside this set. */
export const SOLTUI_ERROR = Object.freeze({
  BAD_PARAMS: 'bad_params',
  UNKNOWN_COMMAND: 'unknown_command',
  FORBIDDEN: 'forbidden',
  FAILED: 'failed',
  TIMEOUT: 'timeout',
});

export const SOLTUI_HOST_NAME = 'com.mitchhudson.soltui';

/** A quick call gets a short deadline; a command flagged long_running gets a long one. */
export const SOLTUI_TIMEOUT_MS = Object.freeze({ quick: 30_000, long: 15 * 60_000, probe: 10_000 });

// soltui command names are dotted lowercase words, for example backtest.run.
// Anything else is refused here, before it reaches a process boundary.
const COMMAND_NAME = /^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$/;

export class SoltuiTransportError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'SoltuiTransportError';
    this.code = code;
  }
}

export const failedEnvelope = (command, code, message) => ({
  ok: false,
  command,
  result: null,
  error: { code, message },
});

/** True for an object shaped like a soltui envelope. */
export function isEnvelope(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && typeof value.ok === 'boolean' && typeof value.command === 'string'
    && 'result' in value && 'error' in value;
}

async function ask(deps, request, timeoutMs) {
  const label = request.op === 'call' ? request.command : request.op;
  if (!deps.soltui || typeof deps.soltui.request !== 'function') {
    return failedEnvelope(label, SOLTUI_ERROR.FAILED, 'soltui transport is not configured on this surface');
  }
  try {
    const envelope = await deps.soltui.request(request, { timeoutMs });
    if (!isEnvelope(envelope)) {
      return failedEnvelope(label, SOLTUI_ERROR.FAILED, 'soltui host answered with something that is not an envelope');
    }
    return envelope;
  } catch (err) {
    // The message of a SoltuiTransportError is written by the transport and
    // names the host and the fix. Any other exception could carry arbitrary
    // text, so it is reduced to a fixed sentence.
    if (err instanceof SoltuiTransportError) return failedEnvelope(label, err.code, err.message);
    return failedEnvelope(label, SOLTUI_ERROR.FAILED, 'soltui transport failed');
  }
}

/** The soltui command list, as soltui's own `list` envelope. */
export function soltuiList(deps, { timeoutMs = SOLTUI_TIMEOUT_MS.quick } = {}) {
  return ask(deps, { op: 'list' }, timeoutMs);
}

// Which commands are long_running, cached per transport. Looking it up costs a
// host round trip, so it is paid at most once per TTL, and a failed lookup just
// means the quick deadline applies.
const META_TTL_MS = 60_000;
const metaCache = new WeakMap();

async function isLongRunning(deps, command) {
  const now = (deps.clock ?? Date.now)();
  let entry = metaCache.get(deps.soltui);
  if (!entry || now - entry.at > META_TTL_MS) {
    const listing = await soltuiList(deps, { timeoutMs: SOLTUI_TIMEOUT_MS.probe });
    if (!listing.ok || !Array.isArray(listing.result)) return false;
    entry = { at: now, long: new Set(listing.result.filter((c) => c?.long_running === true).map((c) => c.name)) };
    metaCache.set(deps.soltui, entry);
  }
  return entry.long.has(command);
}

/** Run one soltui command. `params` is forwarded exactly as given. */
export async function soltuiCall(deps, { command, params = {}, timeoutMs } = {}) {
  if (typeof command !== 'string' || !COMMAND_NAME.test(command)) {
    return failedEnvelope(String(command ?? ''), SOLTUI_ERROR.BAD_PARAMS,
      'command must be a soltui registry name such as backtest.run; see soltuiCommands');
  }
  let deadline = timeoutMs;
  if (deadline === undefined) {
    const long = deps.soltui && typeof deps.soltui.request === 'function' && await isLongRunning(deps, command);
    deadline = long ? SOLTUI_TIMEOUT_MS.long : SOLTUI_TIMEOUT_MS.quick;
  }
  return ask(deps, { op: 'call', command, params }, deadline);
}

/** Ask the host for the hash of the extension directory it serves. */
export function soltuiBuildHash(deps) {
  return ask(deps, { op: 'buildHash' }, SOLTUI_TIMEOUT_MS.probe);
}
