"use strict";

// Owner content is data: every dynamic string enters the DOM through textContent.
const $ = (id) => document.getElementById(id);
const state = { status: null, registrations: null, telemetry: null, selected: null,
  cursors: [""], page: 0, next: null, polling: false, eventCursor: 0,
  events: [], droppedEvents: 0, receivedAt: null, control: null, analytics: null,
  oracle: null, oracleInstrument: "SOL/USD", selectedRecord: null, session: null,
  busy: new Set(), localActions: new Map(), voterDrafts: new Map(), managerDrafts: new Map(), pendingPrefs: new Map(),
  wikiCatalog: null, wikiPage: null, wikiKnownPages: new Map(), wikiRequest: 0, wikiPageRequest: 0,
  launchCatalogKey: null, managerCatalogKey: null, instrumentCatalogKey: null,
  formInitialized: false, recordingDirty: false, feedbackTimer: null, swap: null, swapLoaded: false, activeRun: "" };
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
function replaceWithFocus(id, content) {
  const key = document.activeElement?.dataset?.controlKey;
  $(id).replaceChildren(content);
  if (key) Array.from($(id).querySelectorAll("[data-control-key]")).find((element) => element.dataset.controlKey === key && !element.disabled)?.focus({ preventScroll: true });
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
  const requestedRun = state.activeRun;
  const requestedInstrument = state.oracleInstrument;
  try {
    const cursor = state.cursors[state.page];
    const requests = [
      ["status", get(scoped("/api/status"))],
      ["registrations", get(scoped(`/api/registrations?limit=100${cursor ? `&after=${encodeURIComponent(cursor)}` : ""}`))],
      ["telemetry", telemetryPage()],
      ["control", get(scoped("/api/control"))],
      ["oracle", get(scoped(`/api/oracle?instrument=${encodeURIComponent(state.oracleInstrument)}`))],
      ["analytics", state.selected ? get(scoped(`/api/analytics?bot_id=${encodeURIComponent(state.selected)}`)) : Promise.resolve(null)],
    ];
    const results = await Promise.allSettled(requests.map(([, promise]) => promise));
    if (requestedRun !== state.activeRun) return;
    requests.forEach(([key], index) => { state[key] = key === "oracle" && requestedInstrument !== state.oracleInstrument ? null : results[index].status === "fulfilled" ? results[index].value : null; });
    state.receivedAt = Date.now();
    render();
    const unavailable = results.filter((result) => result.status === "rejected").length;
    text("connection-state", unavailable ? `${unavailable} owner interface${unavailable === 1 ? " is" : "s are"} unavailable · stale values withheld` : "Connected to local owners · refreshing every 2 seconds");
    text("last-refresh", `Observed ${new Date(state.receivedAt).toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC")}`);
  } catch {
    text("connection-state", "Owner response could not be rendered · refresh to recover");
  } finally {
    state.polling = false;
    $("refresh").disabled = false;
    if (requestedRun !== state.activeRun || requestedInstrument !== state.oracleInstrument) queueMicrotask(refresh);
  }
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
    button.addEventListener("click", () => selectBot(bot));
    nameCell.append(button);
    const statusCell = node("td");
    statusCell.append(node("span", bot.registration_observation_stale ? "Stale registration" : human(bot.observed_state), "status"), node("small", human(bot.reason)));
    const measured = state.analytics?.coins?.find((row) => row.bot_id === bot.bot_id);
    const measuredPnl = forwardPnl(measured?.forward);
    const ownerPnl = botPnl(managerBot(bot.bot_id));
    const pnl = node("td", money(finite(measuredPnl) ? measuredPnl : ownerPnl), "pnl-cell");
    pnl.append(node("small", measured ? "Recorded forward paper result" : finite(ownerPnl) ? "Bot Manager measured result" : "Select to inspect forward P&L"));
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
  const bot = state.registrations?.bots?.find((row) => row.bot_id === state.selected) || state.selectedRecord;
  text("selected-name", bot ? bot.asset ? `${bot.asset} · ${bot.strategy_id}` : bot.display_name || human(bot.strategy_id) : "Choose a bot");
  text("selected-subtitle", bot ? bot.asset ? `${bot.asset}/${bot.quote_currency} · ${bot.interval} · ${bot.preset_horizon} · ${bot.owner}` : `${human(bot.strategy_id)} · revision ${label(bot.config_revision)} · ${label(bot.owner)}` : "Its owner evidence will appear here.");
  text("selected-status", bot?.registration_observation_stale ? "Stale registration" : human(bot?.observed_state));
  text("selected-version", bot ? bot.cell_id ? `Cell ${bot.cell_id}` : `Revision ${label(bot.config_revision)}` : "No selection");
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
  text("configuration", bot?.resolved_values ? JSON.stringify({ saved_revision: bot.config_revision, config_hash: bot.config_hash, values: bot.resolved_values, provenance: bot.provenance }, null, 2) : bot ? JSON.stringify({ strategy: bot.strategy_id, version: bot.strategy_version, asset: bot.asset, quote: bot.quote_currency, interval: bot.interval, horizon: bot.preset_horizon, selected_configuration: bot.backtest?.selected_configuration, mode: bot.mode, armed: bot.armed }, null, 2) : "No configuration selected.");
}
function renderOracle() {
  const entries = Object.entries(state.status?.oracle || {});
  const age = finite(state.status?.heartbeat_at) ? Date.now() / 1000 - state.status.heartbeat_at : null;
  const ownerFresh = state.status?.supervisor_running === true && finite(age) && age >= 0 && age <= 30;
  const fragment = document.createDocumentFragment();
  entries.forEach(([asset, observation]) => {
    const row = node("tr"); const now = Date.now() / 1000;
    const marketFresh = ownerFresh && observation.market === "available" && finite(observation.observed_at) && observation.observed_at <= now && now - observation.observed_at <= 15;
    const selected = observation.instrument === state.oracleInstrument;
    const view = selected ? state.oracle : null;
    const expiry = view?.aggregate?.expires_at ?? view?.aggregate?.expiry;
    const freshView = view?.instrument === state.oracleInstrument && marketFresh && view?.status === "available" && view?.market?.status === "available" && finite(expiry) && expiry > now && finite(view?.as_of) && view.as_of <= now && now - view.as_of <= 30;
    const marketCell = node("td", marketFresh ? human(observation.market) : "Unavailable · stale or missing");
    marketCell.append(node("small", marketFresh && finite(observation.price) ? `${money(observation.price)} · ${human(observation.kind)}` : "No fresh reference price"), node("small", `Observed ${timestamp(observation.observed_at)}`), node("small", observation.source));
    marketCell.append(node("small", (Array.isArray(observation.limitations) ? observation.limitations : []).map(human).join(" · ") || "Reference snapshot; no execution quote"));
    const predictionCell = node("td", selected ? freshView ? "Available" : "Unavailable" : "Choose this instrument");
    if (selected) predictionCell.append(node("small", `${label(view?.horizon_seconds)} second horizon · expires ${timestamp(expiry)}`));
    const signalCell = node("td", selected ? freshView ? view.signal : human(view?.aggregate?.reason || view?.market?.reason || "selected_vote_unavailable") : "Selected-voter view not requested");
    if (freshView) signalCell.append(node("small", finite(view.aggregate.balance_percent) ? `${view.aggregate.balance_percent.toFixed(2)}% signed vote balance` : "Vote balance unavailable"), node("small", `${array(view.aggregate.included).length} contributing · ${array(view.aggregate.excluded).length} excluded`));
    if (!selected) {
      const inspect = node("button", "Inspect voters", "button quiet small"); inspect.type = "button"; inspect.dataset.controlKey = `oracle-inspect:${state.activeRun}:${observation.instrument}`;
      inspect.addEventListener("click", () => setInstrument(observation.instrument)); signalCell.append(inspect);
    }
    row.append(node("td", observation.instrument || asset), marketCell, predictionCell, signalCell); fragment.append(row);
  });
  replaceWithFocus("oracle-rows", fragment); $("oracle-empty").hidden = entries.length > 0;
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
function render() { renderSummary(); renderFleet(); renderInspector(); renderOracle(); renderEvidence(); renderOwners(); renderControl(); renderAnalytics(); renderSelectedAggregate(); }
function navigate() {
  const requested = location.hash.slice(1).split("/")[0];
  const view = ["fleet", "launch", "oracle", "evidence", "activity", "swap", "wiki"].includes(requested) ? requested : "fleet";
  document.querySelectorAll("[data-view]").forEach((element) => { element.hidden = element.dataset.view !== view; });
  document.querySelectorAll("[data-nav]").forEach((element) => {
    if (element.dataset.nav === view) element.setAttribute("aria-current", "page"); else element.removeAttribute("aria-current");
  });
  text("crumb", { fleet: "Bot fleet", launch: "Launch a bot", oracle: "Oracle", evidence: "Research & evidence", activity: "Servers & activity", swap: "Manual wallet swap", wiki: "Ecosystem wiki" }[view]);
  text("footer-scope", view === "swap" ? "Manual swap · wallet approval required" : "Paper controls · no automated orders");
  if (view === "swap" && !state.swap) loadSwapState();
  if (view === "wiki") {
    if (!state.wikiCatalog) loadWikiCatalog($("wiki-search").value);
    const id = location.hash.slice(1).split("/").slice(1).join("/");
    if (id && state.wikiPage?.id !== id) loadWikiPage(id);
  }
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

// The operational plane has a finite action registry. A nonce lives only in
// memory; no credential is written to the DOM, URL, console or browser storage.
function announce(message) {
  clearTimeout(state.feedbackTimer);
  text("action-feedback", message);
  $("action-feedback").hidden = false;
  state.feedbackTimer = setTimeout(() => { $("action-feedback").hidden = true; }, 14000);
}
function actionKey(action, params) { return `${params.run_id || state.activeRun || "primary"}:${action}:${params.identity || params.instrument || "owner"}`; }
function voterKey(instrument = state.oracleInstrument, run = state.activeRun) { return `${run || "primary"}:${instrument}`; }
function preferencePending(kind, instrument = null) { return Array.from(state.pendingPrefs.values()).some((item) => item.kind === kind && item.run === state.activeRun && (!instrument || item.instrument === instrument)); }
function array(value) { return Array.isArray(value) ? value : []; }
function currentCapabilities() { return array(state.control?.servers).flatMap((server) => array(server.actions)); }
async function submitAction(action, params = {}, button = null) {
  const key = actionKey(action, params);
  const requestedRun = action === "research.launch" ? "" : typeof params.run_id === "string" ? params.run_id : state.activeRun;
  if (state.busy.has(key)) return null;
  state.busy.add(key);
  const requestId = crypto.randomUUID();
  const requested = Date.now() / 1000;
  if (button) { button.disabled = true; button.setAttribute("aria-busy", "true"); }
  let sent = false;
  try {
    if (!state.session?.csrf_nonce) state.session = await get("/api/session");
    if (typeof state.session?.csrf_nonce !== "string" || !state.session.csrf_nonce) throw new Error("control_session_unavailable");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    let response;
    try {
      sent = true;
      response = await fetch("/api/actions", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json", "X-Sol-CSRF": state.session.csrf_nonce },
        body: JSON.stringify({ action, request_id: requestId, params: requestedRun && action !== "research.launch" ? { ...params, run_id: requestedRun } : params }), signal: controller.signal,
      });
    } finally { clearTimeout(timeout); }
    const envelope = await response.json();
    if (!response.ok || envelope.schema_version !== 1 || envelope.ok !== true) {
      if (response.status === 403) state.session = null;
      const reason = typeof envelope.error === "string" ? envelope.error : "action_refused";
      announce(`${human(action)} was refused: ${human(reason)}. Inspect the owner state before trying again.`);
      return null;
    }
    const record = envelope.data;
    if (!record || typeof record.id !== "string") throw new Error("invalid_action_receipt");
    state.localActions.set(record.id, record);
    announce(`${human(action)}: ${human(record.state)} for ${requestedRun || "the primary pipeline"}. Action ${record.id}.`);
    renderActionLedger();
    return record;
  } catch {
    const record = { id: requestId, action, state: sent ? "unknown" : "not_sent", created_at: requested,
      error: sent ? "request_outcome_unknown_inspect_durable_receipt" : "control_session_unavailable" };
    state.localActions.set(requestId, record);
    announce(sent ? `The request outcome is unknown. Inspect action ${requestId}; a launch is never retried automatically.` : "The control session is unavailable. Refresh owner state before submitting an action.");
    renderActionLedger();
    return null;
  } finally {
    state.busy.delete(key);
    if (button?.isConnected) { button.removeAttribute("aria-busy"); button.disabled = false; }
    refresh();
  }
}
async function selectBot(bot) {
  state.selected = bot.bot_id;
  state.selectedRecord = bot;
  state.analytics = null;
  renderFleet(); renderInspector(); renderAnalytics();
  try {
    const identity = state.selected;
    const value = await get(scoped(`/api/analytics?bot_id=${encodeURIComponent(identity)}`));
    if (state.selected === identity) { state.analytics = value; renderAnalytics(); renderFleet(); }
  } catch { renderAnalytics(); }
}
function actionButton(action, caption, params = {}, enabled = true, reason = null) {
  const wrap = node("div", undefined, "action-control");
  const button = node("button", caption, "button secondary");
  button.type = "button"; button.dataset.controlKey = JSON.stringify([params.run_id || state.activeRun, action, params]);
  const busy = state.busy.has(actionKey(action, params));
  button.disabled = !enabled || busy;
  if (busy) button.setAttribute("aria-busy", "true");
  button.addEventListener("click", () => submitAction(action, params, button));
  wrap.append(button);
  if (reason) wrap.append(node("p", human(reason)));
  return wrap;
}
function renderStages(target, stages) {
  const fragment = document.createDocumentFragment();
  array(stages).forEach((stage) => {
    const item = node("div", undefined, "stage-item");
    const status = stage.state || stage.status || "unavailable";
    item.dataset.state = status;
    item.append(node("strong", human(stage.label || stage.id)), node("small", human(status)));
    if (finite(stage.total) && stage.total > 0 && finite(stage.done) && stage.done >= 0) {
      const progress = node("progress");
      progress.max = stage.total; progress.value = Math.min(stage.done, stage.total);
      progress.setAttribute("aria-label", `${human(stage.label || stage.id)}: ${stage.done} of ${stage.total}`);
      item.append(progress, node("small", `${stage.done} / ${stage.total}`));
    } else if (["running", "active", "in_progress"].includes(status)) {
      const progress = node("progress");
      progress.setAttribute("aria-label", `${human(stage.label || stage.id)} is running; completion target unavailable`);
      item.append(progress);
    }
    if (stage.detail || stage.reason) item.append(node("small", human(stage.detail || stage.reason)));
    fragment.append(item);
  });
  $(target).replaceChildren(fragment);
}
function fillSelect(id, items, desired = null) {
  const element = $(id);
  const entries = array(items).map((item) => typeof item === "string" ? { id: item, label: item } : item).filter((item) => item && typeof item.id === "string");
  const signature = JSON.stringify(entries.map((item) => [item.id, item.label]));
  if (element.dataset.options === signature) return;
  const selected = element.value || desired;
  const fragment = document.createDocumentFragment();
  entries.forEach((entry) => {
    const option = node("option", entry.label || human(entry.id));
    option.value = entry.id; fragment.append(option);
  });
  if (!entries.length) { const option = node("option", "Unavailable"); option.value = ""; fragment.append(option); }
  element.replaceChildren(fragment); element.dataset.options = signature;
  if (entries.some((item) => item.id === selected)) element.value = selected;
  else if (desired && entries.some((item) => item.id === desired)) element.value = desired;
}
function launchParams() {
  return {
    name: $("launch-name").value.trim(),
    coins: Array.from($("launch-coins").querySelectorAll("input:checked")).map((input) => input.value),
    strategies: [$("launch-strategy").value], intervals: [$("launch-interval").value],
    horizons: [$("launch-horizon").value], start: $("launch-start").value,
    end: $("launch-end").value, capital: Number($("launch-capital").value),
    record_pnl: $("launch-record-pnl").checked,
    swap_provider: $("launch-swap-provider").value,
    cost_model: { fee_bps: Number($("launch-fee-bps").value), referral_fee_bps: Number($("launch-referral-bps").value), slippage_bps: Number($("launch-slippage-bps").value),
      borrow_long_bps_hour: Number($("launch-borrow-long").value), borrow_short_bps_hour: Number($("launch-borrow-short").value), source: "configured_scenario" },
  };
}
function renderLaunchReview() {
  const params = launchParams();
  text("launch-review", `${human(params.strategies[0])} · ${params.coins.length} selected coin${params.coins.length === 1 ? "" : "s"} · ${human(params.intervals[0])} bars · ${human(params.horizons[0])} preset · ${money(params.capital)} per independent trial · P&L recording ${params.record_pnl ? "on" : "off"} · ${human(params.swap_provider)} cost scenario · ${(params.cost_model.fee_bps + params.cost_model.referral_fee_bps).toFixed(2)} bps assumed fee per side including referral`);
  text("launch-preview", JSON.stringify({ ...params, mode: "paper", armed: false,
    selection_semantics: "Requested card preset; the existing owner freezes and evaluates its supported variants." }, null, 2));
}
function renderLaunchCatalog() {
  const catalog = state.control?.catalog;
  fillSelect("launch-strategy", catalog?.strategies, "rsi");
  fillSelect("launch-interval", catalog?.intervals, "1d");
  fillSelect("launch-horizon", catalog?.horizons, "medium");
  const coins = array(catalog?.coins).filter((coin) => typeof coin === "string");
  const signature = JSON.stringify(coins);
  if (state.launchCatalogKey !== signature) {
    const selected = new Set(Array.from($("launch-coins").querySelectorAll("input:checked")).map((input) => input.value));
    const first = state.launchCatalogKey === null;
    const fragment = document.createDocumentFragment();
    coins.forEach((coin, index) => {
      const wrapper = node("label");
      const input = document.createElement("input"); input.type = "checkbox"; input.value = coin;
      input.checked = selected.has(coin) || (first && (coins.includes("SOL") ? coin === "SOL" : index === 0));
      input.addEventListener("change", renderLaunchReview);
      wrapper.append(input, node("span", coin)); fragment.append(wrapper);
    });
    if (!coins.length) fragment.append(node("p", "No asset catalog is available.", "empty"));
    $("launch-coins").replaceChildren(fragment); state.launchCatalogKey = signature;
  }
  if (!state.formInitialized && state.status?.config) {
    $("launch-start").value = state.status.config.start || "2025-01-01";
    $("launch-end").value = new Date().toISOString().slice(0, 10);
    const costs = state.status.config.cost_model;
    if (costs) {
      [["launch-fee-bps", "fee_bps"], ["launch-referral-bps", "referral_fee_bps"], ["launch-slippage-bps", "slippage_bps"], ["launch-borrow-long", "borrow_long_bps_hour"], ["launch-borrow-short", "borrow_short_bps_hour"]].forEach(([id, key]) => { if (finite(costs[key])) $(id).value = costs[key]; });
    }
    if (["jupiter", "reference"].includes(state.status.config.swap_provider)) $("launch-swap-provider").value = state.status.config.swap_provider;
    state.formInitialized = true;
  }
  const launch = currentCapabilities().find((item) => item.action === "research.launch");
  const enabled = Boolean(state.control && catalog && array(catalog.strategies).length && (!launch || launch.enabled));
  $("launch-submit").disabled = !enabled || state.busy.has(actionKey("research.launch", {}));
  text("launch-availability", enabled ? "Launch creates a distinct, attributable paper run. No live orders are available." : human(launch?.reason || "research_launch_unavailable"));
  const managerStrategies = Object.keys(catalog?.manager_schema?.strategies || {});
  fillSelect("manager-new-strategy", managerStrategies);
  $("manager-create-submit").disabled = !state.control || !managerStrategies.length || state.busy.has(actionKey("manager.create", {}));
  renderLaunchReview();
}
function renderRuns() {
  const fragment = document.createDocumentFragment();
  array(state.control?.runs).forEach((run) => {
    const card = node("article", undefined, "run-card");
    const heading = node("div", undefined, "run-card-header");
    const identity = node("div"); identity.append(node("h3", run.name || run.id), node("p", `Run ${label(run.id)} · ${label(run.home)}`));
    const inspect = node("button", "Inspect run", "button secondary small"); inspect.type = "button"; inspect.dataset.controlKey = `run-inspect:${run.id}`;
    inspect.addEventListener("click", () => { setActiveRun(run.id); location.hash = "fleet"; });
    const stateBox = node("div", undefined, "config-actions"); stateBox.append(node("span", human(run.phase), "tag neutral"), inspect);
    heading.append(identity, stateBox); card.append(heading);
    const progress = run.progress;
    if (finite(progress?.total) && progress.total > 0 && finite(progress.done)) {
      const wrapper = node("div", undefined, "run-progress"); const bar = node("progress");
      bar.max = progress.total; bar.value = Math.min(progress.done, progress.total);
      bar.setAttribute("aria-label", `${run.name || run.id} historical progress`);
      wrapper.append(bar, node("span", `${progress.done} / ${progress.total} historical cells`)); card.append(wrapper);
    }
    const stages = node("div", undefined, "stage-track");
    array(run.stages).forEach((stage) => {
      const block = node("div", undefined, "stage-item"); block.dataset.state = stage.state || "unavailable";
      block.append(node("strong", human(stage.label || stage.id)), node("small", human(stage.state)), node("small", stage.reason || (finite(stage.total) ? `${label(stage.done)} / ${stage.total}` : "No fixed completion target")));
      if (finite(stage.total) && stage.total > 0 && finite(stage.done)) {
        const bar = node("progress"); bar.max = stage.total; bar.value = Math.min(stage.done, stage.total);
        bar.setAttribute("aria-label", `${human(stage.id)}: ${stage.done} of ${stage.total}`); block.append(bar);
      } else if (["running", "acquiring", "backtesting"].includes(stage.state)) {
        const bar = node("progress"); bar.setAttribute("aria-label", `${human(stage.id)} is running; completion target unavailable`); block.append(bar);
      }
      if (stage.id === "forward") block.append(node("small", "Initial call coverage; outcome collection continues."));
      stages.append(block);
    });
    card.append(stages);
    const actions = node("div", undefined, "config-actions");
    const ownerActions = Array.isArray(run.actions) ? run.actions : [
      { action: "pipeline.start", label: "Start run", enabled: run.running === false && run.phase !== "unavailable", reason: run.running ? "Already running" : "Resume this saved paper run" },
      { action: "pipeline.stop", label: "Stop run", enabled: run.running === true, reason: "Cooperative stop; retains this run's archives" },
      { action: "pipeline.restart", label: "Restart run", enabled: run.running === true, reason: "Restart this saved paper run without creating a new identity" },
    ];
    ownerActions.forEach((action) => { actions.append(actionButton(action.action, action.label, { ...action.params, run_id: run.id }, action.enabled === true, action.reason)); });
    if (actions.childNodes.length) card.append(actions);
    fragment.append(card);
  });
  if (!fragment.childNodes.length) fragment.append(node("p", state.control ? "No additional run has been launched from this control room." : "Research run inventory is unavailable.", "empty"));
  replaceWithFocus("research-runs", fragment);
}
function managerStatuses() {
  const value = state.control?.statuses;
  return Array.isArray(value) ? value : array(value?.bots);
}
function renderManagerConfigs() {
  // A polling refresh must not erase a settings delta while its author types.
  if (document.activeElement?.matches("#manager-configs textarea")) return;
  const fragment = document.createDocumentFragment();
  array(state.control?.configs).forEach((config) => {
    const observed = managerStatuses().find((item) => item.bot_id === config.bot_id);
    const card = node("article", undefined, "config-card"); card.dataset.managerBot = config.bot_id;
    const heading = node("div", undefined, "config-card-header"); const identity = node("div");
    identity.append(node("h3", config.display_name), node("p", `${human(config.strategy_id)} · saved revision ${label(config.config_revision)} · ${human(observed?.observed_state)}`));
    const inspect = node("button", "Inspect configuration", "button secondary small"); inspect.type = "button"; inspect.dataset.controlKey = `manager-inspect:${config.bot_id}`;
    inspect.addEventListener("click", () => {
      state.selected = config.bot_id;
      state.selectedRecord = { ...config, lifecycle: observed?.lifecycle, observed_state: observed?.observed_state, reason: observed?.reason };
      state.analytics = null; location.hash = "fleet"; renderInspector(); renderAnalytics();
    });
    heading.append(identity, inspect); card.append(heading);
    const details = node("details"); details.append(node("summary", "Saved settings and explicit edit delta"));
    const settings = node("pre", JSON.stringify(config.resolved_values, null, 2), "safe-json");
    const caption = node("label", "Settings delta (JSON)", "subtle");
    const textarea = node("textarea"); textarea.spellcheck = false; textarea.id = `manager-edit-${config.bot_id}`; caption.htmlFor = textarea.id;
    textarea.value = state.managerDrafts.get(config.bot_id) || "{}";
    textarea.addEventListener("input", () => state.managerDrafts.set(config.bot_id, textarea.value));
    details.append(settings, caption, textarea); card.append(details);
    const actions = node("div", undefined, "config-actions");
    const capabilities = observed?.action_capabilities || {};
    [ ["edit", "Save new revision"], ["apply", "Apply saved revision"], ["start", "Start paper bot"], ["stop", "Stop paper bot"] ].forEach(([operation, captionText]) => {
      const wrapper = node("div", undefined, "action-control"); const button = node("button", captionText, "button secondary"); button.type = "button"; button.dataset.controlKey = `manager:${operation}:${config.bot_id}:${config.config_revision}`;
      const available = capabilities[operation]?.available === true;
      const busy = state.busy.has(actionKey(`manager.${operation}`, { identity: config.bot_id }));
      button.disabled = !available || busy;
      const reason = capabilities[operation]?.reason || "owner_capability_unavailable";
      button.title = human(reason);
      button.addEventListener("click", () => {
        const params = { identity: config.bot_id };
        if (["edit", "apply"].includes(operation)) params.expected_revision = config.config_revision;
        if (operation === "edit") {
          try {
            const delta = JSON.parse(textarea.value);
            if (!delta || Array.isArray(delta) || typeof delta !== "object") throw new Error("object_required");
            params.overrides = delta;
          } catch { announce("Settings delta must be a JSON object. No action was sent."); return; }
        }
        submitAction(`manager.${operation}`, params, button);
      });
      wrapper.append(button, node("p", human(reason))); actions.append(wrapper);
    });
    card.append(actions, node("p", `Configuration ${label(config.config_hash)} · owner ${label(config.owner)}. Saving and adopting settings are separate actions.`, "config-status"));
    fragment.append(card);
  });
  if (!fragment.childNodes.length) fragment.append(node("p", "No saved manager configuration is available. Create a paper draft above; its owner will report runtime readiness.", "empty"));
  replaceWithFocus("manager-configs", fragment);
}
function renderControl() {
  text("control-status", state.control ? "Owner interfaces observed" : "Unavailable");
  const servers = document.createDocumentFragment(); const actions = document.createDocumentFragment();
  array(state.control?.servers).forEach((server) => {
    const card = node("article", undefined, "server-card");
    card.append(node("h3", server.label || server.id), node("span", human(server.state), "server-state"));
    const facts = node("dl");
    [["Owner", server.owner], ["Running", server.running === true ? "Yes" : server.running === false ? "No" : "Unavailable"], ["Process ID", server.pid], ["Heartbeat", timestamp(server.heartbeat_at)]].forEach(([name, value]) => {
      const group = node("div"); group.append(node("dt", name), node("dd", value)); facts.append(group);
    });
    [["Snapshot age", finite(server.snapshot_age_s) ? `${server.snapshot_age_s.toFixed(1)} seconds` : undefined], ["Messages", server.messages], ["Snapshots", server.snapshots], ["Reconnects", server.reconnects], ["Recorded days", server.recorded_days], ["Live connection", typeof server.live === "boolean" ? server.live ? "Connected" : "Disconnected" : undefined], ["Service definition", typeof server.service?.definition_present === "boolean" ? server.service.definition_present ? "Installed" : "Absent" : undefined]].filter(([, value]) => value !== undefined).forEach(([name, value]) => {
      const group = node("div"); group.append(node("dt", name), node("dd", value)); facts.append(group);
    });
    card.append(facts); servers.append(card);
    array(server.actions).forEach((descriptor) => {
      const warning = descriptor.action?.startsWith("recorder.") ? "Shared recorder: this action affects every subscribing component." : descriptor.reason;
      actions.append(actionButton(descriptor.action, descriptor.label || human(descriptor.action), descriptor.params || {}, descriptor.enabled === true, warning));
    });
  });
  if (!servers.childNodes.length) servers.append(node("p", "Server state is unavailable. Controls remain disabled until the owner responds.", "empty"));
  if (!actions.childNodes.length) actions.append(node("p", "No supported server action is available.", "empty"));
  $("server-cards").replaceChildren(servers); replaceWithFocus("server-actions", actions);
  const recording = state.control?.recording;
  const recordingAvailable = typeof recording?.enabled === "boolean" && Number.isSafeInteger(recording?.revision);
  if (!state.recordingDirty) $("record-pnl").checked = recording?.enabled === true;
  $("record-pnl").disabled = !recordingAvailable || preferencePending("recording");
  $("recording-save").disabled = !recordingAvailable || preferencePending("recording") || state.busy.has(actionKey("pnl.recording.set", {}));
  text("recording-status", recordingAvailable ? `Current policy: ${recording.enabled ? "recording new paper outcomes" : "new accounting disabled"} · revision ${recording.revision}. Historical evidence remains retained.` : "Recording policy is unavailable.");
  const runOptions = [{ id: "", label: "Primary pipeline" }, ...array(state.control?.runs).map((run) => ({ id: run.id, label: run.name || run.id }))];
  fillSelect("active-run", runOptions, state.activeRun); $("active-run").value = state.activeRun;
  const selectedRun = array(state.control?.runs).find((run) => run.id === state.activeRun);
  text("active-run-note", `${selectedRun?.name || (state.activeRun ? state.activeRun : "Primary pipeline")} · server and recording controls act on this run`);
  renderLaunchCatalog(); renderRuns(); renderManagerConfigs(); renderActionLedger();
}
function renderActionLedger() {
  const records = new Map(state.localActions);
  array(state.control?.recent_actions).forEach((record) => records.set(record.id, record));
  for (const [id, effect] of state.pendingPrefs) {
    const record = records.get(id);
    if (["failed", "interrupted"].includes(record?.state)) {
      state.pendingPrefs.delete(id);
      announce(`${human(record.action)} ${human(record.state)}. Your unsaved choice is retained; inspect the action record.`);
    } else if (record?.state === "succeeded" && effect.run === state.activeRun) {
      const expected = record.result?.revision;
      const actual = effect.kind === "recording" ? state.control?.recording?.revision : state.oracle?.selection?.revision;
      if (Number.isSafeInteger(expected) && Number.isSafeInteger(actual) && actual >= expected) {
        if (effect.kind === "recording") state.recordingDirty = false;
        else state.voterDrafts.delete(voterKey(effect.instrument, effect.run));
        state.pendingPrefs.delete(id);
        announce(`${human(record.action)} completed · saved revision ${expected}.`);
      }
    }
  }
  const values = Array.from(records.values()).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))).slice(0, 100);
  const fragment = document.createDocumentFragment();
  values.forEach((record) => {
    const row = node("tr"); const action = node("td", human(record.action));
    const inspect = node("a", record.id); inspect.href = `/api/actions?id=${encodeURIComponent(record.id)}`; inspect.target = "_blank"; inspect.rel = "noopener noreferrer";
    action.append(node("small", undefined)); action.lastChild.append(inspect);
    const outcome = record.error ? typeof record.error === "string" ? record.error : JSON.stringify(record.error) : record.result ? JSON.stringify(record.result) : record.state === "queued" ? "Accepted; awaiting owner execution" : "No completed result received";
    row.append(action, node("td", human(record.state)), node("td", timestamp(record.created_at)), node("td", outcome.length > 1200 ? `${outcome.slice(0, 1200)} · bounded preview; open the action record` : outcome));
    fragment.append(row);
  });
  $("action-rows").replaceChildren(fragment); $("action-empty").hidden = values.length > 0;
  text("action-ledger-note", `${values.length} recent action records. Queued, running, failed and completed outcomes remain distinct.`);
}
function forwardPnl(forward) {
  return forward && forward.status === "available" && forward.resolved > 0 && forward.recorded > 0 && finite(forward.realized_pnl_usd) ? forward.realized_pnl_usd : null;
}
function renderAnalytics() {
  const data = state.analytics; const coins = array(data?.coins);
  text("analytics-status", human(data?.status));
  text("coin-performance-note", state.selected ? `Selected strategy ${human(state.selectedRecord?.strategy_id)} · all attributable coin results from the research owner.` : "Select a bot to compare historical and forward evidence across coins.");
  const fragment = document.createDocumentFragment();
  let calls = 0; let resolved = 0; let recorded = 0; let measured = 0; let positive = 0; let negative = 0; let singlePnl = null;
  coins.forEach((coin) => {
    const forward = coin.forward || {}; const backtest = coin.backtest || {}; const pnl = forwardPnl(forward);
    calls += finite(forward.calls) ? forward.calls : 0; resolved += finite(forward.resolved) ? forward.resolved : 0; recorded += finite(forward.recorded) ? forward.recorded : 0;
    if (finite(pnl)) { measured += 1; singlePnl = pnl; if (pnl > 0) positive += 1; if (pnl < 0) negative += 1; }
    const row = node("tr");
    const market = node("td", coin.asset); market.append(node("small", `${coin.interval} · ${human(coin.horizon)}`));
    const historical = node("td", human(backtest.state));
    historical.append(node("small", finite(backtest.score) ? `${backtest.score.toFixed(3)} CPCV median Sharpe` : human(backtest.reason || "score_unavailable")));
    if (finite(backtest.median_return_percent)) historical.append(node("small", `${backtest.median_return_percent.toFixed(2)}% selected historical median return`));
    if (backtest.selected_configuration) {
      const configuration = node("details"); configuration.append(node("summary", "Selected parameters"), node("pre", JSON.stringify(backtest.selected_configuration, null, 2), "safe-json")); historical.append(configuration);
    }
    const prospective = node("td", `${label(forward.calls)} / ${label(forward.resolved)}`);
    prospective.append(node("small", `${label(forward.pending)} pending · ${label(forward.recorded)} recorded · ${label(forward.excluded)} excluded`));
    const economic = node("td", money(pnl), finite(pnl) ? pnl > 0 ? "positive" : pnl < 0 ? "negative" : "" : "");
    economic.append(node("small", finite(pnl) && finite(forward.realized_return_percent) ? `${forward.realized_return_percent.toFixed(2)}% on stated paper notional` : human(forward.status || "no_recorded_resolved_economic_result")), node("small", `${finite(forward.paper_capital_usd) ? money(forward.paper_capital_usd) : finite(forward.paper_capital_reference) && forward.quote_currency ? `${forward.paper_capital_reference.toFixed(2)} ${forward.quote_currency}` : "Unavailable"} capital per independent trial`));
    const assessment = node("td", human(forward.profit_assessment || "profit_unknown"));
    const costs = [ ["fees", forward.fees_bps], ["slippage", forward.slippage_bps], ["borrow", forward.borrow_bps] ].map(([name, value]) => `${name} ${finite(value) ? value.toFixed(2) : "unavailable"} bps`).join(" · ");
    assessment.append(node("small", costs)); row.append(market, historical, prospective, economic, assessment); fragment.append(row);
  });
  $("coin-rows").replaceChildren(fragment); $("coin-empty").hidden = coins.length > 0;
  text("coin-empty", state.selected ? "No attributable per-coin evidence is currently available for this identity." : "No bot selected.");
  text("coin-policy", `Source: existing historical and forward ledgers. ${data?.recording?.enabled === false ? "New P&L recording is disabled; prior records are retained. " : ""}Paper returns describe independent trial notionals and can overlap. They are not a compounded portfolio or live profit. Unresolved or excluded calls cannot establish profit.`);
  const stages = data?.stages || state.control?.runs?.find((run) => run.id === state.selectedRecord?.run_id || run.batch_id === state.selectedRecord?.batch_id)?.stages || inferredSelectedStages(coins);
  renderStages("selected-stages", stages);
  text("equity-message", measured ? measured === 1 ? `${money(singlePnl)} recorded trial net result` : `${positive} profitable · ${negative} losing / ${measured} measured trials` : state.selected ? "Profit is not established yet" : "Select a bot to inspect paper results");
  text("equity-reason", state.selected ? `${human(state.selectedRecord?.strategy_id)} · ${calls} prospective calls · ${resolved} resolved · ${recorded} included in accounting · ${measured} coins with measured P&L. Independent trial comparisons; costs included. No shared portfolio total is inferred.` : "Choose a fleet row. Recorded paper economics and directional accuracy are reported separately.");
}
function currentVoterDraft() {
  const policy = state.oracle?.selection;
  if (!policy || policy.instrument !== state.oracleInstrument || !Array.isArray(policy.selected_ids)) return null;
  let draft = state.voterDrafts.get(voterKey());
  if (!draft || !draft.dirty) {
    draft = { ids: [...policy.selected_ids], revision: policy.revision, dirty: false };
    state.voterDrafts.set(voterKey(), draft);
  }
  return draft;
}
function renderSelectedAggregate() {
  const value = state.oracle; const market = value?.market; const observation = market?.observation;
  const now = Date.now() / 1000;
  const expiry = value?.aggregate?.expires_at ?? value?.aggregate?.expiry;
  const fresh = market?.status === "available" && finite(observation?.observed_at) && finite(observation?.received_at) && observation.observed_at <= now && observation.received_at <= now && now - observation.observed_at <= 15 && now - observation.received_at <= 15;
  const available = value?.instrument === state.oracleInstrument && fresh && value?.status === "available" && finite(expiry) && expiry > now && finite(value?.aggregate?.balance_percent) && finite(value?.as_of) && value.as_of <= now && now - value.as_of <= 30;
  const signal = available ? value.signal : "Unavailable";
  const balance = available ? value.aggregate.balance_percent : null;
  const reason = available ? `${array(value.aggregate.included).length} contributing votes · ${array(value.aggregate.excluded).length} excluded. Directional vote balance, not profit probability.` : human(value?.aggregate?.reason || market?.reason || (!fresh ? "fresh_market_evidence_unavailable" : "insufficient_or_expired_forecast_evidence"));
  ["aggregate-signal", "oracle-signal"].forEach((id) => text(id, signal));
  ["aggregate-balance", "oracle-balance"].forEach((id) => text(id, available ? `${balance > 0 ? "+" : ""}${balance.toFixed(2)}% signed weighted vote balance` : "No current vote balance"));
  ["aggregate-reason", "oracle-reason"].forEach((id) => text(id, reason));
  text("aggregate-freshness", value ? `${value.instrument} · ${label(value.horizon_seconds)} second horizon · expires ${timestamp(expiry)}` : "No current Oracle response");
  const meter = $("aggregate-meter"); meter.hidden = !available; meter.value = available ? Math.abs(balance) : 0;
  const reading = meter.closest(".aggregate-reading"); reading.dataset.direction = !available ? "unavailable" : balance > 0 ? "buy" : balance < 0 ? "sell" : "flat";
  $("oracle-signal").className = available ? balance > 0 ? "positive" : balance < 0 ? "negative" : "" : "";
  text("oracle-explanation", `Engine ${state.control?.servers?.find((server) => server.id === "oracle")?.running === true ? "observed running" : "not observed running"}. Source: ${human(observation?.source)} · ${human(observation?.kind)} · observed ${timestamp(observation?.observed_at)}. ${array(market?.limitations).map(human).join(" · ")}. Historical accuracy and vote balance do not measure a probability of profit.`);
  const instruments = array(state.control?.catalog?.coins).map((coin) => `${coin}/USD`);
  if (!instruments.includes(state.oracleInstrument)) instruments.push(state.oracleInstrument);
  fillSelect("oracle-instrument", instruments, state.oracleInstrument); fillSelect("oracle-instrument-detail", instruments, state.oracleInstrument);
  $("oracle-instrument").value = state.oracleInstrument; $("oracle-instrument-detail").value = state.oracleInstrument;
  const draft = currentVoterDraft(); const catalog = array(value?.catalog); const strategies = array(value?.strategies);
  const focused = document.activeElement?.dataset?.strategyId; const fragment = document.createDocumentFragment();
  catalog.forEach((card) => {
    const id = card.strategy_id || card.id; if (typeof id !== "string") return;
    const row = strategies.find((entry) => entry.strategy_id === id) || {};
    const labelElement = node("label", undefined, "voter-option"); const input = document.createElement("input");
    input.type = "checkbox"; input.value = id; input.dataset.strategyId = id; input.checked = draft?.ids.includes(id) || false; input.disabled = !draft || preferencePending("voters", state.oracleInstrument);
    input.addEventListener("change", () => {
      const edited = currentVoterDraft(); if (!edited) return;
      edited.ids = Array.from($("voter-options").querySelectorAll("input:checked")).map((item) => item.value); edited.dirty = true;
      renderVoterStatus();
    });
    const content = node("span"); content.append(node("strong", human(id)));
    const excluded = array(value?.aggregate?.excluded).find((entry) => entry.strategy_id === id);
    const accuracy = finite(row.confidence_percent) ? `${row.confidence_percent.toFixed(2)}% historical directional accuracy` : "Insufficient resolved directional evidence";
    content.append(node("small", accuracy), node("small", `${label(row.hits)} hits / ${label(row.resolved)} resolved · ${human(excluded?.reason || row.reason || "current_owner_evidence")}`));
    const vote = array(value?.aggregate?.included).find((entry) => entry.strategy_id === id);
    if (finite(vote?.weight)) content.append(node("small", `${(vote.weight * 100).toFixed(2)}% of one vote · weighted by resolved accuracy`));
    labelElement.append(input, content); fragment.append(labelElement);
  });
  if (!catalog.length) fragment.append(node("p", "The Oracle strategy catalog is unavailable.", "empty"));
  $("voter-options").replaceChildren(fragment);
  if (focused) Array.from($("voter-options").querySelectorAll("input")).find((input) => input.dataset.strategyId === focused)?.focus();
  renderVoterStatus();
}
function renderVoterStatus() {
  const draft = currentVoterDraft(); const policy = state.oracle?.selection;
  const conflict = draft && policy && draft.revision !== policy.revision;
  $("voters-save").disabled = !draft || !draft.dirty || conflict || preferencePending("voters", state.oracleInstrument) || state.busy.has(actionKey("oracle.voters.set", { instrument: state.oracleInstrument }));
  $("voters-reset").disabled = !draft || !draft.dirty || preferencePending("voters", state.oracleInstrument);
  text("voters-status", preferencePending("voters", state.oracleInstrument) ? "Saving selection; waiting for the owner result and matching policy revision." : conflict ? "The saved policy changed while you edited. Restore the current saved selection before making a new change." : draft ? `${draft.ids.length} selected · policy revision ${draft.revision}${draft.dirty ? " · unsaved selection" : " · saved"}. Accuracy and freshness gates still apply.` : "No voting policy received.");
}
async function loadWikiCatalog(query = "") {
  const request = ++state.wikiRequest;
  text("wiki-search-status", "Searching the documentation snapshot…");
  try {
    const catalog = await get(`/api/wiki?q=${encodeURIComponent(query.trim())}`);
    if (request !== state.wikiRequest) return;
    state.wikiCatalog = catalog;
    array(catalog.pages).forEach((page) => state.wikiKnownPages.set(page.source_path, page));
    renderWikiIndex();
  } catch {
    if (request !== state.wikiRequest) return;
    state.wikiCatalog = null; $("wiki-results").replaceChildren(node("p", "Documentation snapshot is unavailable.", "empty"));
    text("wiki-search-status", "Wiki source unavailable. No cached documentation is presented as current.");
  }
}
function renderWikiIndex() {
  const catalog = state.wikiCatalog; const fragment = document.createDocumentFragment();
  array(catalog?.pages).forEach((page) => {
    const button = node("button", undefined, "wiki-page-link"); button.type = "button";
    button.append(node("span", page.title), node("small", `${human(page.category)} · ${page.source_path}`));
    if (state.wikiPage?.id === page.id) button.setAttribute("aria-current", "page");
    button.addEventListener("click", () => { location.hash = `wiki/${encodeURIComponent(page.id)}`; if (state.wikiPage?.id === page.id) loadWikiPage(page.id); });
    fragment.append(button);
  });
  if (!fragment.childNodes.length) fragment.append(node("p", "No source pages match this search.", "empty"));
  $("wiki-results").replaceChildren(fragment);
  text("wiki-search-status", catalog ? `${label(catalog.returned)} shown / ${label(catalog.total)} matching source pages${catalog.truncated ? " · search the full corpus to narrow results" : ""} · snapshot SHA-256 ${label(catalog.snapshot_sha256)}` : "Wiki catalog unavailable.");
}
function appendInline(element, source) {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]*\))/g;
  let cursor = 0; let match;
  while ((match = pattern.exec(source)) !== null) {
    element.append(document.createTextNode(source.slice(cursor, match.index)));
    const value = match[0];
    if (value.startsWith("`")) element.append(node("code", value.slice(1, -1)));
    else if (value.startsWith("**")) element.append(node("strong", value.slice(2, -2)));
    else {
      const parts = /^\[([^\]]+)\]\(([^)]*)\)$/.exec(value); const caption = parts[1]; const destination = parts[2];
      let link = null;
      try {
        const address = new URL(destination, `https://wiki.invalid/${state.wikiPage?.source_path || ""}`);
        if (address.hostname === "wiki.invalid" && address.protocol === "https:") {
          const relative = decodeURIComponent(address.pathname.slice(1));
          const page = state.wikiKnownPages.get(relative);
          if (page) { link = node("a", caption); link.href = `#wiki/${encodeURIComponent(page.id)}`; }
        } else if (["https:", "http:"].includes(address.protocol)) {
          link = node("a", caption); link.href = address.href; link.target = "_blank"; link.rel = "noopener noreferrer";
        }
      } catch { /* Untrusted malformed destinations remain plain text. */ }
      element.append(link || document.createTextNode(value));
    }
    cursor = pattern.lastIndex;
  }
  element.append(document.createTextNode(source.slice(cursor)));
}
function renderMarkdown(source) {
  const fragment = document.createDocumentFragment(); const lines = source.split(/\r?\n/); let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }
    if (/^\s*```/.test(line)) {
      const block = []; index += 1;
      while (index < lines.length && !/^\s*```/.test(lines[index])) { block.push(lines[index]); index += 1; }
      index += 1; const pre = node("pre"); pre.append(node("code", block.join("\n"))); fragment.append(pre); continue;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) { const element = node(`h${Math.min(4, heading[1].length + 1)}`); appendInline(element, heading[2]); fragment.append(element); index += 1; continue; }
    if (/^\s*\|/.test(line)) {
      const block = []; while (index < lines.length && /^\s*\|/.test(lines[index])) { block.push(lines[index]); index += 1; }
      fragment.append(node("pre", block.join("\n"))); continue;
    }
    const item = /^\s*([-*]|\d+\.)\s+(.+)$/.exec(line);
    if (item) {
      const list = node(/^\d/.test(item[1]) ? "ol" : "ul");
      while (index < lines.length) {
        const next = /^\s*([-*]|\d+\.)\s+(.+)$/.exec(lines[index]); if (!next || /^\d/.test(next[1]) !== /^\d/.test(item[1])) break;
        const li = node("li"); appendInline(li, next[2]); list.append(li); index += 1;
      }
      fragment.append(list); continue;
    }
    if (/^>\s?/.test(line)) { const quote = node("blockquote"); appendInline(quote, line.replace(/^>\s?/, "")); fragment.append(quote); index += 1; continue; }
    const paragraph = [];
    while (index < lines.length && lines[index].trim() && !/^\s*(```|#{1,6}\s|\||[-*]\s|\d+\.\s|>)/.test(lines[index])) { paragraph.push(lines[index]); index += 1; }
    if (!paragraph.length) { paragraph.push(lines[index]); index += 1; }
    const element = node("p"); appendInline(element, paragraph.join(" ")); fragment.append(element);
  }
  return fragment;
}
async function loadWikiPage(id) {
  const request = ++state.wikiPageRequest;
  text("wiki-page-title", "Loading source guide…");
  try {
    const data = await get(`/api/wiki/page?id=${encodeURIComponent(id)}`);
    if (request !== state.wikiPageRequest) return;
    const page = data.page;
    if (!page || page.id !== id || typeof page.body !== "string") throw new Error("invalid_wiki_page");
    state.wikiPage = page;
    text("wiki-page-title", page.title); text("wiki-category", human(page.category));
    text("wiki-source", `Source: ${page.source_location || page.source_path}`);
    text("wiki-proof", `SHA-256 ${label(page.content_sha256)} · source commit ${label(page.source_commit)}`);
    $("wiki-body").replaceChildren(renderMarkdown(page.body)); renderWikiIndex();
  } catch {
    if (request !== state.wikiPageRequest) return;
    state.wikiPage = null; text("wiki-page-title", "Source page unavailable");
    text("wiki-source", "No current source could be verified."); text("wiki-proof", "No verified document hash.");
    $("wiki-body").replaceChildren(node("p", "This page could not be loaded. Search the wiki for a current source."));
  }
}
$("launch-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const params = launchParams();
  if (!params.coins.length) { announce("Choose at least one coin before launching. No action was sent."); return; }
  if (!params.strategies[0] || !params.name || !finite(params.capital) || params.capital <= 0 || !params.start || !params.end || params.start >= params.end) { announce("Choose a valid strategy, name, capital and history window. No action was sent."); return; }
  await submitAction("research.launch", params, $("launch-submit"));
});
$("launch-form").addEventListener("input", renderLaunchReview);
["coins-all", "coins-none"].forEach((id) => $(id).addEventListener("click", () => { $("launch-coins").querySelectorAll("input").forEach((input) => { input.checked = id === "coins-all"; }); renderLaunchReview(); }));
$("manager-create-form").addEventListener("submit", async (event) => {
  event.preventDefault(); let overrides;
  try { overrides = JSON.parse($("manager-new-overrides").value); if (!overrides || Array.isArray(overrides) || typeof overrides !== "object") throw new Error("object_required"); }
  catch { announce("Settings overrides must be a JSON object. No action was sent."); return; }
  await submitAction("manager.create", { name: $("manager-new-name").value.trim(), strategy: $("manager-new-strategy").value, overrides }, $("manager-create-submit"));
});
$("record-pnl").addEventListener("change", () => { state.recordingDirty = true; });
$("recording-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const recording = state.control?.recording; if (!recording) return;
  const run = state.activeRun;
  const result = await submitAction("pnl.recording.set", { enabled: $("record-pnl").checked, expected_revision: recording.revision }, $("recording-save"));
  if (result) state.pendingPrefs.set(result.id, { kind: "recording", run });
});
function setInstrument(instrument) {
  state.oracleInstrument = instrument; state.oracle = null; renderSelectedAggregate(); renderOracle(); refresh();
}
["oracle-instrument", "oracle-instrument-detail"].forEach((id) => $(id).addEventListener("change", (event) => setInstrument(event.target.value)));
$("voter-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const draft = currentVoterDraft(); if (!draft) return;
  const instrument = state.oracleInstrument; const run = state.activeRun;
  const result = await submitAction("oracle.voters.set", { instrument, ids: [...draft.ids], expected_revision: draft.revision }, $("voters-save"));
  if (result) state.pendingPrefs.set(result.id, { kind: "voters", run, instrument });
});
$("voters-reset").addEventListener("click", () => { state.voterDrafts.delete(voterKey()); renderSelectedAggregate(); });
$("wiki-search-form").addEventListener("submit", (event) => { event.preventDefault(); loadWikiCatalog($("wiki-search").value); });
let wikiSearchTimer;
$("wiki-search").addEventListener("input", () => { clearTimeout(wikiSearchTimer); wikiSearchTimer = setTimeout(() => loadWikiCatalog($("wiki-search").value), 300); });

function scoped(path) {
  return state.activeRun ? `${path}${path.includes("?") ? "&" : "?"}run_id=${encodeURIComponent(state.activeRun)}` : path;
}
function setActiveRun(id) {
  if (id === state.activeRun) return;
  const run = array(state.control?.runs).find((item) => item.id === id);
  state.activeRun = id; state.page = 0; state.cursors = [""]; state.next = null;
  state.selected = null; state.selectedRecord = null; state.analytics = null;
  state.status = null; state.registrations = null; state.oracle = null; state.control = null;
  state.recordingDirty = false;
  text("logs-status", "Research run changed. Load the current run’s source logs."); $("logs-content").replaceChildren();
  const coins = array(run?.config?.coins);
  if (coins.length && !coins.includes(state.oracleInstrument.split("/")[0])) state.oracleInstrument = `${coins[0]}/USD`;
  render(); refresh();
}
function inferredSelectedStages(coins) {
  if (!coins.length) return [];
  const done = coins.filter((coin) => terminal.includes(coin.backtest?.state)).length;
  const eligible = coins.filter((coin) => coin.backtest?.selected_configuration);
  const observed = eligible.filter((coin) => coin.forward?.calls > 0).length;
  return [
    { id: "backtest", label: "Historical scoring", state: done === coins.length ? "complete" : "running", done, total: coins.length, detail: "Terminal historical cells; missing and unsupported remain explicit." },
    { id: "forward", label: "Forward call coverage", state: eligible.length ? observed ? "observing" : "waiting" : "blocked", done: observed, total: eligible.length, detail: "Coins with actual prospective calls; coverage is not completed forward validation." },
    { id: "outcomes", label: "Economic outcomes", state: coins.some((coin) => forwardPnl(coin.forward) !== null) ? "observing" : "waiting", detail: "Recorded resolutions establish paper economics; no arbitrary certainty target is invented." },
    { id: "live", label: "Live readiness", state: "unavailable", detail: "Requires separate evidence from the responsible live owner." },
  ];
}
async function loadSwapState() {
  try {
    const data = await get("/api/swap"); state.swap = data; renderSwapState(); return data;
  } catch {
    state.swap = null; text("swap-status", "The dedicated swap service is unavailable. Wallet code has not been loaded.");
    $("swap-load").disabled = true; fields("swap-facts", [["Availability", "Unavailable"], ["Wallet authority", "Explicit wallet approval only"]]); return null;
  }
}
function renderSwapState() {
  const data = state.swap; const config = data?.config || {};
  text("swap-status", data?.reason ? `Swap configuration: ${human(data.reason)}. Inspect the dedicated interface before wallet approval.` : state.swapLoaded ? "Dedicated swap page loaded. Inspect its current quote and approve explicitly with your wallet." : "Wallet interface is unloaded. The provider runs on its own local origin after your explicit load action.");
  fields("swap-facts", [
    ["Provider", config.provider || "Jupiter"], ["Scope", data?.scope], ["Configuration state", human(data?.status || data?.readiness?.status || "quote_not_yet_requested")],
    ["Referral fee", finite(config.referral_fee_bps) ? `${config.referral_fee_bps} bps configured` : "Unavailable until verified"],
    ["Referral accounts", config.referral_accounts ? JSON.stringify(config.referral_accounts) : "Unavailable"],
    ["Actual venue fee", "Available only from the current route quote"],
    ["Tip / priority cost", config.tip ? JSON.stringify(config.tip) : "Available only from the current quote or explicit widget setting"],
    ["Paper cost model", "Separate configured scenario; not an actual Jupiter quote"],
    ["Transaction authority", "Your wallet; no Oracle signing or submission"],
  ]);
  $("swap-load").disabled = state.swapLoaded || !data?.url;
  $("swap-unload").disabled = !state.swapLoaded;
}
$("active-run").addEventListener("change", (event) => setActiveRun(event.target.value));
$("swap-load").addEventListener("click", async () => {
  const data = await loadSwapState(); if (!data) return;
  try {
    const address = new URL(data.url);
    if (data.scope !== "manual_wallet_swap" || address.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(address.hostname) || address.origin === location.origin || address.username || address.password) throw new Error("invalid_swap_origin");
    const frame = document.createElement("iframe"); frame.title = "Manual Jupiter swap; wallet approval required";
    frame.referrerPolicy = "no-referrer"; frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups");
    frame.src = address.href; $("swap-container").replaceChildren(frame); $("swap-container").hidden = false;
    state.swapLoaded = true; renderSwapState();
  } catch { text("swap-status", "The swap service did not provide an approved separate local origin. No wallet interface was loaded."); }
});
$("swap-unload").addEventListener("click", () => {
  $("swap-container").replaceChildren(); $("swap-container").hidden = true; state.swapLoaded = false; renderSwapState();
  announce("The embedded swap page was unloaded. This does not cancel a signed or submitted transaction.");
});
$("logs-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const server = $("log-server").value; const run = state.activeRun;
  const button = $("logs-load"); button.disabled = true; button.setAttribute("aria-busy", "true");
  text("logs-status", `Loading ${human(server)} source logs…`); $("logs-content").replaceChildren();
  try {
    const data = await get(scoped(`/api/logs?server=${encodeURIComponent(server)}&limit=100`));
    if (run !== state.activeRun || server !== $("log-server").value) return;
    const fragment = document.createDocumentFragment();
    array(data.files).forEach((file) => {
      const section = node("section", undefined, "log-file");
      section.append(node("h3", file.path), node("p", `${label(file.bytes)} bytes · modified ${timestamp(file.modified_at)} · ${file.truncated ? "bounded tail; earlier content omitted" : "tail not truncated"}`, "subtle"));
      section.append(node("pre", array(file.lines).map((line) => `${line.redacted ? "[redacted] " : ""}${typeof line.text === "string" ? line.text : "Unavailable"}`).join("\n"), "log-tail")); fragment.append(section);
    });
    $("logs-content").replaceChildren(fragment);
    text("logs-status", data.status === "available" ? `${human(server)} · ${array(data.files).length} observed source file${data.files?.length === 1 ? "" : "s"}. Redacted tail only.` : `Logs unavailable: ${human(data.reason)}. No synthetic log content is supplied.`);
  } catch { if (run === state.activeRun) text("logs-status", "Log source unavailable. Refresh server state and try the requested source again."); }
  finally { button.disabled = false; button.removeAttribute("aria-busy"); }
});
