/**
 * Service-worker transport to the soltui native messaging host.
 *
 * Chrome starts `com.mitchhudson.soltui` (soltui/native_host.py) on demand and
 * speaks length-prefixed JSON with it. This file owns what is Chrome-specific
 * about that: the port, the request id, the per-call timeout and the clean
 * error when the host is not installed. The envelope handling lives in
 * src/core/soltui.js, which is shared with the node transport.
 *
 * One short-lived connection per request, closed as soon as the reply arrives.
 * A connectNative port left open keeps the service worker alive and the host
 * process running for nothing, and a once-a-minute build probe does not need a
 * warm host. A request that times out disconnects, which ends the host process;
 * otherwise a runaway command would block the next request behind it.
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
export function createNativeTransport({
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
