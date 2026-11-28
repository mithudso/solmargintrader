/* An isolated host only. The portal never receives extension commands or data. */
(() => {
  if (globalThis.__smt1000xHost) return;
  globalThis.__smt1000xHost = true;
  let host, frame, body, heading, key = '', collapsed = false;
  let fitMovedPanel, onWindowClosed, hasWindowMarket = false;
  const version = chrome.runtime.getManifest().version;

  async function controlWindow(action) {
    const response = await chrome.runtime.sendMessage({ type: 'jupiterIndicatorWindow', action });
    if (!response?.ok) throw new Error(response?.error ?? 'Chrome did not respond');
    return response.result.detached;
  }

  function mount({ symbol, kind, side }) {
    const perps = kind === 'perps';
    const canDetach = !perps && Boolean(symbol);
    host = document.createElement('aside');
    host.id = perps ? 'smt-perps-panel' : 'smt-1000x-indicators';
    host.setAttribute('aria-label', perps ? 'SolMarginTrader Perps paper window' : 'SolMarginTrader indicator window');
    const shadow = host.attachShadow({ mode: 'open' });
    const style = document.createElement('style');
    style.textContent = `
      :host{all:initial;position:fixed;right:18px;bottom:18px;width:640px;height:690px;
        max-width:calc(100vw - 24px);max-height:calc(100vh - 24px);min-width:300px;min-height:160px;
        z-index:2147483600;display:flex;flex-direction:column;resize:both;overflow:hidden;
        border:1px solid #46536c;border-radius:12px;background:#101723;color:#e7edf8;
        box-shadow:0 10px 50px #0009;font:13px system-ui,sans-serif;color-scheme:dark}
      :host([data-collapsed]){width:300px!important;height:40px!important;min-height:40px;resize:none}
      :host([data-detached]){width:330px!important;height:40px!important;min-height:40px;resize:none}
      :host([data-window-error]){min-height:66px}
      header{height:40px;min-height:40px;display:flex;align-items:center;gap:8px;padding:0 10px;
        cursor:move;touch-action:none;background:#1c2638;user-select:none;box-sizing:border-box}
      strong{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px}
      button{background:#26344c;color:#e7edf8;border:1px solid #667590;border-radius:5px;
        min-width:30px;min-height:28px;cursor:pointer;font:12px system-ui}
      button:focus-visible{outline:2px solid #80d9ec;outline-offset:2px}
      .move-controls:not([hidden]){display:flex;gap:4px}
      .window-status:not(:empty){padding:3px 10px;color:#f5ce85}
      main{flex:1;min-height:0}iframe{border:0;width:100%;height:100%;display:block}
    `;
    const bar = document.createElement('header');
    heading = document.createElement('strong');
    heading.textContent = `${perps ? 'Perps paper' : 'Indicators'} · ${symbol || 'select market'} · v${version}`;
    const toggle = document.createElement('button');
    toggle.textContent = '−';
    toggle.title = 'Collapse indicators';
    toggle.setAttribute('aria-expanded', 'true');
    const close = document.createElement('button');
    close.textContent = '×';
    close.title = 'Hide chart and stop its feed';
    close.setAttribute('aria-label', 'Hide chart and stop its feed');
    const move = document.createElement('button');
    move.textContent = 'Move';
    move.setAttribute('aria-label', 'Move panel');
    move.setAttribute('aria-expanded', 'false');
    const controls = document.createElement('div');
    controls.id = 'smt-panel-move-controls';
    controls.className = 'move-controls';
    controls.hidden = true;
    controls.setAttribute('role', 'group');
    controls.setAttribute('aria-label', 'Move panel');
    move.setAttribute('aria-controls', controls.id);
    const status = document.createElement('div');
    status.className = 'window-status';
    status.setAttribute('role', 'status');
    const windowButton = (id, label, action) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.id = `smt-1000x-${id}`;
      button.textContent = label;
      button.addEventListener('click', event => {
        if (event.isTrusted) void changeWindow(action);
      });
      return button;
    };
    // The 1s scalp view is its own window; this button only asks the worker to open it.
    const scalp = document.createElement('button');
    scalp.type = 'button';
    scalp.id = 'smt-1000x-scalp';
    scalp.textContent = '1s scalp';
    scalp.title = perps ? 'Open the 1s scalp window for this market: next-30s read-out and the Experiments tab. Read-outs only on the Perps page.'
      : 'Open the 1s scalp window: next-30s read-out, take profit and stop loss';
    scalp.addEventListener('click', async event => {
      if (!event.isTrusted || scalp.disabled) return;
      scalp.disabled = true;
      status.textContent = '';
      try {
        const response = await chrome.runtime.sendMessage({ type: 'jupiterScalpWindow', action: 'open' });
        if (!response?.ok) throw new Error(response?.error ?? 'Chrome did not respond');
      } catch {
        if (active()) status.textContent = 'Could not open the 1s scalp window. Try again.';
      } finally {
        if (active()) { scalp.disabled = false; renderWindow(); }
      }
    });
    const popout = windowButton('popout', 'Pop out', 'open');
    const focus = windowButton('focus', 'Focus', 'focus');
    const dock = windowButton('dock', 'Dock', 'dock');
    const mounted = host;
    const active = () => mounted === host && mounted.isConnected;
    let detached = false, pending = canDetach;

    function renderWindow() {
      mounted.toggleAttribute('data-detached', detached);
      mounted.toggleAttribute('data-window-error', Boolean(status.textContent));
      popout.hidden = !canDetach || detached || !controls.hidden;
      scalp.hidden = !(canDetach || (perps && Boolean(symbol))) || !controls.hidden;
      focus.hidden = dock.hidden = !detached;
      popout.disabled = focus.disabled = dock.disabled = pending;
      move.hidden = detached || !controls.hidden;
      toggle.hidden = close.hidden = detached;
      setCollapsed(collapsed);
    }
    async function changeWindow(action) {
      if (!active() || (pending && action !== 'status')) return;
      pending = true;
      status.textContent = '';
      renderWindow();
      try {
        const isDetached = await controlWindow(action);
        if (active()) detached = isDetached;
      } catch {
        if (active() && action !== 'status') status.textContent = 'Could not change the indicator window. Try again.';
      } finally {
        if (active()) {
          pending = false;
          renderWindow();
        }
      }
    }

    function placePanel(left, top) {
      const { width } = host.getBoundingClientRect();
      host.style.left = `${Math.max(0, Math.min(innerWidth - width, left))}px`;
      host.style.top = `${Math.max(0, Math.min(innerHeight - bar.offsetHeight - 2, top))}px`;
      host.style.right = 'auto';
      host.style.bottom = 'auto';
    }
    fitMovedPanel = () => {
      if (!host.style.left) return;
      const { left, top } = host.getBoundingClientRect();
      placePanel(left, top);
    };
    const moveStep = 24;
    for (const [symbol, label, dx, dy] of [
      ['←', 'Move left', -moveStep, 0],
      ['↑', 'Move up', 0, -moveStep],
      ['↓', 'Move down', 0, moveStep],
      ['→', 'Move right', moveStep, 0],
    ]) {
      const nudge = document.createElement('button');
      nudge.textContent = symbol;
      nudge.title = label;
      nudge.setAttribute('aria-label', label);
      nudge.addEventListener('click', () => {
        const { left, top } = host.getBoundingClientRect();
        placePanel(left + dx, top + dy);
      });
      controls.append(nudge);
    }
    const done = document.createElement('button');
    done.textContent = 'Done';
    controls.append(done);
    const setMoving = active => {
      controls.hidden = !active;
      heading.hidden = active;
      renderWindow();
      move.setAttribute('aria-expanded', String(active));
      (active ? controls.firstElementChild : move).focus({ preventScroll: true });
    };
    let originalPosition;
    move.addEventListener('click', () => {
      const { left, top, right, bottom } = host.style;
      originalPosition = { left, top, right, bottom };
      setMoving(true);
    });
    done.addEventListener('click', () => setMoving(false));
    bar.addEventListener('keydown', event => {
      if (controls.hidden || event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      Object.assign(host.style, originalPosition);
      fitMovedPanel();
      setMoving(false);
    });
    body = document.createElement('main');
    const setCollapsed = (value) => {
      collapsed = value;
      host.toggleAttribute('data-collapsed', value);
      toggle.textContent = value ? '+' : '−';
      toggle.title = value ? 'Open indicators' : 'Collapse indicators';
      toggle.setAttribute('aria-expanded', String(!value));
      if (value || detached || pending) { frame?.remove(); frame = null; }
      else if (!frame) {
        frame = document.createElement('iframe');
        frame.title = perps ? 'Jupiter Perps paper and risk controls' : 'Jupiter indicators and auto-trading controls';
        const path = perps ? 'src/perps/panel.html' : 'src/1000x/panel.html';
        const fragment = new URLSearchParams({ market: symbol });
        if (perps) fragment.set('side', side);
        frame.src = chrome.runtime.getURL(path) + '#' + fragment;
        body.append(frame);
      }
    };
    toggle.addEventListener('click', () => setCollapsed(!collapsed));
    close.addEventListener('click', () => setCollapsed(true));
    let drag;
    bar.addEventListener('pointerdown', (event) => {
      if (!controls.hidden || event.target.closest('button')) return;
      const r = host.getBoundingClientRect();
      drag = { x: event.clientX - r.left, y: event.clientY - r.top };
      bar.setPointerCapture(event.pointerId);
    });
    bar.addEventListener('pointermove', (event) => {
      if (!drag) return;
      placePanel(event.clientX - drag.x, event.clientY - drag.y);
    });
    bar.addEventListener('pointerup', () => { drag = null; });
    bar.addEventListener('lostpointercapture', () => { drag = null; });
    bar.append(heading, scalp, popout, focus, dock, toggle, close, move, controls);
    shadow.append(style, bar, status, body);
    document.documentElement.append(host);
    onWindowClosed = canDetach ? () => {
      if (!active()) return;
      detached = false;
      status.textContent = '';
      renderWindow();
    } : null;
    renderWindow();
    if (canDetach) void changeWindow('status');
  }

  function route() {
    const url = new URL(location.href);
    let target;
    if (/^\/1000x\/?$/.test(url.pathname)) {
      const raw = url.searchParams.get('market') || '';
      target = { kind: 'yolo', symbol: /^[A-Z0-9]{1,12}$/.test(raw) ? raw : '' };
    } else {
      const match = /^\/perps\/(long|short)\/(JupUSD-(SOL|ETH|BTC|ZEC|HYPE)|USDC-(ZEC|HYPE))\/?$/.exec(url.pathname);
      if (match) target = { kind: 'perps', symbol: match[3] ?? match[4], side: match[1] };
    }
    const next = target ? JSON.stringify(target) : '';
    if (host?.isConnected && key === next) return;
    const nextHasMarket = target?.kind === 'yolo' && Boolean(target.symbol);
    if (hasWindowMarket && !nextHasMarket) {
      void controlWindow('status').catch(() => {});
    }
    hasWindowMarket = nextHasMarket;
    if (!target) {
      host?.remove(); host = frame = onWindowClosed = null; key = ''; return;
    }
    host?.remove(); host = frame = null;
    key = next;
    mount(target);
  }
  let timer;
  const resume = () => {
    if (timer) return;
    route();
    timer = setInterval(route, 1000);
  };
  const suspend = () => {
    clearInterval(timer); timer = null;
    host?.remove(); host = frame = onWindowClosed = null; key = '';
  };
  chrome.runtime.onMessage.addListener(({ type } = {}, sender) => {
    if (sender.id === chrome.runtime.id && type === 'jupiter1000xWindowClosed') onWindowClosed?.();
  });
  /** The same three requests on a Perps beta market, answered by perps-bridge.js. */
  function perpsRelay(message, respond, symbol) {
    const bridge = globalThis.__smtPerpsBridge;
    const onMarket = () => new RegExp(`^/perps/(?:long|short)/(?:JupUSD|USDC)-${symbol}/?$`).test(location.pathname);
    const settle = promise => { promise.then(result => respond({ ok: true, ...result }), () => respond({ ok: false, reason: 'page_read_failed' })); return true; };
    try {
      if (!bridge) respond({ ok: false, reason: 'page_read_failed' });
      else if (message.action === 'positions') {
        let form;
        try { form = bridge.readOrderForm(document); } catch { form = { recognized: false, reason: 'order_form_not_found' }; }
        respond({ ok: true, ...bridge.readPositions(document), form: { ...form, market: symbol } });
      } else if (message.action === 'closePosition') {
        if (message.expect?.coin !== symbol) respond({ ok: true, clicked: false, reason: 'position_market_mismatch' });
        else return settle(bridge.closePosition(document, message.expect));
      } else if (message.action === 'openPosition') {
        if (message.request?.coin !== symbol) respond({ ok: true, clicked: false, reason: 'market_mismatch' });
        // The market is checked again just before the press: the page can navigate while the form settles.
        else return settle(bridge.openPosition(document, message.request, { stillValid: onMarket }));
      } else respond({ ok: false, reason: 'unknown_action' });
    } catch {
      respond({ ok: false, reason: 'page_read_failed' });
    }
    return false;
  }

  // Page bridge for the 1s scalp window. Only this extension's background worker
  // may use it (a tab, even one of ours, is refused), and only on the 1000x route.
  chrome.runtime.onMessage.addListener((message, sender, respond) => {
    if (sender.id !== chrome.runtime.id || sender.tab || message?.type !== 'jupiter1000xPage') return undefined;
    // The Perps beta markets have their own bridge with the same contract; every other Perps market is read-outs only.
    const beta = /^\/perps\/(?:long|short)\/(?:JupUSD|USDC)-(ZEC|HYPE)\/?$/.exec(location.pathname);
    // A window opened on one venue never drives the other's page, even if its tab has navigated there.
    if (beta) return message.venue === 'perps' ? perpsRelay(message, respond, beta[1]) : (respond({ ok: false, reason: 'not_on_1000x' }), false);
    const bridge = globalThis.__smt1000xBridge;
    let reply;
    try {
      if (!bridge || !/^\/1000x\/?$/.test(location.pathname) || message.venue === 'perps') reply = { ok: false, reason: message.venue === 'perps' ? 'not_on_perps' : 'not_on_1000x' };
      else if (message.action === 'positions') {
        // The order form opens a position in the page's current market, so report which one that is.
        // A fault in the order-form read must not cost the guard its positions read.
        let form;
        try { form = bridge.readOrderForm(document); } catch { form = { recognized: false, reason: 'order_form_not_found' }; }
        reply = { ok: true, ...bridge.readPositions(document), form: { ...form, market: new URL(location.href).searchParams.get('market') } };
      } else if (message.action === 'closePosition') reply = { ok: true, ...bridge.closePosition(document, message.expect) };
      else if (message.action === 'openPosition') {
        const onMarket = () => /^\/1000x\/?$/.test(location.pathname) && new URL(location.href).searchParams.get('market') === message.request?.coin;
        if (!onMarket()) reply = { ok: true, clicked: false, reason: 'market_mismatch' };
        else {
          // The market is checked again just before the press: the page can navigate while the form settles.
          bridge.openPosition(document, message.request, { stillValid: onMarket }).then(result => respond({ ok: true, ...result }),
            () => respond({ ok: false, reason: 'page_read_failed' }));
          return true; // the reply follows once the page's form has settled
        }
      }
      else reply = { ok: false, reason: 'unknown_action' };
    } catch {
      reply = { ok: false, reason: 'page_read_failed' };
    }
    respond(reply);
    return false;
  });
  resume();
  window.addEventListener('resize', () => {
    if (host?.isConnected) fitMovedPanel();
  });
  window.addEventListener('popstate', route);
  // A back/forward-cache restore resumes the same document without reinjecting
  // content scripts. Suspend the data frame, then restore exactly one host.
  window.addEventListener('pagehide', suspend);
  window.addEventListener('pageshow', resume);
})();
