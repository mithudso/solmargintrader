import { mountLivePanel } from './live-panel.js';

/** Keep PiP owned by a persistent document, never the transient action popup. */
export function mountFloatingOwner({ read, asset = () => 'SOL', runtime = chrome.runtime, owner = window, onState = () => {} }) {
  let port = null, retry = null, disposed = false, floating = null, panel = null, opening = null;
  const status = () => {
    try { port?.postMessage({ kind: 'status', floating: !!floating && !floating.closed, visible: !owner.document.hidden }); } catch { /* Worker reconnect follows. */ }
  };
  function pin(coin = asset()) {
    if (disposed) return Promise.reject(new Error('This workspace has closed.'));
    if (floating && !floating.closed) { panel?.setAsset(coin); floating.focus(); return Promise.resolve({ mode: 'picture-in-picture', alwaysOnTop: true }); }
    if (opening) return opening;
    if (!owner.documentPictureInPicture?.requestWindow) return Promise.reject(new Error('Always-on-top needs Chrome Document Picture-in-Picture. Keep this live window open.'));
    // No await or native call before requestWindow: the Port event carries the
    // browser-action gesture, and this API must consume it synchronously.
    const requested = owner.documentPictureInPicture.requestWindow({ width: 430, height: 740 });
    opening = requested.then(pip => {
      if (disposed) { pip.close(); throw new Error('The workspace closed.'); }
      floating = pip;
      pip.document.title = 'Live signals · SolMarginTrader';
      for (const name of ['ui.css', 'signal-desk.css']) {
        const style = pip.document.createElement('link'); style.rel = 'stylesheet'; style.href = runtime.getURL(`src/ui/${name}`); pip.document.head.append(style);
      }
      pip.document.body.className = 'floating-live';
      const header = pip.document.createElement('p'); header.className = 'note floating-owner-note';
      header.textContent = 'Pinned on top · keep the originating workspace open.';
      const host = pip.document.createElement('main'); host.className = 'live-monitor';
      pip.document.body.replaceChildren(header, host);
      panel = mountLivePanel(host, { read, asset: coin, clock: pip,
        dashboardURL: runtime.getURL('src/ui/dashboard.html') });
      pip.addEventListener('pagehide', () => {
        panel?.dispose(); panel = null; floating = null; status(); onState(false);
      }, { once: true });
      status(); onState(true);
      return { mode: 'picture-in-picture', alwaysOnTop: true };
    }).finally(() => { opening = null; });
    return opening;
  }
  function connect() {
    if (disposed) return;
    try {
      port = runtime.connect({ name: 'signal-live-owner' });
      port.onMessage.addListener(message => {
        if (message?.kind === 'ready') { status(); return; }
        if (message?.kind !== 'pin') return;
        const current = port;
        let task;
        try { task = pin(message.asset); } catch (error) { task = Promise.reject(error); }
        Promise.resolve(task).then(result => current.postMessage({ kind: 'result', id: message.id, ok: true, result }),
          error => current.postMessage({ kind: 'result', id: message.id, ok: false,
            error: error.name === 'NotAllowedError' ? 'Click Pin on top inside the live window to grant Chrome its required gesture.' : error.message })).catch(() => {});
      });
      port.onDisconnect.addListener(() => { port = null; if (!disposed) retry = owner.setTimeout(connect, 1000); });
      status();
    } catch { if (!disposed) retry = owner.setTimeout(connect, 1000); }
  }
  const visibility = () => status();
  owner.document.addEventListener('visibilitychange', visibility);
  connect();
  return { pin, dispose() {
    disposed = true; owner.clearTimeout(retry); owner.document.removeEventListener('visibilitychange', visibility);
    panel?.dispose(); floating?.close(); port?.disconnect(); port = null;
  } };
}
