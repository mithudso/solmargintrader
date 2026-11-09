/**
 * Service-worker transport to the soltui native messaging host.
 *
 * Chrome starts `com.mitchhudson.soltui` (soltui/native_host.py) on demand and
 * speaks length-prefixed JSON with it. This file owns what is Chrome-specific
 * about that: the port, the request id, the per-call timeout and the clean
 * error when the host is not installed. The envelope handling lives in
 * src/core/soltui.js, which is shared with the node transport.
 *
 * Dashboard leases retain one multiplexed port so replay and job state survives
 * between calls. With no dashboard, probes still use short-lived connections.
 * Disconnects and timeouts never replay a request: a submit may have succeeded.
 */

import { SoltuiTransportError, SOLTUI_ERROR, SOLTUI_HOST_NAME } from '../core/soltui.js';

const INSTALL_HINT = 'run `python -m soltui.native_host_install install` and reload the extension';

const describeRequest = (request) => (request.op === 'call' ? request.command : request.op);

/**
 * @param {object} [opts]
 * @param {function(string): object} [opts.connect]  chrome.runtime.connectNative
 * @param {function(): string} [opts.lastError]      the text of chrome.runtime.lastError
 * @param {function(): string} [opts.newId]
 * @param {string} [opts.hostName]
 */
function createOneShotTransport({
  connect = (name) => chrome.runtime.connectNative(name),
  lastError = () => chrome.runtime.lastError?.message ?? '',
  newId = () => crypto.randomUUID(),
  hostName = SOLTUI_HOST_NAME,
} = {}) {
  return {
    request(request, { timeoutMs }) {
      return new Promise((resolve, reject) => {
        const id = newId();
        let port;
        let timer;
        let done = false;

        const finish = (fn, value) => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          try { port?.disconnect(); } catch { /* already closed */ }
          fn(value);
        };

        try {
          port = connect(hostName);
        } catch {
          finish(reject, new SoltuiTransportError(SOLTUI_ERROR.FAILED,
            `soltui native host "${hostName}" could not be started; ${INSTALL_HINT}`));
          return;
        }

        port.onMessage.addListener((msg) => {
          // Replies for any other request id are not ours.
          if (msg?.id !== id) return;
          finish(resolve, msg.response);
        });
        port.onDisconnect.addListener(() => {
          // Read lastError here, in the event, or Chrome logs it as unchecked.
          const reason = lastError();
          finish(reject, new SoltuiTransportError(SOLTUI_ERROR.FAILED,
            `soltui native host "${hostName}" is not available${reason ? ` (${reason})` : ''}; ${INSTALL_HINT}`));
        });
        timer = setTimeout(() => {
          finish(reject, new SoltuiTransportError(SOLTUI_ERROR.TIMEOUT,
            `soltui ${describeRequest(request)} timed out after ${Math.round(timeoutMs / 1000)}s`));
        }, timeoutMs);

        try {
          port.postMessage({ id, ...request });
        } catch {
          finish(reject, new SoltuiTransportError(SOLTUI_ERROR.FAILED, 'soltui native host rejected the request'));
        }
      });
    },
  };
}

/** Dashboard leases expire after a crash; pending calls hold their own connection. */
export function createNativeTransport({
  connect = (name) => chrome.runtime.connectNative(name),
  lastError = () => chrome.runtime.lastError?.message ?? '',
  newId = () => crypto.randomUUID(),
  hostName = SOLTUI_HOST_NAME,
  leaseMs = 90_000,
} = {}) {
  const oneShot = createOneShotTransport({ connect, lastError, newId, hostName });
  const leases = new Map();
  const pending = new Map();
  let port = null;
  let generation = 0;

  function closeIfIdle() {
    if (leases.size || pending.size || !port) return;
    const old = port;
    port = null;
    old.disconnect();
  }
  function finish(id, error, value) {
    const call = pending.get(id);
    if (!call) return;
    pending.delete(id);
    clearTimeout(call.timer);
    if (error) call.reject(error);
    else call.resolve(value);
    closeIfIdle();
  }
  function open() {
    if (port) return port;
    const opened = connect(hostName);
    port = opened;
    generation += 1;
    opened.onMessage.addListener((msg) => {
      if (port === opened) finish(msg?.id, null, msg?.response);
    });
    opened.onDisconnect.addListener(() => {
      const reason = lastError();
      if (port !== opened) return;
      port = null;
      const error = new SoltuiTransportError(SOLTUI_ERROR.FAILED,
        `soltui session disconnected${reason ? ` (${reason})` : ''}; in-memory replay and jobs may be lost. Check saved state before continuing. Requests were not retried; ${INSTALL_HINT}`);
      for (const id of [...pending.keys()]) finish(id, error);
    });
    return opened;
  }
  return {
    busy: () => leases.size > 0 || pending.size > 0,
    session(id, active) {
      clearTimeout(leases.get(id));
      leases.delete(id);
      if (active) {
        const timer = setTimeout(() => { leases.delete(id); closeIfIdle(); }, leaseMs);
        timer.unref?.();
        leases.set(id, timer);
      }
      closeIfIdle();
      return { available: true, connected: port !== null, generation };
    },
    request(request, { timeoutMs }) {
      if (!leases.size && !port) return oneShot.request(request, { timeoutMs });
      return new Promise((resolve, reject) => {
        const id = newId();
        let current;
        try { current = open(); }
        catch {
          reject(new SoltuiTransportError(SOLTUI_ERROR.FAILED, `soltui native host could not be started; ${INSTALL_HINT}`));
          return;
        }
        const timer = setTimeout(() => finish(id, new SoltuiTransportError(SOLTUI_ERROR.TIMEOUT,
          `soltui ${describeRequest(request)} timed out. Its outcome is unknown; check status before continuing. This request was not retried.`)), timeoutMs);
        pending.set(id, { resolve, reject, timer });
        try { current.postMessage({ ...request, id }); }
        catch { finish(id, new SoltuiTransportError(SOLTUI_ERROR.FAILED, 'soltui native host rejected the request; it was not retried')); }
      });
    },
  };
}
