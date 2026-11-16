/* An isolated host only. The portal never receives extension commands or data. */
(() => {
  if (globalThis.__smt1000xHost) return;
  globalThis.__smt1000xHost = true;
  let host, frame, body, heading, key = '', collapsed = false;
  const version = chrome.runtime.getManifest().version;

  function mount(symbol) {
    host = document.createElement('aside');
    host.id = 'smt-1000x-indicators';
    host.setAttribute('aria-label', 'SolMarginTrader indicator window');
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
      main{flex:1;min-height:0}iframe{border:0;width:100%;height:100%;display:block}
    `;
    const bar = document.createElement('header');
    heading = document.createElement('strong');
    heading.textContent = `Indicators · ${symbol || 'select market'} · v${version}`;
    const toggle = document.createElement('button');
    toggle.textContent = '−';
    toggle.title = 'Collapse indicators';
    toggle.setAttribute('aria-expanded', 'true');
    const close = document.createElement('button');
    close.textContent = '×';
    close.title = 'Hide chart and stop its feed';
    close.setAttribute('aria-label', 'Hide chart and stop its feed');
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
        frame.title = 'Read-only Jupiter oracle indicators';
        frame.src = chrome.runtime.getURL('src/1000x/panel.html') + `#market=${encodeURIComponent(symbol)}`;
        body.append(frame);
      }
    };
    toggle.addEventListener('click', () => setCollapsed(!collapsed));
    close.addEventListener('click', () => setCollapsed(true));
    let drag;
    bar.addEventListener('pointerdown', (event) => {
      if (event.target.closest('button')) return;
      const r = host.getBoundingClientRect();
      drag = { x: event.clientX - r.left, y: event.clientY - r.top };
      bar.setPointerCapture(event.pointerId);
    });
    bar.addEventListener('pointermove', (event) => {
      if (!drag) return;
      const r = host.getBoundingClientRect();
      host.style.left = `${Math.max(0, Math.min(innerWidth - r.width, event.clientX - drag.x))}px`;
      host.style.top = `${Math.max(0, Math.min(innerHeight - 40, event.clientY - drag.y))}px`;
      host.style.right = 'auto'; host.style.bottom = 'auto';
    });
    bar.addEventListener('pointerup', () => { drag = null; });
    bar.addEventListener('lostpointercapture', () => { drag = null; });
    bar.append(heading, toggle, close);
    shadow.append(style, bar, body);
    document.documentElement.append(host);
    setCollapsed(collapsed);
  }

  function route() {
    const url = new URL(location.href);
    if (!/^\/1000x\/?$/.test(url.pathname)) {
      host?.remove(); host = frame = null; key = ''; return;
    }
    const raw = url.searchParams.get('market') || '';
    const symbol = /^[A-Z0-9]{1,12}$/.test(raw) ? raw : '';
    if (host?.isConnected && key === symbol) return;
    host?.remove(); host = frame = null;
    key = symbol;
    mount(symbol);
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
  window.addEventListener('popstate', route);
  // A back/forward-cache restore resumes the same document without reinjecting
  // content scripts. Suspend the data frame, then restore exactly one host.
  window.addEventListener('pagehide', suspend);
  window.addEventListener('pageshow', resume);
})();
