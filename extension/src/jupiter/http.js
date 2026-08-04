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
    return String(url);
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
}) {
  // Budget is charged per ATTEMPT, not per call: a retry storm that bypassed
  // the budget would defeat the point of having one.
  if (budget && !budget.tryTake()) {
    throw new JupiterHttpError('local request budget exhausted', { status: 0, body: null, url });
  }

  let lastError;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (attempt > 0 && budget && !budget.tryTake()) {
      throw new JupiterHttpError('local request budget exhausted mid-retry', {
        status: 0,
        body: null,
        url,
      });
    }

    let res;
    // Without a timeout a stalled connection hangs the tick until Chrome kills
    // the whole service worker, losing the journal flush with it.
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timer = controller && timeoutMs > 0 ? setTimeout(() => controller.abort(), timeoutMs) : null;
    try {
      res = await fetchImpl(url, controller ? { ...init, signal: controller.signal } : init);
    } catch (err) {
      // Network-level failure (offline, DNS, timeout abort): retryable.
      const timedOut = err.name === 'AbortError';
      lastError = new JupiterHttpError(
        timedOut ? `request timed out after ${timeoutMs}ms` : `network failure: ${err.message}`,
        { status: 0, body: null, url },
      );
      lastError.timedOut = timedOut;
      if (attempt === maxAttempts - 1) break;
      await sleepImpl(backoffDelayMs(attempt));
      continue;
    } finally {
      if (timer) clearTimeout(timer);
    }

    if (res.ok) {
      const text = await res.text();
      if (!text) return null;
      try {
        return JSON.parse(text);
      } catch {
        throw new JupiterHttpError('response was not JSON', {
          status: res.status,
          body: text.slice(0, 200),
          url,
        });
      }
    }

    const body = await res.text().catch(() => '');
    lastError = new JupiterHttpError(`HTTP ${res.status}`, { status: res.status, body: body.slice(0, 400), url });

    if (!RETRYABLE_STATUS.has(res.status) || attempt === maxAttempts - 1) break;

    // Honour Retry-After when the server sends one; it knows better than our curve.
    const retryAfter = Number(res.headers?.get?.('retry-after'));
    const delay = Number.isFinite(retryAfter) && retryAfter > 0
      ? retryAfter * 1000
      : backoffDelayMs(attempt);
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
