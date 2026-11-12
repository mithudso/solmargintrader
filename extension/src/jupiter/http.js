/**
 * HTTP layer for the Jupiter APIs.
 *
 * A grid ticking every 30s across N rungs will hit rate limits on the free
 * tier, so retry/backoff and a per-tick request budget are part of the client
 * rather than something callers remember to add.
 */

export class JupiterHttpError extends Error {
  constructor(message, { status, body, url }) {
    super(message);
    this.name = 'JupiterHttpError';
    this.status = status;
    this.body = body;
    // Query strings can carry mints and wallet addresses; keep the path only.
    this.url = safePath(url);
  }
}

function safePath(url) {
  try {
    const u = new URL(url);
    return `${u.origin}${u.pathname}`;
  } catch {
    return 'invalid URL';
  }
}

const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

/** Token-bucket budget so a cold start cannot fire a burst of requests. */
export class RequestBudget {
  constructor({ maxPerWindow = 30, windowMs = 60_000 } = {}) {
    this.maxPerWindow = maxPerWindow;
    this.windowMs = windowMs;
    this.stamps = [];
  }

  /** @returns {boolean} true if a request may proceed now. */
  tryTake(nowMs = Date.now()) {
    this.stamps = this.stamps.filter((t) => nowMs - t < this.windowMs);
    if (this.stamps.length >= this.maxPerWindow) return false;
    this.stamps.push(nowMs);
    return true;
  }

  remaining(nowMs = Date.now()) {
    this.stamps = this.stamps.filter((t) => nowMs - t < this.windowMs);
    return Math.max(0, this.maxPerWindow - this.stamps.length);
  }
}

export function backoffDelayMs(attempt, { baseMs = 500, maxMs = 15_000, jitter = true } = {}) {
  const raw = Math.min(maxMs, baseMs * 2 ** attempt);
  // Full jitter: several rungs retrying in lockstep would otherwise re-collide.
  return jitter ? Math.random() * raw : raw;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function defaultRequestLog(event) {
  // stderr preserves JSON-only CLI stdout; Chrome has no process global.
  if (globalThis.process?.versions?.node) console.error(JSON.stringify(event));
  else console.debug(event);
}

/** A hung request must not outlive the tick that started it. */
export const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * @param {object} opts
 * @param {string} opts.url
 * @param {object} [opts.init]           fetch init
 * @param {RequestBudget} [opts.budget]
 * @param {number} [opts.maxAttempts]
 * @param {number} [opts.timeoutMs]      per-attempt timeout
 * @param {function} [opts.fetchImpl]    injectable for tests
 */
export async function request({
  url,
  init = {},
  budget,
  maxAttempts = 4,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  fetchImpl = globalThis.fetch,
  sleepImpl = sleep,
  log = defaultRequestLog,
}) {
  if (!Number.isSafeInteger(maxAttempts) || maxAttempts < 1 ||
      !Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    throw new RangeError('HTTP attempts and timeout must be positive finite values');
  }
  // A lost write response does not prove the server rejected the operation.
  // Only read requests can be replayed without creating a second order/deposit.
  const readOnly = ['GET', 'HEAD'].includes((init.method ?? 'GET').toUpperCase());
  const attempts = readOnly ? maxAttempts : 1;
  const method = (init.method ?? 'GET').toUpperCase();
  const context = { transport: 'jupiter-http', path: safePath(url),
    method: ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'].includes(method) ? method : 'OTHER' };
  const emit = (event) => {
    try { log({ ...context, ...event }); } catch { /* Diagnostic sinks cannot replay a write. */ }
  };
  let lastError;
  for (let attempt = 0; attempt < attempts; attempt++) {
    if (budget && !budget.tryTake()) {
      emit({ level: 'warn', msg: 'request budget exhausted', attempt: attempt + 1 });
      throw new JupiterHttpError('local request budget exhausted', { status: 0, body: null, url });
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let res;
    let text;
    emit({ level: 'info', msg: 'request started', attempt: attempt + 1 });
    try {
      res = await fetchImpl(url, { ...init, signal: controller.signal });
      // Keep the deadline active until the body is read, not just the headers.
      text = await res.text();
    } catch (err) {
      const timedOut = err?.name === 'AbortError';
      lastError = new JupiterHttpError(
        timedOut ? `request timed out after ${timeoutMs}ms` : 'network request failed',
        { status: 0, body: null, url },
      );
      lastError.timedOut = timedOut;
      emit({ level: 'error', msg: timedOut ? 'request timed out' : 'network request failed', attempt: attempt + 1 });
    } finally {
      clearTimeout(timer);
    }
    if (text !== undefined) {
      if (res.ok) {
        if (!text) {
          emit({ level: 'info', msg: 'request completed', status: res.status, attempt: attempt + 1 });
          return null;
        }
        try {
          const value = JSON.parse(text);
          emit({ level: 'info', msg: 'request completed', status: res.status, attempt: attempt + 1 });
          return value;
        } catch {
          emit({ level: 'error', msg: 'response was not JSON', status: res.status, attempt: attempt + 1 });
          throw new JupiterHttpError('response was not JSON', { status: res.status, body: null, url });
        }
      }
      lastError = new JupiterHttpError(`HTTP ${res.status}`, { status: res.status, body: null, url });
      emit({ level: 'error', msg: 'HTTP request failed', status: res.status, attempt: attempt + 1 });
      if (!RETRYABLE_STATUS.has(res.status)) break;
    }
    if (attempt === attempts - 1) break;
    const rawRetryAfter = res?.headers?.get?.('retry-after');
    const retryAfter = typeof rawRetryAfter === 'string' && rawRetryAfter.trim()
      ? (/^\d+(?:\.\d+)?$/.test(rawRetryAfter.trim()) ? Number(rawRetryAfter) * 1000 : Date.parse(rawRetryAfter) - Date.now()) : NaN;
    // A bounded caller may refuse a long server delay, but cannot replay early.
    if (Number.isFinite(retryAfter) && retryAfter > 15_000) break;
    const delay = Number.isFinite(retryAfter) ? Math.max(0, retryAfter) : backoffDelayMs(attempt);
    await sleepImpl(delay);
  }

  throw lastError;
}

/** Headers for Jupiter calls. The key is never logged or stringified anywhere. */
export function headers({ apiKey, jwt } = {}) {
  const h = { 'Content-Type': 'application/json' };
  if (apiKey) h['x-api-key'] = apiKey;
  if (jwt) h.Authorization = `Bearer ${jwt}`;
  return h;
}
