"use strict";

(() => {
  const palette = [
    "#1d6f8a", "#9b4f20", "#456b32", "#74528a", "#a43d4a", "#387e71",
    "#92711f", "#315b9b", "#9a6042", "#58616f", "#5a7831", "#8a4569",
    "#28759f", "#786026",
  ];
  const shortNames = {
    ma_crossover: "MA", rsi: "RSI", breakout: "BO", macd: "MACD",
    bb_reversion: "BB-R", bb_breakout: "BB-B", keltner: "KEL",
    ts_momentum: "TSM", stochastic: "STO", zscore: "ZS",
    sma_regime: "SMA", ema_crossover: "EMA", ppo: "PPO", ma_ribbon: "RIB",
  };
  let chart;
  let priceSeries;
  let markers;
  let graphData = null;
  let selected = null;
  let signature = "";
  let libraryPromise;

  const byId = (id) => document.getElementById(id);
  const text = (id, value) => { byId(id).textContent = value; };
  const directionName = (value) => value === 1 ? (graphData?.aggregate_semantics === "target_exposure_not_probability" ? "Long" : "Up") : value === -1 ? "Down" : value === 0 ? "Flat" : "No call";
  const directionMark = (value) => value === 1 ? "↑" : value === -1 ? "↓" : value === 0 ? "·" : "";
  const formatBps = (value) => Number.isFinite(value) ? `${value > 0 ? "+" : ""}${value.toFixed(1)} bps` : "Unavailable";

  async function loadLibrary() {
    if (!libraryPromise) libraryPromise = import("/lightweight-charts.mjs");
    return libraryPromise;
  }

  async function ensureChart() {
    if (chart) return;
    const library = await loadLibrary();
    chart = library.createChart(byId("oracle-chart"), {
      autoSize: true,
      layout: { background: { color: "#fff" }, textColor: "#42536a", attributionLogo: true },
      grid: { vertLines: { color: "#edf0f4" }, horzLines: { color: "#edf0f4" } },
      rightPriceScale: { borderColor: "#d9e0e8" },
      timeScale: { borderColor: "#d9e0e8", timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: "#95a4b6" }, horzLine: { color: "#95a4b6" } },
    });
    priceSeries = chart.addSeries(library.LineSeries, {
      color: "#173f66", lineWidth: 2, priceLineVisible: false,
      lastValueVisible: true, crosshairMarkerVisible: true,
    });
    markers = library.createSeriesMarkers(priceSeries, []);
    byId("oracle-chart").dataset.chartReady = "true";
  }

  function setStatus(graph) {
    const ready = graph?.status === "available" && Array.isArray(graph.ticks) && graph.ticks.length > 0;
    text("oracle-graph-status", ready ? `${graph.count} recorded ticks` : "History unavailable");
    text("oracle-chart-status", ready
      ? `Showing ${graph.ticks.length} of the latest evaluated ticks for ${graph.instrument}. Strategy markers are directions at observed prices; no price target is inferred.`
      : graph?.reason === "graph_history_not_recorded"
        ? "This archive predates graph history. New evaluations will appear here."
        : "Graph history will appear after the Oracle records a completed-bar evaluation.");
    return ready;
  }

  function updateShape(tick) {
    const shape = tick?.market_shape;
    if (!shape) {
      text("oracle-shape-summary", "No completed-bar shape was recorded.");
      byId("oracle-shape-fields").replaceChildren();
      return;
    }
    const through = Number.isFinite(shape.lookback_end)
      ? ` · through ${new Date(shape.lookback_end * 1000).toISOString()}`
      : " · context unavailable";
    text("oracle-shape-summary", `${shape.lookback_bars} prior completed bars${through}`);
    const values = [
      ["Net return", formatBps(shape.net_return_bps)],
      ["Observed range", formatBps(shape.range_bps)],
      ["Path efficiency", Number.isFinite(shape.path_efficiency) ? `${(shape.path_efficiency * 100).toFixed(1)}%` : "Unavailable"],
      ["Realized volatility", formatBps(shape.realized_volatility_bps)],
    ];
    const fragment = document.createDocumentFragment();
    values.forEach(([name, value]) => {
      const item = document.createElement("div");
      const term = document.createElement("dt");
      const description = document.createElement("dd");
      term.textContent = name;
      description.textContent = value;
      item.append(term, description);
      fragment.append(item);
    });
    byId("oracle-shape-fields").replaceChildren(fragment);
  }

  function renderLatestRows(tick) {
    const fragment = document.createDocumentFragment();
    (tick.strategies || []).forEach((row, index) => {
      const tr = document.createElement("tr");
      const name = document.createElement("td");
      const signal = document.createElement("td");
      const accuracy = document.createElement("td");
      const eligible = document.createElement("td");
      name.textContent = row.strategy_id;
      name.className = `oracle-strategy-name oracle-color-${index % palette.length}`;
      signal.textContent = directionName(row.direction);
      accuracy.textContent = Number.isFinite(row.accuracy_percent) ? `${row.accuracy_percent.toFixed(1)}% (${row.resolved})` : "No resolved evidence";
      eligible.textContent = row.vote_eligible ? "Eligible" : row.reason ? `Excluded · ${row.reason.replaceAll("_", " ")}` : "Not eligible";
      tr.append(name, signal, accuracy, eligible);
      fragment.append(tr);
    });
    const aggregate = document.createElement("tr");
    aggregate.className = "oracle-aggregate-row";
    const aggregateLabel = document.createElement("th");
    const aggregateSignal = document.createElement("td");
    const aggregateBalance = document.createElement("td");
    const aggregateEligible = document.createElement("td");
    aggregateLabel.scope = "row";
    aggregateLabel.textContent = graphData?.aggregate_semantics === "target_exposure_not_probability" ? "Selected ensemble" : "Full-catalog aggregate";
    aggregateSignal.textContent = tick.aggregate?.signal || "Unavailable";
    aggregateBalance.textContent = Number.isFinite(tick.aggregate?.balance_percent)
      ? `${tick.aggregate.balance_percent.toFixed(1)}% ${graphData?.aggregate_semantics === "target_exposure_not_probability" ? "target exposure" : "signed vote balance"}`
      : "No vote balance";
    aggregateEligible.textContent = `${tick.aggregate?.included?.length || 0} included · ${tick.aggregate?.excluded?.length || 0} excluded`;
    aggregate.append(aggregateLabel, aggregateSignal, aggregateBalance, aggregateEligible);
    fragment.append(aggregate);
    byId("oracle-chart-rows").replaceChildren(fragment);
  }

  function createLegend(strategies) {
    const container = byId("oracle-chart-legend");
    const ids = strategies.map((row) => row.strategy_id);
    if (!selected) selected = new Set([...ids, "__aggregate__"]);
    else ids.forEach((id) => selected.add(id));
    const fragment = document.createDocumentFragment();
    strategies.forEach((row, index) => {
      const label = document.createElement("label");
      label.className = "oracle-overlay-toggle";
      label.classList.add(`oracle-color-${index % palette.length}`);
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = row.strategy_id;
      input.checked = selected.has(row.strategy_id);
      input.addEventListener("change", () => {
        if (input.checked) selected.add(input.value);
        else selected.delete(input.value);
        drawMarkers();
      });
      const name = document.createElement("span");
      name.textContent = row.strategy_id;
      label.append(input, name);
      fragment.append(label);
    });
    const aggregate = document.createElement("label");
    aggregate.className = "oracle-overlay-toggle aggregate-overlay-toggle";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = "__aggregate__";
    input.checked = selected.has("__aggregate__");
    input.addEventListener("change", () => {
      if (input.checked) selected.add(input.value);
      else selected.delete(input.value);
      drawMarkers();
    });
    const name = document.createElement("span");
    name.textContent = graphData?.aggregate_semantics === "target_exposure_not_probability" ? "Selected ensemble" : "Full-catalog aggregate";
    aggregate.append(input, name);
    fragment.append(aggregate);
    container.replaceChildren(fragment);
  }

  function drawMarkers() {
    if (!markers || !graphData) return;
    const points = [];
    graphData.ticks.forEach((tick) => {
      (tick.strategies || []).forEach((row, index) => {
        if (!selected.has(row.strategy_id) || ![-1, 0, 1].includes(row.direction)) return;
        points.push({
          time: tick.time,
          position: row.direction > 0 ? "aboveBar" : row.direction < 0 ? "belowBar" : "inBar",
          color: palette[index % palette.length],
          shape: row.direction > 0 ? "arrowUp" : row.direction < 0 ? "arrowDown" : "circle",
          text: `${shortNames[row.strategy_id] || row.strategy_id} ${directionMark(row.direction)}`,
          size: 1,
        });
      });
      const total = tick.aggregate?.signal;
      if (selected.has("__aggregate__") && total) {
        const direction = total.includes("Buy") ? 1 : total.includes("Sell") ? -1 : total === "Flat" ? 0 : null;
        if (direction !== null) points.push({
          time: tick.time,
          position: direction > 0 ? "aboveBar" : direction < 0 ? "belowBar" : "inBar",
          color: "#102f52",
          shape: "square",
          text: `ALL ${directionMark(direction)}`,
          size: 2,
        });
      }
    });
    points.sort((left, right) => left.time - right.time);
    markers.setMarkers(points);
  }

  async function render(graph) {
    if (!setStatus(graph)) {
      graphData = null;
      if (priceSeries) priceSeries.setData([]);
      if (markers) markers.setMarkers([]);
      text("oracle-shape-summary", "No completed Oracle graph tick is recorded.");
      byId("oracle-shape-fields").replaceChildren();
      byId("oracle-chart-rows").replaceChildren();
      return;
    }
    const ticks = graph.ticks;
    if (ticks.some((tick) => !Number.isSafeInteger(tick.time) || !Number.isFinite(tick.price) || tick.price <= 0)
      || ticks.some((tick, index) => index > 0 && tick.time <= ticks[index - 1].time)) {
      text("oracle-chart-status", "Graph history has an invalid or out-of-order tick. No chart is shown.");
      graphData = null;
      signature = "";
      if (priceSeries) priceSeries.setData([]);
      if (markers) markers.setMarkers([]);
      return;
    }
    await ensureChart();
    graphData = graph;
    createLegend(ticks.at(-1).strategies || []);
    const key = `${ticks[0].tick_id}:${ticks.at(-1).tick_id}:${ticks.length}:${[...selected].sort().join(",")}`;
    updateShape(ticks.at(-1));
    renderLatestRows(ticks.at(-1));
    if (key === signature) return;
    signature = key;
    const range = chart.timeScale().getVisibleLogicalRange();
    priceSeries.setData(ticks.map((tick) => ({ time: tick.time, value: tick.price })));
    drawMarkers();
    if (range) chart.timeScale().setVisibleLogicalRange(range);
    else chart.timeScale().fitContent();
  }

  window.OracleChart = { render };
})();
