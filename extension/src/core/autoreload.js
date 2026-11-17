/**
 * Auto-reload on update, as a pure decision with injected effects.
 *
 * Once a minute the service worker asks the soltui host for `buildHash`, a
 * SHA-256 over the manifest and src/ of the extension directory on disk. When
 * that hash differs from the one the worker stored, the code on disk is newer
 * than the code Chrome loaded, and `chrome.runtime.reload()` picks it up.
 *
 * A reload kills the worker. It must never land mid-tick, or between an order
 * submit and its reconcile (that is how a rung double-fires, see engine.js). So:
 *
 *   - the FIRST observation only records the hash;
 *   - an unreachable host never reloads, and is logged once until it recovers;
 *   - a busy engine defers the reload to the next minute WITHOUT recording the
 *     new hash, so the change is not forgotten;
 *   - the final check and the reload happen inside the engine's own store lock,
 *     so nothing can start between "idle" and "reloaded", and anything queued
 *     behind the reload stays queued until the worker is gone.
 *
 * The new hash is stored BEFORE the reload. Storing it after would reload again
 * on every restart if the write was lost.
 *
 * Effects are injected so the whole gate is testable without Chrome.
 */

import { soltuiBuildHash } from './soltui.js';

export const BUILD_STATE_KEY = 'soltuiBuild';

export const OUTCOME = Object.freeze({
  FIRST: 'first-observation',
  UNCHANGED: 'unchanged',
  RELOADED: 'reloaded',
  DEFERRED: 'deferred-busy',
  UNREACHABLE: 'host-unreachable',
  BAD_HASH: 'bad-hash',
});

const HASH = /^[0-9a-f]{64}$/;

/**
 * @param {object} p
 * @param {object} p.deps                  { soltui } transport, as the registry uses it
 * @param {{get:function,set:function}} p.state   persistent key/value (chrome.storage.local)
 * @param {function(): number} p.pending          locked operations queued or running (0 = idle)
 * @param {function(function): Promise} p.withLock runs fn inside the engine store lock
 * @param {function(): void} p.reload             chrome.runtime.reload
 * @param {function(): Promise} [p.hold]          never settles by default: keeps the lock until the worker dies
 * @param {function(object): Promise} p.logEvent  best-effort event log, never given a secret
 * @param {function(): Promise<object>} [p.describe] extra non-secret fields for the reload event
 * @returns {Promise<string>} one of OUTCOME
 */
export async function checkForUpdate({
  deps, state, pending, withLock, reload, logEvent, describe, hold = () => new Promise(() => {}),
}) {
  const saved = (await state.get(BUILD_STATE_KEY, null)) ?? {};
  const envelope = await soltuiBuildHash(deps);
  const hash = envelope.ok ? envelope.result?.hash : undefined;

  if (!envelope.ok) {
    // Log the first failure only; recovery clears the flag, so a later outage logs again.
    if (!saved.hostDown) {
      await state.set(BUILD_STATE_KEY, { ...saved, hostDown: true });
      await logEvent({ type: 'soltui-host-unreachable', code: envelope.error?.code ?? 'failed' });
    }
    return OUTCOME.UNREACHABLE;
  }
  if (typeof hash !== 'string' || !HASH.test(hash)) return OUTCOME.BAD_HASH;

  if (saved.hostDown) await logEvent({ type: 'soltui-host-reachable' });

  if (typeof saved.hash !== 'string') {
    await state.set(BUILD_STATE_KEY, { hash, hostDown: false });
    return OUTCOME.FIRST;
  }
  if (saved.hash === hash) {
    if (saved.hostDown) await state.set(BUILD_STATE_KEY, { hash, hostDown: false });
    return OUTCOME.UNCHANGED;
  }

  // The code on disk changed. Only a quiet engine may be interrupted.
  if (pending() !== 0) return OUTCOME.DEFERRED;

  return withLock(async () => {
    // Inside the lock this operation is the one pending entry. Anything more is
    // work queued beside it, and that work goes first.
    if (pending() > 1) return OUTCOME.DEFERRED;
    const metadata = describe ? await describe() : {};
    await state.set(BUILD_STATE_KEY, { hash, hostDown: false });
    await logEvent({ type: 'auto-reload', from: saved.hash.slice(0, 12), to: hash.slice(0, 12), ...metadata });
    try {
      reload();
    } catch {
      // The reload did not happen, so the change is still pending: put the old
      // hash back so the next minute tries again.
      await state.set(BUILD_STATE_KEY, saved);
      await logEvent({ type: 'auto-reload-failed' });
      return OUTCOME.DEFERRED;
    }
    // Hold the lock until the worker is torn down: a tick queued now waits here
    // instead of running in the last milliseconds of the old code.
    await hold();
    return OUTCOME.RELOADED;
  });
}
