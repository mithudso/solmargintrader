const STORAGE = 'jupiter1000xScalpWindows';
const PAGE = 'src/1000x/scalp.html';
const BRIDGE = 'jupiter1000xPage';
const SYMBOL = /^[A-Z0-9]{1,12}$/;
const RELAY_TIMEOUT_MS = 4000;

function jupiterMarket(value) {
  try {
    const url = new URL(value);
    if (url.origin !== 'https://jup.ag' || !/^\/1000x\/?$/.test(url.pathname)) return null;
    const symbol = url.searchParams.get('market') ?? '';
    return SYMBOL.test(symbol) ? symbol : '';
  } catch {
    return null;
  }
}

/**
 * One 1s scalp window per Jupiter 1000x tab, and the only route from that
 * window to the tab's page bridge. The window can read the tab's listed
 * positions and ask for one Close click; nothing else is relayed, and only the
 * window this module opened for that tab may ask. Session state survives MV3
 * worker eviction.
 */
export function createJupiterScalpWindows({ runtime, storage, tabs, windows, setTimeoutImpl = globalThis.setTimeout, clearTimeoutImpl = globalThis.clearTimeout }) {
  const pageURL = symbol => `${runtime.getURL(PAGE)}#market=${encodeURIComponent(symbol)}`;
  const load = async () => (await storage.get(STORAGE))[STORAGE] ?? {};
  const save = entries => storage.set({ [STORAGE]: entries });
  let queue = Promise.resolve();
  function serialize(operation) {
    const next = queue.then(operation);
    queue = next.catch(() => {});
    return next;
  }
  async function drop(entries, tabId, { closeWindow }) {
    const entry = entries[tabId];
    delete entries[tabId];
    await save(entries);
    if (closeWindow && entry) await windows.remove(entry.windowId).catch(() => {});
  }

  windows.onRemoved.addListener(windowId => {
    void serialize(async () => {
      const entries = await load();
      const match = Object.entries(entries).find(([, entry]) => entry.windowId === windowId);
      if (match) await drop(entries, match[0], { closeWindow: false });
    }).catch(() => {});
  });
  // The window stays open when its Jupiter tab reloads or navigates: an armed
  // guard must report that it lost the page, not vanish. It closes with the tab,
  // unless a guard is live: then it stays to say that the page is gone.
  tabs.onRemoved.addListener(tabId => {
    void serialize(async () => {
      const entries = await load();
      if (entries[tabId]) await drop(entries, tabId, { closeWindow: entries[tabId].guardLive !== true });
    }).catch(() => {});
  });

  function panelEntry(entries, sender) {
    return Object.entries(entries).find(([, entry]) => entry.panelTabId === sender.tab.id
      && entry.windowId === sender.tab.windowId && sender.url === pageURL(entry.symbol));
  }

  /** Ask the owning tab's content script; a missing or late reply is an explicit failure. */
  async function relay(tabId, message) {
    // Without the "tabs" permission the worker cannot read the tab's address. The
    // content script only exists on jup.ag and answers only on the 1000x route.
    if (!await tabs.get(tabId).catch(() => null)) return { ok: false, reason: 'jupiter_tab_unavailable' };
    let timer;
    const timeout = new Promise(resolve => { timer = setTimeoutImpl(() => resolve({ ok: false, reason: 'page_timeout' }), RELAY_TIMEOUT_MS); });
    try {
      const reply = await Promise.race([tabs.sendMessage(tabId, { type: BRIDGE, ...message }, { frameId: 0 }), timeout]);
      return reply && typeof reply === 'object' ? reply : { ok: false, reason: 'page_no_reply' };
    } catch {
      return { ok: false, reason: 'page_unreachable' };
    } finally {
      clearTimeoutImpl(timer);
    }
  }

  return {
    control(action, sender, args = {}) {
      return serialize(async () => {
        const tabId = sender?.tab?.id;
        if (sender?.frameId !== 0 || !Number.isInteger(tabId)) throw new Error('The scalp window requires its owning browser tab');
        const entries = await load();
        const market = jupiterMarket(sender.url);

        if (market === null) {
          // Requests from the scalp window itself.
          const match = panelEntry(entries, sender);
          if (!match) throw new Error('This scalp window is not attached to a Jupiter 1000x tab');
          const [sourceTabId, entry] = match;
          if (action === 'status') return { attached: true, symbol: entry.symbol };
          if (action === 'guardState') {
            // The worker cannot see the guard; the window says when one is live so it is not closed under it.
            entry.guardLive = args.live === true;
            await save(entries);
            return { ok: true, live: entry.guardLive };
          }
          if (action === 'positions') return relay(Number(sourceTabId), { action: 'positions' });
          if (action === 'closePosition') {
            const expect = args.expect;
            if (!expect || expect.coin !== entry.symbol) return { ok: false, reason: 'position_market_mismatch' };
            return relay(Number(sourceTabId), { action: 'closePosition', expect });
          }
          if (action === 'showJupiter') {
            const tab = await tabs.get(Number(sourceTabId)).catch(() => null);
            if (!tab) return { ok: false, reason: 'jupiter_tab_unavailable' };
            await tabs.update(tab.id, { active: true });
            await windows.update(tab.windowId, { focused: true });
            return { ok: true };
          }
          throw new Error('Invalid scalp window action');
        }

        // Requests from the Jupiter tab's content script.
        let entry = entries[tabId];
        if (entry && !await windows.get(entry.windowId).catch(() => null)) {
          await drop(entries, tabId, { closeWindow: false });
          entry = null;
        }
        if (action === 'status') return { open: Boolean(entry) };
        const LIVE = 'A take profit or stop loss is live in the open 1s scalp window. Disarm it there first.';
        if (action === 'close') {
          if (entry?.guardLive) throw new Error(LIVE);
          if (entry) await drop(entries, tabId, { closeWindow: true });
          return { open: false };
        }
        if (action !== 'open') throw new Error('Invalid scalp window action');
        if (!market) throw new Error('Select a Jupiter 1000x market first');
        if (entry && entry.symbol === market) {
          await windows.update(entry.windowId, { focused: true });
          return { open: true };
        }
        if (entry?.guardLive) {
          await windows.update(entry.windowId, { focused: true });
          throw new Error(LIVE);
        }
        if (entry) await drop(entries, tabId, { closeWindow: true });
        let popup;
        try {
          // Register the owner before the page loads, so its first status request is answered.
          popup = await windows.create({ type: 'popup', url: 'about:blank', width: 500, height: 1000, focused: true });
          const panelTabId = (popup?.tabs ?? (await windows.get(popup.id, { populate: true })).tabs)?.[0]?.id;
          if (!Number.isInteger(popup?.id) || !Number.isInteger(panelTabId)) throw new Error('Chrome did not create a scalp window');
          entries[tabId] = { windowId: popup.id, panelTabId, symbol: market };
          await save(entries);
          await tabs.update(panelTabId, { url: pageURL(market) });
          return { open: true };
        } catch (error) {
          if (entries[tabId]) await drop(entries, tabId, { closeWindow: true });
          else if (Number.isInteger(popup?.id)) await windows.remove(popup.id).catch(() => {});
          throw error;
        }
      });
    },
  };
}
