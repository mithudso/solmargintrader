"use strict";

// Owner content is data: every dynamic string enters the DOM through textContent.
const $ = (id) => document.getElementById(id);
const state = { status: null, registrations: null, telemetry: null, selected: null,
  cursors: [""], page: 0, next: null, polling: false, eventCursor: 0,
  events: [], droppedEvents: 0, receivedAt: null };
const terminal = ["completed", "partial", "missing", "unsupported", "failed"];
const finite = (value) => typeof value === "number" && Number.isFinite(value);
const label = (value) => value === null || value === undefined || value === "" ? "Unavailable" : String(value);
const human = (value) => label(value).replaceAll("_", " ");
const money = (value) => finite(value) ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value) : "Unavailable";
function text(id, value) { $(id).textContent = label(value); }
function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value !== undefined) element.textContent = label(value);
  if (className) element.className = className;
  return element;
}
function timestamp(value) {
  if (value === null || value === undefined || value === "") return "Unavailable";
  const date = new Date(typeof value === "number" ? value * 1000 : value);
  return Number.isFinite(date.getTime()) ? date.toISOString().replace("T", " ").replace(".000Z", " UTC") : "Unavailable";
}
function fields(id, entries) {
  const fragment = document.createDocumentFragment();
  entries.forEach(([key, value]) => {
    const group = node("div");
    group.append(node("dt", key), node("dd", value));
    fragment.append(group);
  });
  $(id).replaceChildren(fragment);
}
function metric(bot, key) { return bot?.financials?.[key]?.value; }
function botPnl(bot) {
  const realized = metric(bot, "realized_net_pnl_usd");
  const unrealized = metric(bot, "unrealized_net_pnl_usd");
  return finite(realized) && finite(unrealized) ? realized + unrealized : null;
}
function managerBot(id) { return state.telemetry?.manager?.bots?.find((row) => row.bot_id === id); }
function aggregate(metricReader) {
  const manager = state.telemetry?.manager;
  const bots = manager?.bots;
  if (manager?.status !== "available" || manager?.truncated || !Array.isArray(bots) || !bots.length || bots.some((row) => row.mode !== "paper")) return null;
  const values = bots.map(metricReader);
  return values.every(finite) ? values.reduce((sum, value) => sum + value, 0) : null;
}
async function get(path) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(path, { cache: "no-store", credentials: "same-origin", signal: controller.signal });
    const envelope = await response.json();
    if (!response.ok || envelope.schema_version !== 1 || !envelope.ok) throw new Error("owner_unavailable");
    return envelope.data;
  } finally { clearTimeout(timer); }
}
async function telemetryPage() {
  let latest = null;
  // Drain four pages per tick, then resume the cursor next tick. Never repeat
  // page zero indefinitely or silently label a bounded window as all history.
  for (let page = 0; page < 4; page += 1) {
    latest = await get(`/api/telemetry?after=${state.eventCursor}&limit=100`);
    const events = Array.isArray(latest.events) ? latest.events : [];
    const fresh = events.filter((event) => Number.isSafeInteger(event.sequence) && event.sequence > state.eventCursor);
    state.events.push(...fresh);
    if (state.events.length > 100) {
      state.droppedEvents += state.events.length - 100;
      state.events = state.events.slice(-100);
    }
    const next = latest.next_after;
    if (!Number.isSafeInteger(next) || next < state.eventCursor) throw new Error("invalid_event_cursor");
    const advanced = next > state.eventCursor;
    state.eventCursor = next;
    if (!latest.has_more || !advanced) break;
  }
  return latest;
}
async function refresh() {
  if (state.polling) return;
  state.polling = true;
  $("refresh").disabled = true;
  const cursor = state.cursors[state.page];
  const results = await Promise.allSettled([
    get("/api/status"),
    get(`/api/registrations?limit=100${cursor ? `&after=${encodeURIComponent(cursor)}` : ""}`),
    telemetryPage(),
  ]);
  ["status", "registrations", "telemetry"].forEach((key, index) => {
    state[key] = results[index].status === "fulfilled" ? results[index].value : null;
  });
  state.receivedAt = Date.now();
  render();
  const unavailable = results.filter((result) => result.status === "rejected").length;
  text("connection-state", unavailable ? `${unavailable} owner interface${unavailable === 1 ? " is" : "s are"} unavailable · stale values withheld` : "Connected to local owners · refreshing every 2 seconds");
  text("last-refresh", `Observed ${new Date(state.receivedAt).toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC")}`);
  state.polling = false;
  $("refresh").disabled = false;
}
function renderSummary() {
  const registrations = state.registrations;
  const batch = state.status?.batch;
  const counts = batch?.counts || {};
  const total = batch?.total;
  const finished = terminal.reduce((sum, key) => sum + (finite(counts[key]) ? counts[key] : 0), 0);
  text("paper-capital", money(aggregate((bot) => bot.configured_virtual_capital?.value)));
  text("capital-note", "Configured virtual capital · not reserved funds");
  text("paper-pnl", money(aggregate(botPnl)));
  text("pnl-note", "Bot Manager paper results · all metrics required");
  text("backtest-coverage", finite(total) && total > 0 ? `${finished} / ${total}` : "Unavailable");
  text("backtest-note", finite(total) ? `${(counts.completed || 0) + (counts.partial || 0)} with selected evidence · ${(counts.missing || 0) + (counts.unsupported || 0) + (counts.failed || 0)} blocked` : "No frozen matrix evidence");
  text("fleet-summary", registrations?.status === "available" ? registrations.total : "Unavailable");
  const observed = state.status?.registration?.observed_states;
  text("fleet-note", observed ? Object.entries(observed).map(([key, value]) => `${value} ${human(key)}`).join(" · ") : "Registration is not proof of a running worker");
  text("nav-count", registrations?.status === "available" ? registrations.total : "—");
  text("telemetry-status", human(state.telemetry?.manager?.status));
  text("equity-reason", state.telemetry?.manager?.truncated ? "Bot Manager's bounded status is incomplete; portfolio totals are withheld." : "No measured equity series is exposed by this owner interface. Forecast hits do not establish trading P&L.");
  text("pipeline-title", `Pipeline: ${human(state.status?.phase)}`);
  text("pipeline-detail", state.status ? `Supervisor ${state.status.supervisor_running ? "lock observed" : "not running"} · Backtester ${batch ? (batch.running ? "running" : "not running") : "unavailable"} · Last heartbeat ${timestamp(state.status.heartbeat_at)}` : "Owner state unavailable. Process health and data freshness have not been established.");
  text("footer-time", `Owner heartbeat ${timestamp(state.status?.heartbeat_at)}`);
}
function renderFleet() {
  const registrations = state.registrations;
  const bots = registrations?.status === "available" && Array.isArray(registrations.bots) ? registrations.bots : [];
  const query = $("bot-search").value.trim().toLowerCase();
  const filter = $("status-filter").value;
  const visible = bots.filter((bot) => (!query || `${bot.display_name} ${bot.asset} ${bot.strategy_id}`.toLowerCase().includes(query)) && (filter === "all" || (filter === "blocked" ? bot.observed_state === "blocked" || bot.registration_observation_stale : bot.lifecycle === filter)));
  const fragment = document.createDocumentFragment();
  visible.forEach((bot) => {
    const row = node("tr");
    row.dataset.botId = bot.bot_id;
    if (bot.bot_id === state.selected) row.className = "selected";
    const nameCell = node("td");
    const button = node("button", undefined, "bot-row-name");
    button.type = "button";
    const identity = node("span");
    identity.append(node("strong", `${bot.asset} · ${bot.strategy_id}`), node("small", `${bot.asset}/${bot.quote_currency} · ${bot.interval} · ${bot.preset_horizon}`));
    button.append(identity);
    button.addEventListener("click", () => { state.selected = bot.bot_id; renderFleet(); renderInspector(); });
    nameCell.append(button);
    const statusCell = node("td");
    statusCell.append(node("span", bot.registration_observation_stale ? "Stale registration" : human(bot.observed_state), "status"), node("small", human(bot.reason)));
    const pnl = node("td", money(botPnl(managerBot(bot.bot_id))), "pnl-cell");
    pnl.append(node("small", "Owner-measured only"));
    const evidence = node("td", bot.forward?.calls === null ? "No forward evidence" : `${label(bot.forward?.calls)} forecasts`, "decision-cell");
    evidence.append(node("small", timestamp(bot.forward?.last_issued)));
    row.append(nameCell, statusCell, pnl, evidence);
    fragment.append(row);
  });
  // Keep focused roster controls and the selected identity across live refreshes.
  const active = document.activeElement;
  const focusedBot = active?.closest("tr")?.querySelector("button") === active ? active.closest("tr").dataset.botId : null;
  $("bot-rows").replaceChildren(fragment);
  if (focusedBot) Array.from($("bot-rows").rows).find((row) => row.dataset.botId === focusedBot)?.querySelector("button")?.focus();
  $("empty-results").hidden = visible.length > 0;
  text("empty-results", registrations?.status !== "available" ? `Registrations unavailable: ${human(registrations?.reason)}` : bots.length ? "No bots match on this page. Clear the filter or choose another page." : "No bots are registered for this run.");
  text("bot-count", registrations?.status === "available" ? registrations.total : "—");
  text("page-description", registrations?.status === "available" ? `Page ${state.page + 1} · ${visible.length} shown / ${bots.length} on page · ${registrations.total} total registrations` : "Registration owner unavailable");
  state.next = registrations?.next_after || null;
  $("previous-page").disabled = state.page === 0;
  $("next-page").disabled = !state.next;
}
function renderInspector() {
  const bot = state.registrations?.bots?.find((row) => row.bot_id === state.selected);
  text("selected-name", bot ? `${bot.asset} · ${bot.strategy_id}` : "Choose a bot");
  text("selected-subtitle", bot ? `${bot.asset}/${bot.quote_currency} · ${bot.interval} · ${bot.preset_horizon} · ${bot.owner}` : "Its owner evidence will appear here.");
  text("selected-status", bot?.registration_observation_stale ? "Stale registration" : human(bot?.observed_state));
  text("selected-version", bot ? `Cell ${bot.cell_id}` : "No selection");
  text("selected-decision", human(bot?.observed_state));
  text("selected-reason", human(bot?.reason));
  text("selected-heartbeat", `Observed ${timestamp(bot?.observed_at)}`);
  const manager = managerBot(bot?.bot_id);
  fields("overview-fields", [
    ["Lifecycle", human(bot?.lifecycle)], ["Worker liveness", bot?.runtime_running === true ? "Running" : bot?.runtime_running === false ? "Not running" : human(bot?.runtime_reason)],
    ["Net paper P&L", money(botPnl(manager))], ["Allocated capital", money(metric(manager, "allocated_capital_usd"))],
    ["Live readiness", bot?.live_ready === true ? "Owner reports ready" : "Not established"], ["Bot ID", bot?.bot_id],
  ]);
  const forward = bot?.forward;
  fields("evidence-fields", [
    ["Backtest state", human(bot?.backtest?.state)], ["Selected score", bot?.backtest?.score],
    ["Independent validation", bot?.backtest?.selection_is_independent_validation ? "Established by owner" : "Not established"],
    ["Forward calls / resolved", forward ? `${label(forward.calls)} / ${label(forward.resolved)}` : "Unavailable"],
    ["Resolved directional hit rate", finite(forward?.accuracy_percent) ? `${forward.accuracy_percent.toFixed(2)}% · not profit probability` : "Insufficient resolved evidence"],
    ["Configuration SHA-256", bot?.backtest?.configuration_hash], ["Strategy version", bot?.strategy_version], ["Batch ID", bot?.batch_id],
  ]);
  text("configuration", bot ? JSON.stringify({ strategy: bot.strategy_id, version: bot.strategy_version, asset: bot.asset, quote: bot.quote_currency, interval: bot.interval, horizon: bot.preset_horizon, selected_configuration: bot.backtest?.selected_configuration, mode: bot.mode, armed: bot.armed }, null, 2) : "No configuration selected.");
}
function renderOracle() {
  const entries = Object.entries(state.status?.oracle || {});
  const age = finite(state.status?.heartbeat_at) ? Date.now() / 1000 - state.status.heartbeat_at : null;
  const ownerFresh = state.status?.supervisor_running === true && finite(age) && age >= 0 && age <= 30;
  const fragment = document.createDocumentFragment();
  entries.forEach(([asset, observation]) => {
    const row = node("tr");
    const now = Date.now() / 1000;
    const marketFresh = ownerFresh && finite(observation.observed_at) && observation.observed_at <= now && now - observation.observed_at <= 15;
    const predictionFresh = marketFresh && finite(observation.expires_at) && observation.expires_at > now && finite(observation.as_of) && observation.as_of <= now;
    const signal = predictionFresh && observation.signal && observation.prediction === "available" ? (typeof observation.signal === "string" ? observation.signal : JSON.stringify(observation.signal)) : human(!ownerFresh ? "owner_observation_stale_or_disconnected" : !marketFresh ? "market_observation_stale_or_missing" : observation.reason || "prediction_expired_or_unavailable");
    const marketCell = node("td", marketFresh ? human(observation.market) : "Unavailable · stale or missing");
    marketCell.append(node("small", marketFresh && finite(observation.price) ? `${money(observation.price)} · ${human(observation.kind)}` : "No fresh reference price"), node("small", `Observed ${timestamp(observation.observed_at)}`), node("small", observation.source));
    marketCell.append(node("small", (Array.isArray(observation.limitations) ? observation.limitations : []).map(human).join(" · ") || "Reference snapshot; no execution quote"));
    const predictionCell = node("td", predictionFresh ? human(observation.prediction) : "Unavailable");
    predictionCell.append(node("small", `${label(observation.horizon_seconds)} second horizon · expires ${timestamp(observation.expires_at)}`));
    const signalCell = node("td", signal);
    if (predictionFresh && observation.prediction === "available") {
      signalCell.append(node("small", finite(observation.balance_percent) ? `${observation.balance_percent.toFixed(2)}% directional vote balance` : "Vote balance unavailable"), node("small", observation.percentage_semantics), node("small", `${observation.included?.length || 0} contributing · ${observation.excluded?.length || 0} excluded`));
    }
    row.append(node("td", observation.instrument || asset), marketCell, predictionCell, signalCell);
    fragment.append(row);
  });
  $("oracle-rows").replaceChildren(fragment);
  $("oracle-empty").hidden = entries.length > 0;
}
function renderEvidence() {
  const acquisitions = Object.entries(state.status?.acquisitions || {});
  const accepted = acquisitions.filter(([, receipt]) => receipt.status === "complete").length;
  text("acquisition-summary", acquisitions.length ? `${accepted} accepted / ${acquisitions.length} attempted inputs. Only fully validated files enter the frozen batch.` : "No acquisition receipt received.");
  fields("acquisition-fields", [["Venue / quote", state.status?.config ? `${state.status.config.market_venue} / ${state.status.config.quote}` : "Unavailable"], ["Start (inclusive)", state.status?.config?.start], ["End (exclusive)", state.status?.config?.end]]);
  const batch = state.status?.batch;
  text("matrix-summary", batch ? `${batch.total} frozen cells · ${human(batch.phase)}. Forward observation waits until every historical cell is terminal.` : "No frozen batch received.");
  fields("matrix-fields", [["Batch ID", state.status?.batch_id], ...Object.entries(batch?.counts || {}).map(([key, value]) => [human(key), value])]);
  const fragment = document.createDocumentFragment();
  acquisitions.forEach(([key, receipt]) => {
    const row = node("tr");
    const provenance = receipt.source ? `${receipt.source} · SHA-256 ${label(receipt.sha256)}` : "No accepted source receipt";
    row.append(node("td", key), node("td", human(receipt.status)), node("td", receipt.reason ? human(receipt.reason) : `${label(receipt.coverage?.bars)} complete bars · ${timestamp(receipt.coverage?.first_ts)} to ${timestamp(receipt.coverage?.last_ts)}`), node("td", provenance));
    fragment.append(row);
  });
  (batch?.problems || []).forEach((problem) => {
    const row = node("tr");
    row.append(node("td", `${problem.asset} · ${problem.strategy} · ${problem.interval} · ${problem.horizon}`), node("td", human(problem.state)), node("td", human(problem.reason)), node("td", `Batch ${label(state.status?.batch_id)}`));
    fragment.append(row);
  });
  $("problem-rows").replaceChildren(fragment);
  $("problem-empty").hidden = fragment.childNodes.length > 0 || acquisitions.length > 0 || Boolean(batch?.problems?.length);
  if (batch?.problems_truncated) { $("problem-empty").hidden = false; text("problem-empty", "Blocker list is bounded. Inspect the batch owner's full cell evidence for the remaining rows."); }
}
function renderOwners() {
  const status = state.status;
  text("owner-phase", human(status?.phase));
  fields("owner-fields", [
    ["Run ID", status?.run_id], ["Phase", human(status?.phase)],
    ["Supervisor lock", status ? status.supervisor_running ? "Observed held" : "Not held" : "Unavailable"],
    ["Heartbeat", timestamp(status?.heartbeat_at)], ["Current work", typeof status?.current === "object" ? JSON.stringify(status.current) : status?.current],
    ["Backtester owner", status?.batch ? `soltui.f5_batch · ${status.batch.running ? "running" : "not running"}` : "Unavailable"],
    ["Recorder owner", status?.recorder ? (status.recorder.running ? "Running" : human(status.recorder.reason || "not_running")) : "Unavailable"],
    ["Bot Manager status", human(state.telemetry?.manager?.status)], ["Telemetry mirror", human(state.telemetry?.status)],
    ["Last event mirror sync", timestamp(state.telemetry?.last_sync)], ["Log files", state.telemetry?.logs?.status ? `${human(state.telemetry.logs.status)} · metadata only; no raw content` : "Unavailable"],
  ]);
  const fragment = document.createDocumentFragment();
  [...state.events].reverse().forEach((event) => {
    const row = node("li");
    const body = node("div");
    body.append(node("strong", human(event.kind)), node("p", `Bot ${label(event.bot_id)} · source sequence ${label(event.source_sequence)}`));
    row.append(node("time", timestamp(event.occurred_at)), node("span", undefined, "event-dot neutral-dot"), body, node("span", event.source, "actor"));
    fragment.append(row);
  });
  $("event-list").replaceChildren(fragment);
  $("events-empty").hidden = state.events.length > 0;
  text("events-note", `Latest ${state.events.length} observed events · ${state.droppedEvents} older rows omitted from this window · cursor ${state.eventCursor}${state.telemetry?.has_more ? " · catching up" : ""}${state.telemetry === null ? " · owner currently unavailable" : ""}`);
}
function render() { renderSummary(); renderFleet(); renderInspector(); renderOracle(); renderEvidence(); renderOwners(); }
function navigate() {
  const view = ["fleet", "oracle", "evidence", "activity"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "fleet";
  document.querySelectorAll("[data-view]").forEach((element) => { element.hidden = element.dataset.view !== view; });
  document.querySelectorAll("[data-nav]").forEach((element) => {
    if (element.dataset.nav === view) element.setAttribute("aria-current", "page"); else element.removeAttribute("aria-current");
  });
  text("crumb", { fleet: "Bot fleet", oracle: "Oracle", evidence: "Research & evidence", activity: "Owner status" }[view]);
}
function tab(name, focus = false) {
  document.querySelectorAll("[data-tab]").forEach((element) => {
    const selected = element.dataset.tab === name;
    element.setAttribute("aria-selected", String(selected)); element.tabIndex = selected ? 0 : -1;
    $(`detail-${element.dataset.tab}`).hidden = !selected;
    if (selected && focus) element.focus();
  });
}
document.querySelectorAll("[data-tab]").forEach((element) => {
  element.addEventListener("click", () => tab(element.dataset.tab));
  element.addEventListener("keydown", (event) => {
    const tabs = ["overview", "evidence", "config"];
    let next = tabs.indexOf(element.dataset.tab);
    if (event.key === "ArrowRight") next = (next + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (next + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault(); tab(tabs[next], true);
  });
});
$("refresh").addEventListener("click", refresh);
$("bot-search").addEventListener("input", renderFleet);
$("status-filter").addEventListener("change", renderFleet);
$("next-page").addEventListener("click", () => { if (!state.next || state.polling) return; state.cursors = state.cursors.slice(0, state.page + 1); state.cursors.push(state.next); state.page += 1; refresh(); });
$("previous-page").addEventListener("click", () => { if (state.page < 1 || state.polling) return; state.page -= 1; refresh(); });
window.addEventListener("hashchange", navigate);
navigate(); refresh(); setInterval(refresh, 2000);
