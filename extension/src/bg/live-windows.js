/** Browser-only window transport; the action stays in the shared registry. */
export function createLiveWindows({ runtime, windows, getURL, timeoutMs = 5000 }) {
  const owners = new Map(), pending = new Map();
  let sequence = 0, opening = null;
  const allowed = new Set([getURL('src/ui/dashboard.html'), getURL('src/ui/live-window.html')]);
  runtime.onConnect.addListener(port => {
    if (port.name !== 'signal-live-owner' || !allowed.has((port.sender?.url ?? '').split(/[?#]/)[0])) return;
    const id = ++sequence;
    const entry = { port, floating: false, visible: true, order: id };
    owners.set(id, entry);
    port.onMessage.addListener(message => {
      if (message?.kind === 'status') {
        entry.floating = message.floating === true;
        entry.visible = message.visible === true;
      }
      if (message?.kind !== 'result') return;
      const task = pending.get(message.id);
      if (!task || task.port !== port) return;
      pending.delete(message.id); clearTimeout(task.timer);
      message.ok ? task.resolve(message.result) : task.reject(new Error(message.error ?? 'Could not pin live signals'));
    });
    port.onDisconnect.addListener(() => {
      owners.delete(id);
      for (const [request, task] of pending) if (task.port === port) {
        pending.delete(request); clearTimeout(task.timer);
        task.reject(new Error('The live workspace closed. Open it again to pin signals.'));
      }
    });
    port.postMessage({ kind: 'ready' });
  });
  return {
    open(asset = 'SOL') {
      if (!/^[A-Z0-9]{1,20}$/.test(asset)) throw new Error('Invalid signal coin');
      const owner = [...owners.values()].sort((a, b) => Number(b.floating) - Number(a.floating)
        || Number(b.visible) - Number(a.visible) || b.order - a.order)[0];
      if (owner) {
        // This call must happen synchronously in the runtime message event.
        // Awaiting store/native work first loses the transient user gesture.
        return new Promise((resolve, reject) => {
          const id = ++sequence;
          const timer = setTimeout(() => { pending.delete(id); reject(new Error('Live window did not answer. Try Pin in the workspace.')); }, timeoutMs);
          pending.set(id, { port: owner.port, resolve, reject, timer });
          try { owner.port.postMessage({ kind: 'pin', id, asset }); }
          catch (error) { pending.delete(id); clearTimeout(timer); reject(error); }
        });
      }
      // A new document cannot inherit DOM activation. Its direct Pin button is
      // the minimal second gesture Chrome requires; do not claim this is AOT.
      opening ??= windows.create({ url: getURL(`src/ui/live-window.html?asset=${asset}`),
        type: 'popup', width: 430, height: 740, focused: true }).then(window => ({
        mode: 'window', windowId: window?.id, requiresPin: true,
        message: 'Live window opened. Click Pin on top there.' })).finally(() => { opening = null; });
      return opening;
    },
  };
}
