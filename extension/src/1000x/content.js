/* An isolated host only. The portal never receives extension commands or data. */
(() => {
  if (globalThis.__smt1000xHost) return;
  globalThis.__smt1000xHost = true;
  let host, frame, body, heading, key = '', collapsed = false;
  let fitMovedPanel;
  const version = chrome.runtime.getManifest().version;

  function mount({ symbol, kind, side }) {
    const perps = kind === 'perps';
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
      header{height:40px;min-height:40px;display:flex;align-items:center;gap:8px;padding:0 10px;
        cursor:move;touch-action:none;background:#1c2638;user-select:none;box-sizing:border-box}
      strong{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px}
      button{background:#26344c;color:#e7edf8;border:1px solid #667590;border-radius:5px;
        min-width:30px;min-height:28px;cursor:pointer;font:12px system-ui}
      button:focus-visible{outline:2px solid #80d9ec;outline-offset:2px}
      .move-controls:not([hidden]){display:flex;gap:4px}
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
      move.hidden = active;
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
      if (value) { frame?.remove(); frame = null; }
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
    bar.append(heading, toggle, close, move, controls);
    shadow.append(style, bar, body);
    document.documentElement.append(host);
    setCollapsed(collapsed);
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
    if (!target) {
      host?.remove(); host = frame = null; key = ''; return;
    }
    const next = JSON.stringify(target);
    if (host?.isConnected && key === next) return;
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
    host?.remove(); host = frame = null; key = '';
  };
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
