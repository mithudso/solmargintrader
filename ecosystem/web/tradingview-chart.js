"use strict";

(() => {
  const load = document.getElementById("tradingview-load");
  const close = document.getElementById("tradingview-close");
  const container = document.getElementById("tradingview-chart-container");
  const status = document.getElementById("tradingview-status");

  load.addEventListener("click", () => {
    if (container.children.length) return;
    const frame = document.createElement("iframe");
    frame.title = "TradingView CRYPTO:ZECUSD one-minute price chart";
    // The official embed script generates this remote iframe endpoint. Keep
    // vendor code outside our origin; never give it the control room's session.
    const config = {
      autosize: true, symbol: "CRYPTO:ZECUSD", interval: "1",
      timezone: "Etc/UTC", theme: "light", style: "1", locale: "en",
      allow_symbol_change: false, withdateranges: true,
      hide_side_toolbar: false, save_image: false,
      support_host: "https://www.tradingview.com",
    };
    frame.setAttribute("sandbox", "allow-scripts allow-same-origin");
    frame.referrerPolicy = "no-referrer";
    frame.src = "https://www.tradingview-widget.com/embed-widget/advanced-chart/?locale=en#" + encodeURIComponent(JSON.stringify(config));
    container.replaceChildren(frame);
    container.hidden = false;
    load.disabled = true;
    close.hidden = false;
    status.textContent = "External TradingView chart: ZECUSD reference prices. If market data is unavailable, use the TradingView account chart link above.";
  });

  close.addEventListener("click", () => {
    container.replaceChildren();
    container.hidden = true;
    load.disabled = false;
    close.hidden = true;
    status.textContent = "Chart closed. Load it to connect to TradingView for external market data.";
    load.focus();
  });
})();
