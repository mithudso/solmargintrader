const STORAGE = 'jupiter1000xDetachedWindows';
const PANEL = 'src/1000x/panel.html';
const CLOSED = 'jupiter1000xWindowClosed';
const SYMBOL = /^[A-Z0-9]{1,12}$/;

function jupiterRoute(value) {
  try {
    const url = new URL(value);
    if (url.origin !== 'https://jup.ag') return null;
    const symbol = url.searchParams.get('market') ?? '';
    return /^\/1000x\/?$/.test(url.pathname) && SYMBOL.test(symbol) ? symbol : '';
  } catch {
    return null;
  }
}

/** One detached panel per source tab. Session state survives MV3 worker eviction. */
export function createJupiterIndicatorWindows({ runtime, storage, tabs, windows }) {
  const panelURL = runtime.getURL(PANEL);
  const detachedURL = symbol => `${panelURL}?detached=1#market=${encodeURIComponent(symbol)}`;
  const load = async () => (await storage.get(STORAGE))[STORAGE] ?? {};
  const save = entries => storage.set({ [STORAGE]: entries });
  const notify = (tabId, entry) => tabs.sendMessage(Number(tabId), { type: CLOSED },
    { documentId: entry.documentId }).catch(() => {});
  // Browser events and clicks share the same short transaction queue.
  let queue = Promise.resolve();
  function serialize(operation) {
    const next = queue.then(operation);
    queue = next.catch(() => {});
    return next;
  }
  async function forget(entries, tabId, entry) {
    delete entries[tabId];
    await save(entries);
    await notify(tabId, entry);
  }
  async function close(entries, tabId, entry) {
    try {
      await windows.remove(entry.windowId);
    } catch (error) {
      // Only restore the docked feed after the detached window is really gone.
      if (await windows.get(entry.windowId).catch(() => null)) throw error;
    }
    await forget(entries, tabId, entry);
  }

  windows.onRemoved.addListener(windowId => {
    void serialize(async () => {
      const entries = await load();
      const match = Object.entries(entries).find(([, entry]) => entry.windowId === windowId);
      if (match) await forget(entries, ...match);
    }).catch(() => {});
  });
  function sourceGone(tabId, change) {
    void serialize(async () => {
      const entries = await load();
      const entry = entries[tabId];
      if (entry && (!change || change.status === 'loading' || jupiterRoute(change.url) !== entry.symbol)) {
        await close(entries, tabId, entry);
      }
    }).catch(() => {});
  }
  tabs.onRemoved.addListener(tabId => sourceGone(tabId));
  tabs.onUpdated.addListener((tabId, change) => {
    if (change.status === 'loading' || change.url) sourceGone(tabId, change);
  });

  return {
    control(action, sender) {
      return serialize(async () => {
        const tabId = sender?.tab?.id;
        if (sender?.frameId !== 0 || !Number.isInteger(tabId) || !sender.documentId) {
          throw new Error('Indicator window requires its owning browser tab');
        }
        const entries = await load();
        const symbol = jupiterRoute(sender.url);
        if (symbol === null) {
          const match = Object.entries(entries).find(([, entry]) =>
            entry.panelTabId === tabId && entry.windowId === sender.tab.windowId &&
            sender.url === detachedURL(entry.symbol));
          if (!match || !['status', 'dock'].includes(action)) throw new Error('Indicator window is no longer attached');
          if (action === 'dock') await close(entries, ...match);
          return { detached: action === 'status' };
        }
        let entry = entries[tabId];
        if (entry && (symbol !== entry.symbol || sender.documentId !== entry.documentId)) {
          await close(entries, tabId, entry);
          entry = null;
        }
        if (entry && !await windows.get(entry.windowId).catch(() => null)) {
          await forget(entries, tabId, entry);
          entry = null;
        }
        if (action === 'status') return { detached: Boolean(entry) };
        if (action === 'dock' && entry) {
          await close(entries, tabId, entry);
          return { detached: false };
        }
        if (action === 'dock' || (action === 'focus' && !entry)) return { detached: false };
        if (!symbol) throw new Error('Select a Jupiter 1000x market first');
        if (entry) {
          await windows.update(entry.windowId, { focused: true });
          return { detached: true };
        }
        let popup;
        try {
          // Register the owner before the new panel document starts its feed.
          popup = await windows.create({ type: 'popup', url: 'about:blank', width: 640, height: 760, focused: true });
          if (!Number.isInteger(popup?.id)) throw new Error('Chrome did not create an indicator window');
          const popupTabs = popup.tabs ?? (await windows.get(popup.id, { populate: true })).tabs;
          const panelTabId = popupTabs?.[0]?.id;
          if (!Number.isInteger(panelTabId)) throw new Error('Chrome did not create an indicator tab');
          entries[tabId] = { windowId: popup.id, panelTabId, symbol, documentId: sender.documentId };
          await save(entries);
          await tabs.update(panelTabId, { url: detachedURL(symbol) });
          return { detached: true };
        } catch (error) {
          if (entries[tabId]) await close(entries, tabId, entries[tabId]);
          else if (Number.isInteger(popup?.id)) await windows.remove(popup.id).catch(() => {});
          throw error;
        }
      });
    },
  };
}
