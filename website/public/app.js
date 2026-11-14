import { freshStrategy } from './evidence.js';
import { createAgentAccess } from './agent-access.js';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const main = $('#main');
const TIMING = Object.freeze({ requestTimeoutMs: 25000, toastMs: 6500, oraclePollMs: 15000, evidenceCheckMs: 1000 });
const state = { config: { coins: ['SOL', 'BTC', 'ETH', 'ZEC'], trialDays: 7 }, user: null, subscription: null, usage: null, portalAvailable: false, bots: [], botsNextPage: null, botsUnavailable: false, accountStatus: 'loading', accountEpoch: 0, accountRequest: 0, accountTransition: false, navigationEpoch: 0, articles: [], strategies: [], coin: 'SOL', oracle: null, view: 'overview', search: '', category: 'all', loadingOracle: false, oracleRequest: 0 };
const agentAccess = createAgentAccess({ api, getUser: () => state.accountTransition ? null : state.user, isSettings: () => state.view === 'settings', openWallet, toast });
const views = { overview: 'Overview', oracle: 'The oracle', bots: 'My bots', backtest: 'Backtest lab', research: 'Research journal', pricing: 'Membership', settings: 'Settings & account' };
const coinNames = { SOL: 'Solana', BTC: 'Bitcoin', ETH: 'Ethereum', ZEC: 'Zcash' };
const coinSymbols = { SOL: '◎', BTC: '₿', ETH: 'Ξ', ZEC: 'Z' };
const strategyLabels = { ema_crossover: 'EMA crossover', rsi: 'RSI', bb_reversion: 'Bollinger reversion', grid: 'Grid' };
let toastTimer;
const researchShards = new Map();

function el(tag, className, value) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (value !== undefined && value !== null) item.textContent = String(value);
  return item;
}
function appendText(parent, tag, className, value) { const item = el(tag, className, value); parent.append(item); return item; }
function errorText(error) {
  const messages = {
    unauthorized: 'Connect and sign in with your wallet to continue.', authentication_required: 'Connect and sign in with your wallet to continue.', account_changed: 'Your account changed. Check your current account and try again.',
    subscription_required: 'An active membership or Stripe trial is needed. Open Membership to get started.', entitlement_required: 'An active membership or Stripe trial is needed. Open Membership to get started.',
    billing_unavailable: 'Membership checkout is not available yet. You can still browse the research journal.', billing_not_configured: 'Membership checkout is not available yet. You can still browse the research journal.',
    engine_unavailable: 'The research engine is currently unavailable. No result has been estimated.', engine_not_configured: 'The research engine is not connected yet. No result has been estimated.',
    invalid_plan: 'Choose one of the available membership plans.', bot_limit: 'Your configured bot slots are full. Pause or archive a configuration to free a slot.',
    backtest_daily_limit: 'Your daily backtest allowance is used. It resets at 00:00 UTC.', backtest_in_progress: 'One backtest is already in progress. Wait for it to finish before starting another.',
    live_execution_unavailable: 'Live execution is unavailable. Save a paper configuration instead.', invalid_signature: 'The wallet signature could not be verified. Please try connecting again.',
    challenge_expired: 'The sign-in message expired. Please connect again.', rate_limited: 'Too many attempts. Please wait a moment and try again.'
  };
  return messages[error?.code] || error?.message || 'Something went wrong. Please try again.';
}
async function api(path, options = {}, expectedAccountId = state.user?.id) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMING.requestTimeoutMs);
  const privatePath = /^\/api\/(?:me(?:[/?]|$)|bots(?:[/?]|$)|backtest-jobs(?:[/?]|$)|backtests(?:[/?]|$)|connections(?:[/?]|$)|execution(?:[/?]|$)|billing\/|agent\/|auth\/logout(?:[/?]|$))/.test(path);
  try {
    const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers, ...(privatePath && expectedAccountId ? { 'X-Oraclebot-Account': expectedAccountId } : {}) }, signal: controller.signal });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const code = typeof body.error === 'string' ? body.error : body.error?.code || body.code;
      const message = body.error?.message || body.message;
      const error = new Error(message || `Request could not complete (${response.status}).`);
      error.code = code;
      throw error;
    }
    return body;
  } catch (error) {
    if (error?.name === 'AbortError') throw new Error('This request is taking too long. No result has been estimated. Please try again later.');
    throw error;
  } finally { clearTimeout(timer); }
}
function toast(message) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, TIMING.toastMs);
}
function shortWallet(wallet) { return wallet ? `${wallet.slice(0, 4)}…${wallet.slice(-4)}` : 'Connect wallet'; }
function formatDate(value) { const date = new Date(typeof value === 'number' && value < 1e12 ? value * 1000 : value); return Number.isNaN(date.getTime()) ? 'Not available' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
function currency(value) { const number = Number(value); return Number.isFinite(number) ? new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(number) : '—'; }
function displayNumber(value, digits = 2) { return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: digits }) : '—'; }
function setBusy(button, busy) { if (button) { button.disabled = busy; button.setAttribute('aria-busy', String(busy)); } }
function accountContext() { return { epoch: state.accountEpoch, userId: state.user?.id ?? null }; }
function currentAccount(context) { return !state.accountTransition && state.accountStatus === 'ready' && state.accountEpoch === context.epoch && (state.user?.id ?? null) === context.userId; }
function clearAccount() { for (const dialog of $$('.automation-dialog')) dialog.remove(); Object.assign(state, { user: null, subscription: null, usage: null, portalAvailable: false, bots: [], botsNextPage: null, botsUnavailable: false }); }
function beginAccountTransition() {
  const context = accountContext();
  state.accountEpoch++; state.accountRequest++; state.accountTransition = true; state.accountStatus = 'loading';
  agentAccess.invalidate(); clearAccount(); $('#bot-dialog').close(); $('#bot-form').reset(); $('#bot-message').textContent = ''; render();
  return { ...context, epoch: state.accountEpoch };
}
function accountActionReady() {
  if (state.accountTransition || state.accountStatus === 'loading') { toast('An account request is already in progress. Finish or cancel that request first.'); return false; }
  if (state.accountStatus === 'unavailable') { toast('Your account could not be checked. Retry the account check before continuing.'); return false; }
  return true;
}
function accountNotice() {
  const notice = el('section', 'panel panel-pad account-notice'); notice.setAttribute('role', 'status');
  appendText(notice, 'h2', '', state.accountStatus === 'unavailable' ? 'Your account could not be checked.' : 'Checking your account…');
  appendText(notice, 'p', '', state.accountStatus === 'unavailable' ? 'Your sign-in and saved workspace are unknown. Retry before changing account data.' : 'Wait while your current wallet session is checked.');
  if (state.accountStatus === 'unavailable') { const retry = el('button', 'button button-outline', 'Retry account check'); retry.dataset.action = 'refresh-account'; notice.append(retry); }
  return notice;
}
function orbit() {
  return '<svg class="hero-orbit" viewBox="0 0 350 350" fill="none" aria-hidden="true"><circle cx="175" cy="175" r="105" stroke="currentColor" stroke-width=".7"/><circle cx="175" cy="175" r="132" stroke="currentColor" stroke-width=".5" stroke-dasharray="2 7"/><ellipse cx="175" cy="175" rx="155" ry="50" transform="rotate(-43 175 175)" stroke="currentColor" stroke-width="1"/><ellipse cx="175" cy="175" rx="121" ry="41" transform="rotate(44 175 175)" stroke="currentColor" stroke-width=".5"/><circle cx="175" cy="175" r="66" stroke="currentColor" stroke-width=".7"/><path d="M175 44v55m0 152v55M44 175h55m152 0h55" stroke="currentColor" stroke-width=".7"/><circle cx="175" cy="175" r="18" stroke="currentColor"/><circle cx="175" cy="175" r="5" fill="currentColor"/><circle cx="279" cy="136" r="5" fill="currentColor"/><path d="m277 139 11-10m-15 4 10 10" stroke="currentColor" stroke-width=".7"/></svg>';
}
function heading(eyebrow, title, text, action = '') {
  return `<div class="view-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p>${text}</p></div>${action}</div>`;
}
function sectionHeading(number, title, destination, text) {
  return `<div class="section-heading"><h2><span class="section-index">${number}</span>${title}</h2>${destination ? `<a href="#${destination}" class="text-link">${text}<span aria-hidden="true">↗</span></a>` : ''}</div>`;
}
function coinTabs() {
  const container = el('div', 'coin-tabs');
  container.setAttribute('role', 'group'); container.setAttribute('aria-label', 'Select coin');
  for (const coin of state.config.coins) {
    const button = el('button', `coin-tab${state.coin === coin ? ' active' : ''}`, coin);
    button.dataset.coin = coin; button.setAttribute('aria-pressed', String(state.coin === coin)); container.append(button);
  }
  return container;
}
function oraclePanel(full = false) {
  const leader = freshStrategy(state.oracle);
  const panel = el('section', `panel${full ? ' oracle-full' : ''}`);
  panel.setAttribute('aria-label', 'Leading strategy for selected coin');
  const top = el('div', 'panel-top');
  const label = el('h3', '', 'Strategy outlook'); label.prepend(el('span', 'small-star', '◎')); top.append(label, coinTabs()); panel.append(top);
  const body = el('div', 'signal-body');
  const detail = el('div', 'signal-detail'); appendText(detail, 'h3', '', state.oracle?.instrument || `${coinNames[state.coin] || state.coin} · quote unavailable`); appendText(detail, 'p', '', 'The leading eligible strategy for this coin.');
  const status = el('div', 'signal-status'); status.append(el('span', 'status-dot'), el('span', '', state.loadingOracle ? 'CHECKING' : leader ? 'EVIDENCE AVAILABLE' : 'AWAITING EVIDENCE'));
  body.append(el('span', 'coin-icon', coinSymbols[state.coin] || state.coin.slice(0, 1)), detail, status); panel.append(body);
  if (leader) {
    const strategy = leader;
    const live = el('div', 'signal-live');
    const rawDirection = String(strategy.direction || 'unavailable').toLowerCase();
    const direction = rawDirection === 'up' || rawDirection === 'long' || rawDirection === 'bullish' ? '↗ UPWARD OUTLOOK' : rawDirection === 'down' || rawDirection === 'short' || rawDirection === 'bearish' ? '↘ DOWNWARD OUTLOOK' : rawDirection === 'flat' || rawDirection === 'neutral' ? '→ FLAT OUTLOOK' : 'DIRECTION UNAVAILABLE';
    appendText(live, 'span', `direction${direction.includes('DOWNWARD') ? ' down' : ''}`, direction);
    appendText(live, 'h2', 'signal-name', strategy.name || strategy.id);
    const grid = el('div', 'metric-grid');
    for (const [label, value] of [['Ranking score', displayNumber(strategy.score)], ['Resolved samples', displayNumber(strategy.sampleSize, 0)], ['As of', strategy.asOf ? formatDate(strategy.asOf) : 'Unavailable']]) {
      const item = el('div', 'metric'); item.append(el('small', '', label), el('strong', '', value)); grid.append(item);
    }
    live.append(grid); appendText(live, 'p', 'fine-print', 'A strategy outlook is a measured signal, not a probability of profit. Historical rankings can change.'); panel.append(live);
  } else {
    const empty = el('div', 'signal-placeholder');
    empty.append(el('div', 'target', '⊕'), el('strong', '', state.loadingOracle ? 'Reading the evidence…' : 'A clear signal starts with good evidence.'));
    appendText(empty, 'p', '', state.loadingOracle ? 'Checking the latest available strategy observations.' : state.oracle?.message || 'No eligible, fresh strategy observation is available for this coin yet. The oracle will show the leader and its direction here when the evidence is ready.');
    panel.append(empty);
  }
  const footer = el('div', 'panel-bottom'); footer.append(el('span', '', 'NO SIGNAL IS A VALID SIGNAL.'), el('span', '', 'Forecasts never place orders')); panel.append(footer);
  return panel;
}
function featuredArticles() {
  const preferred = ['research/META-ANALYSIS.md', 'research/SHAPE-AWARE-SPOT.md', 'research/COINBASE50-GRID-CYCLES.md'];
  const selected = preferred.map(path => state.articles.find(article => article.source === path)).filter(Boolean);
  return [...selected, ...state.articles.filter(article => !selected.includes(article))].slice(0, 3);
}
function overview() {
  main.innerHTML = `<div class="page-intro"><div><p class="eyebrow">A BETTER PERSPECTIVE</p><h1>Your edge starts here.</h1><p>One workspace. Every idea, put to the test.</p></div><span class="date-label" id="today-date"></span></div><section class="hero"><div class="hero-content"><p class="eyebrow">MEET YOUR NEW RESEARCH PARTNER</p><h1>Less noise.<br>More <em>conviction.</em></h1><p>Find the strategy. Understand the signal. Test your thesis before putting capital behind it.</p><a href="#oracle" class="button button-lime">Explore the oracle <span aria-hidden="true">↗</span></a></div>${orbit()}<span class="hero-coordinate">OBSERVE / TEST / REFINE</span></section>${sectionHeading('01', 'Your market perspective', 'oracle', 'Open the oracle')}<div class="overview-grid" id="overview-grid"></div><div class="feature-row"><a href="#bots" class="feature-card"><div class="feature-head"><span class="feature-symbol" aria-hidden="true">⌘</span><span aria-hidden="true">↗</span></div><h3>A strategy of your own.</h3><p>Build a Coinbase spot bot or a Jupiter leveraged position configuration.</p></a><a href="#backtest" class="feature-card"><div class="feature-head"><span class="feature-symbol" aria-hidden="true">⌁</span><span aria-hidden="true">↗</span></div><h3>Test the idea. Not your luck.</h3><p>Explore historical performance with costs and risk built into the model.</p></a><a href="#research" class="feature-card"><div class="feature-head"><span class="feature-symbol" aria-hidden="true">▤</span><span aria-hidden="true">↗</span></div><h3>Go a little deeper.</h3><p>Read the reasoning, experiments and limitations behind the strategies.</p></a></div>${sectionHeading('02', 'Notes from the research desk', 'research', 'Read the journal')}<div class="journal-grid" id="journal-preview"></div>`;
  $('#today-date').textContent = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }).toUpperCase();
  const setup = el('section', 'panel getting-started');
  setup.innerHTML = `<h3>Make yourself at home.</h3><p>A thoughtful first trade starts well before execution.</p><div class="step"><span class="step-number${state.user ? ' done' : ''}">${state.user ? '✓' : '1'}</span><div><h4>Connect your wallet</h4><p>One signature. Your own account.</p></div><button class="text-link" data-action="wallet" aria-label="Connect your wallet">↗</button></div><div class="step"><span class="step-number">2</span><div><h4>Find your perspective</h4><p>Explore a coin and its leading strategy.</p></div><a class="text-link" href="#oracle" aria-label="Explore the oracle">↗</a></div><div class="step"><span class="step-number">3</span><div><h4>Put an idea to the test</h4><p>Start in the backtest lab. Stay curious.</p></div><a class="text-link" href="#backtest" aria-label="Open backtest lab">↗</a></div>`;
  $('#overview-grid').append(oraclePanel(), setup);
  renderArticles($('#journal-preview'), featuredArticles());
}
function oracleView() {
  main.innerHTML = heading('OBSERVE BEFORE YOU ACT', 'A perspective, with provenance.', 'Select a coin to see its leading eligible strategy and the direction it expects. Fresh evidence comes first.');
  main.append(oraclePanel(true));
  const info = el('div', 'info-strip'); info.append(el('span', '', 'ⓘ'), el('span', '', 'The top strategy is selected from measured evidence for your coin. If evidence is stale or missing, the oracle withholds a direction. Agreement is not a probability of profit.')); main.append(info);
  if (Array.isArray(state.oracle?.strategies) && state.oracle.strategies.length) {
    const section = el('section', 'panel panel-pad'); appendText(section, 'h3', '', 'Strategy evidence');
    const table = el('table', 'data-table');
    const head = el('thead'); const row = el('tr'); for (const name of ['Strategy', 'Direction', 'Score', 'Samples']) row.append(el('th', '', name)); head.append(row); table.append(head);
    const body = el('tbody'); for (const strategy of state.oracle.strategies) { const tr = el('tr'); for (const value of [strategy.name || strategy.id, strategy.direction || 'Unavailable', displayNumber(strategy.score), displayNumber(strategy.sampleSize, 0)]) tr.append(el('td', '', value)); body.append(tr); } table.append(body); section.append(table); main.append(section);
  }
}
function botsView() {
  main.innerHTML = heading('IDEAS, GIVEN STRUCTURE', 'Build with intention.', 'Create a bot configuration for Coinbase spot or a leveraged Jupiter position. Start in paper mode.', '<button class="button button-dark" data-action="new-bot">Create a bot <span aria-hidden="true">＋</span></button>');
  if (state.accountStatus !== 'ready') return;
  const visibleBots = state.bots.filter(item => item.status !== 'archived');
  if (state.botsUnavailable) {
    const failure = el('section', 'panel empty-state');
    appendText(failure, 'h2', '', 'Your configurations could not be loaded.');
    appendText(failure, 'p', '', 'This does not mean your workspace is empty. Try loading it again.');
    const retry = el('button', 'button button-dark', 'Reload configurations'); retry.dataset.action = 'refresh-bots'; failure.append(retry); main.append(failure);
  } else if (!visibleBots.length) {
    const empty = el('section', 'panel empty-state');
    empty.innerHTML = '<span class="empty-symbol" aria-hidden="true">⌘</span><h2>Great strategies start as ideas.</h2><p>Choose a market, set your budget and give your strategy a name. Your first configuration will appear here.</p><button class="button button-dark" data-action="new-bot">Create your first bot <span aria-hidden="true">↗</span></button>'; main.append(empty);
  } else {
    const list = el('div', 'bot-list');
    for (const bot of visibleBots) {
      const card = el('article', 'panel bot-card'); const top = el('div', 'bot-card-header');
      const detail = el('div'); appendText(detail, 'h3', '', bot.name); appendText(detail, 'small', '', `${bot.coin} · ${bot.venue === 'jupiter' ? 'Jupiter' : 'Coinbase'} · ${bot.status || 'configured'}`);
      top.append(el('span', 'coin-icon', coinSymbols[bot.coin] || '◎'), detail); card.append(top);
      const grid = el('div', 'metric-grid');
      for (const [name, value] of [['Paper capital', currency(bot.budget ?? bot.capital)], ['Leverage', `${bot.leverage || 1}×`], ['Mode', bot.automation?.enabled ? 'Automated spot' : 'Paper']]) { const metric = el('div', 'metric'); metric.append(el('small', '', name), el('strong', '', value)); grid.append(metric); }
      card.append(grid); appendText(card, 'p', '', bot.blockedReason || bot.blocked_reason || 'Saved configuration. A verified per-account executor is required before this bot can run.');
      const actions = el('div', 'bot-card-actions');
      for (const [label, status] of [['Pause', 'paused'], ['Archive', 'archived']]) { const button = el('button', 'button button-outline', label); button.dataset.botId = bot.id; button.dataset.botStatus = status; actions.append(button); }
      if (bot.venue === 'coinbase') { const automation = el('button', 'button button-outline', 'Automation & authorization'); automation.type = 'button'; automation.addEventListener('click', () => openAutomation(bot)); actions.append(automation); }
      card.append(actions); list.append(card);
    }
    main.append(list);
  }
  if (state.botsNextPage !== null && !state.botsUnavailable) { const more = el('button', 'button button-outline', 'Load more configurations'); more.dataset.action = 'more-bots'; main.append(more); }
  const note = el('div', 'info-strip'); note.append(el('span', '', 'ⓘ'), el('span', '', 'Connecting a wallet does not authorize trading. Configurations do not move funds. Live execution requires separate venue authorization and verified risk controls.')); main.append(note);
  const current = usagePanel(); if (current) main.append(current);
}
function populateSelects(root = document) {
  for (const select of $$('[data-coin-select]', root)) {
    const chosen = select.value || state.coin; select.replaceChildren();
    for (const coin of state.config.coins) { const option = el('option', '', `${coin} · ${coinNames[coin] || coin}`); option.value = coin; select.append(option); } select.value = state.config.coins.includes(chosen) ? chosen : state.coin;
  }
  if (state.strategies.length) for (const select of $$('[data-strategy-select]', root)) {
    const chosen = select.value; select.replaceChildren();
    for (const item of state.strategies) { const option = el('option', '', item.name || strategyLabels[item.id] || item.id); option.value = item.id; select.append(option); }
    if ([...select.options].some(option => option.value === chosen)) select.value = chosen;
  }
}
async function openAutomation(bot) {
  if (!accountActionReady() || !state.user) return;
  const context = accountContext(); const navigation = state.navigationEpoch;
  const wallet = state.user.wallet;
  const dialog = el('dialog', 'automation-dialog'); dialog.setAttribute('aria-label', 'Managed bot authorization');
  const close = el('button', 'icon-button', '×'); close.type = 'button'; close.setAttribute('aria-label', 'Close automation'); close.addEventListener('click', () => dialog.close());
  dialog.append(close, el('h2', '', `${bot.name} automation`));
  appendText(dialog, 'p', '', 'Approve a limited trading session once. This bot uses your verified Coinbase connection and sells only inventory recorded from its own fills.');
  const status = appendText(dialog, 'p', 'form-message', 'Checking authorization…');
  const form = el('form');
  form.innerHTML = '<label>Coinbase connection<select name="connectionId" required></select></label><label>Closed bar interval<select name="interval"><option value="1m">1 minute</option><option value="5m">5 minutes</option><option value="15m">15 minutes</option><option value="1h" selected>1 hour</option><option value="6h">6 hours</option><option value="1d">1 day</option></select></label><label>Maximum per trade, USD<input name="maxTradeUsd" type="number" min="0.01" max="1000000" step="0.01" required></label><label>Maximum cumulative trading, USD<input name="maxTotalUsd" type="number" min="0.01" max="1000000" step="0.01" required></label><label>Authorization duration<select name="days"><option value="1">1 day</option><option value="7" selected>7 days</option><option value="30">30 days</option></select></label><label>Signing wallet<select name="provider"><option value="phantom">Phantom</option><option value="solflare">Solflare</option></select></label>';
  $('[name="maxTradeUsd"]', form).value = String(bot.budget);
  $('[name="maxTotalUsd"]', form).value = String(Math.min(1000000, bot.budget * 10));
  const submit = el('button', 'button button-dark', 'Authorize and start'); submit.type = 'submit'; submit.disabled = true;
  form.append(submit); dialog.append(form);
  appendText(dialog, 'p', 'fine-print', 'Limits include fees and count buys and sells. Expiry or exhausted authority can prevent an exit. Pausing revokes authorization and does not close positions. Your wallet will show the exact strategy revision, connection, limits and expiry.');
  document.body.append(dialog); dialog.showModal();
  dialog.addEventListener('close', () => dialog.remove(), { once: true });
  const current = () => currentAccount(context) && state.navigationEpoch === navigation && dialog.isConnected && dialog.open;
  const snapshot = () => JSON.stringify(Object.fromEntries(new FormData(form)));
  try {
    const automation = await api(`/api/bots/${bot.id}/automation`, {}, context.userId);
    if (!current()) return;
    status.textContent = automation.configured ? `${automation.enabled ? 'Enabled' : 'Paused or expired'} · bot-owned ${automation.allocationQuantity} ${bot.coin} · ${automation.reason}${automation.pendingIntentId ? ' · reconciliation pending' : ''}` : 'No trading authority has been granted.';
    if (!state.config.managedAutomationConfigured) { status.textContent += ' Automated trading is awaiting hosted launch verification.'; return; }
    const connections = await api('/api/connections', {}, context.userId); if (!current()) return;
    for (const connection of connections.connections || []) if (connection.status === 'verified') { const option = el('option', '', `Coinbase · ${connection.portfolioId}`); option.value = connection.id; $('[name="connectionId"]', form).append(option); }
    submit.disabled = !$('[name="connectionId"]', form).value;
    if (submit.disabled) status.textContent += ' Connect Coinbase in Settings first.';
  } catch (error) { if (current()) status.textContent = errorText(error); }
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (!current() || submit.disabled) return;
    const values = Object.fromEntries(new FormData(form)); const frozen = snapshot();
    const provider = values.provider === 'phantom' ? window.phantom?.solana || (window.solana?.isPhantom ? window.solana : null) : window.solflare;
    if (!provider?.signMessage || provider.publicKey?.toString() !== wallet) { status.textContent = 'Unlock the signing wallet for your signed-in account before authorizing this bot.'; return; }
    setBusy(submit, true);
    try {
      const policy = { version: 2, venues: ['coinbase'], assets: [bot.coin], products: ['spot'], maxLeverage: 1, maxTradeUsd: Number(values.maxTradeUsd), maxTotalUsd: Number(values.maxTotalUsd), expiresAt: Math.floor(Date.now() / 1000) + Number(values.days) * 86400 };
      const challenge = await api(`/api/bots/${bot.id}/automation/challenge`, { method: 'POST', body: JSON.stringify({ connectionId: values.connectionId, interval: values.interval, policy }) }, context.userId);
      if (!current() || snapshot() !== frozen || provider.publicKey?.toString() !== wallet) return;
      const expected = policy;
      if (JSON.stringify(challenge.policy) !== JSON.stringify(expected) || challenge.config?.asset !== bot.coin || challenge.config.strategyId !== bot.strategy || challenge.config.budgetUsd !== bot.budget || !/^[a-f0-9]{64}$/.test(challenge.config.strategyRevision || '') || typeof challenge.message !== 'string' || !challenge.message.includes(`Wallet: ${wallet}\n`) || !challenge.message.includes(`Customer connection: ${values.connectionId}\n`)) throw new Error('The authorization does not match the selected bot and limits.');
      status.textContent = 'Review and sign the limited bot authorization in your wallet.';
      const signed = await provider.signMessage(new TextEncoder().encode(challenge.message), 'utf8');
      if (!current() || snapshot() !== frozen || provider.publicKey?.toString() !== wallet) return;
      const signature = btoa(String.fromCharCode(...new Uint8Array(signed.signature || signed)));
      const result = await api(`/api/bots/${bot.id}/automation`, { method: 'POST', body: JSON.stringify({ challengeId: challenge.challengeId, signature }) }, context.userId);
      if (current()) status.textContent = result.enabled ? 'Authorization saved. The bot will evaluate fresh, closed strategy bars.' : 'Authorization saved; check status before assuming the bot is running.';
    } catch (error) { if (current()) status.textContent = errorText(error); }
    finally { if (current()) setBusy(submit, false); }
  });
}
function backtestView() {
  main.innerHTML = heading('THE LAB, BEFORE THE MARKET', 'Let the evidence speak.', 'Run a historical simulation with the same canonical engine used by the local research tools. Costs stay in the calculation.');
  const grid = el('div', 'backtest-grid');
  grid.innerHTML = '<section class="panel form-panel"><h3>Design your experiment.</h3><form id="backtest-form"><div class="form-grid"><label>Coin<select name="coin" data-coin-select></select></label><label>Bar interval<select name="interval"><option value="1h">1 hour</option><option value="1d">1 day</option><option value="1m">1 minute</option></select></label></div><label>Strategy<select name="strategy" data-strategy-select><option value="ema_crossover">Moving average crossover</option><option value="rsi">RSI</option><option value="bb_reversion">Bollinger reversion</option><option value="grid">Grid</option></select></label><div class="form-grid"><label>Starting capital (USD)<input type="number" name="capital" min="10" max="1000000" step="0.01" value="1000" required></label><label>Leverage<select name="leverage"><option value="1">1×</option><option value="2">2×</option><option value="3">3×</option><option value="5">5×</option></select></label></div><div class="inline-note">Historical, cached bars only. Fees, slippage and perpetual borrowing costs remain part of the engine model.</div><p id="backtest-message" class="form-message" role="status"></p><button type="submit" class="button button-dark button-full">Run backtest <span aria-hidden="true">↗</span></button></form></section><section class="panel backtest-output" id="backtest-output" aria-live="polite"><div class="empty-state"><span class="empty-symbol" aria-hidden="true">⌁</span><h2>Every hypothesis deserves a test.</h2><p>Your costed simulation, performance metrics and available equity history will appear here. We never fill gaps with estimated results.</p><span class="tiny-label">SIMULATION ONLY</span></div></section>';
  main.append(grid); populateSelects(grid);
  const current = usagePanel(); if (current) main.append(current);
  if (state.config.durableBacktests && state.user) recentBacktests(accountContext(), state.navigationEpoch);
}
async function followBacktest(job, context, current, message) {
  for (let attempt = 0; attempt < 120 && current(); attempt += 1) {
    if (job.status === 'complete') return job.result;
    if (job.status === 'failed') throw new Error('This calculation could not complete. Its daily credit was released.');
    message.textContent = job.status === 'running' ? 'Calculation running. You can leave this page; the job is saved.' : 'Your calculation is queued and saved.';
    await new Promise(resolve => setTimeout(resolve, 1500));
    if (!current()) return null;
    job = await api(`/api/backtest-jobs/${job.id}`, {}, context.userId);
  }
  if (current()) message.textContent = 'Your job is saved. Use Recent calculations to check it again.';
  return null;
}
async function recentBacktests(context, navigation) {
  const panel = el('section', 'panel'); appendText(panel, 'h3', '', 'Recent calculations');
  const message = appendText(panel, 'p', 'muted', 'Loading saved jobs…'); main.append(panel);
  const current = () => currentAccount(context) && state.navigationEpoch === navigation && panel.isConnected;
  try {
    const response = await api('/api/backtest-jobs', {}, context.userId);
    if (!current()) return;
    message.textContent = response.jobs.length ? 'Saved calculations continue when you leave this page.' : 'Your saved calculations will appear here.';
    for (const job of response.jobs.slice(0, 20)) {
      const row = el('div', 'info-strip');
      const label = el('span', '', `${job.request.coin} · ${job.request.strategy.replaceAll('_', ' ')} · ${job.request.interval} · ${job.status}`);
      const button = el('button', 'button button-outline', job.status === 'complete' ? 'View result' : job.status === 'failed' ? 'View status' : 'Check progress');
      button.type = 'button';
      button.addEventListener('click', async () => {
        if (!current()) return; setBusy(button, true);
        try {
          const latest = await api(`/api/backtest-jobs/${job.id}`, {}, context.userId);
          if (!current()) return;
          const result = await followBacktest(latest, context, current, label);
          if (result && current()) renderBacktest(result);
        } catch (error) { if (current()) label.textContent = errorText(error); }
        finally { setBusy(button, false); }
      });
      row.append(label, button); panel.append(row);
    }
  } catch (error) { if (current()) message.textContent = errorText(error); }
}
function renderBacktest(result) {
  const output = $('#backtest-output'); if (!output) return;
  output.replaceChildren(); appendText(output, 'p', 'eyebrow', 'HISTORICAL SIMULATION'); appendText(output, 'h2', '', 'Results, with context.');
  const metrics = result.metrics || result.result?.metrics || {};
  const fields = [['Return', metrics.total_return ?? metrics.return ?? metrics.return_pct, 'percent'], ['Max drawdown', metrics.max_drawdown ?? metrics.max_drawdown_pct, 'percent'], ['Sharpe ratio', metrics.sharpe ?? metrics.sharpe_ratio, 'number'], ['Trades', metrics.n_trades ?? metrics.trades ?? metrics.trade_count, 'number'], ['Final equity', metrics.final_equity ?? result.finalEquity, 'currency'], ['Trading fees', metrics.total_fees, 'currency'], ['Borrowing costs', metrics.total_borrow_fees, 'currency']];
  const grid = el('div', 'metric-grid');
  for (const [name, value, format] of fields) {
    if (value === undefined || value === null) continue;
    const cell = el('div', 'metric'); let formatted = displayNumber(value);
    if (format === 'currency') formatted = currency(value);
    if (format === 'percent' && typeof value === 'number') formatted = `${displayNumber(name === 'Return' && metrics.return_pct !== undefined || name === 'Max drawdown' && metrics.max_drawdown_pct !== undefined ? value : value * 100)}%`;
    cell.append(el('small', '', name), el('strong', '', formatted)); grid.append(cell);
  }
  output.append(grid);
  if (result.costs) {
    appendText(output, 'h3', '', 'Simulation cost assumptions');
    appendText(output, 'p', '', 'Default model costs apply. These are not your verified Coinbase fee tier or a live Jupiter quote.');
    const costs = el('pre', 'source-note', JSON.stringify(result.costs, null, 2)); output.append(costs);
  }
  if (Array.isArray(result.limitations)) for (const limitation of result.limitations) appendText(output, 'p', 'fine-print', limitation.replaceAll('_', ' '));
  const series = result.equity || result.result?.equity || [];
  const numbers = series.map(item => typeof item === 'number' ? item : item.equity ?? item.value).filter(item => typeof item === 'number' && Number.isFinite(item));
  if (numbers.length > 1) {
    const min = Math.min(...numbers), max = Math.max(...numbers), range = max - min || 1;
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.classList.add('equity-chart'); svg.setAttribute('viewBox', '0 0 600 160'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'Historical simulated equity');
    const line = document.createElementNS(svg.namespaceURI, 'polyline'); line.setAttribute('points', numbers.map((value, index) => `${15 + index / (numbers.length - 1) * 570},${145 - (value - min) / range * 130}`).join(' ')); svg.append(line); output.append(svg);
  }
  if (!grid.children.length) appendText(output, 'p', '', result.message || 'The engine returned no reportable performance metrics.');
  const provenance = result.provenance || result.source || result.dataSource;
  if (provenance) appendText(output, 'p', 'fine-print', typeof provenance === 'string' ? provenance : JSON.stringify(provenance));
  appendText(output, 'p', 'result-notes', 'Simulated past performance does not predict future results. Selection bias, limited history and changing execution costs can affect the result.');
}
function renderArticles(container, articles) {
  if (!container) return; container.replaceChildren();
  if (!articles.length) { appendText(container, 'p', 'fine-print', state.articles.length ? 'No articles match your search.' : 'The research journal is being prepared. Check back shortly.'); return; }
  for (const article of articles) {
    const card = el('article', 'article-card'); const meta = el('div', 'article-meta'); meta.append(el('span', '', article.category || 'Research'), el('span', '', article.status?.startsWith('incomplete') ? 'INCOMPLETE' : 'RESEARCH NOTE')); card.append(meta);
    const link = el('a'); link.href = `#research/${encodeURIComponent(article.slug)}`; appendText(link, 'h3', '', article.title); card.append(link);
    appendText(card, 'p', '', article.summary || 'Explore the methods, assumptions and limitations in this research note.');
    const read = el('a', 'text-link', 'Read the note'); read.href = link.href; read.append(el('span', '', '↗')); card.append(read); container.append(card);
  }
}
function researchView() {
  main.innerHTML = heading('WORKING NOTES. OPEN QUESTIONS.', 'From the research desk.', 'The thinking behind the signals. Explore the studies, strategy cards and experiments in the research library. Historical findings retain their original limitations.');
  const filters = el('div', 'filter-bar'); const search = el('input'); search.type = 'search'; search.placeholder = 'Search the research library…'; search.setAttribute('aria-label', 'Search research'); search.id = 'research-search'; search.value = state.search;
  const select = el('select'); select.id = 'research-category'; select.setAttribute('aria-label', 'Filter by category');
  const all = el('option', '', 'All categories'); all.value = 'all'; select.append(all);
  for (const category of [...new Set(state.articles.map(item => item.category).filter(Boolean))].sort()) { const option = el('option', '', category); option.value = category; select.append(option); }
  select.value = state.category; filters.append(search, select, el('span', 'research-count')); main.append(filters, el('div', 'journal-grid full', '')); $('.journal-grid', main).id = 'research-list'; filterResearch();
}
function filterResearch() {
  const query = state.search.trim().toLowerCase();
  const articles = state.articles.filter(item => (state.category === 'all' || item.category === state.category) && (!query || `${item.title} ${item.summary} ${item.category}`.toLowerCase().includes(query)));
  renderArticles($('#research-list'), articles); const count = $('.research-count'); if (count) count.textContent = `${articles.length} ${articles.length === 1 ? 'NOTE' : 'NOTES'}`;
}
function inlineMarkdown(text, parent) {
  const pattern = /\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  let start = 0, match;
  while ((match = pattern.exec(text))) {
    parent.append(document.createTextNode(text.slice(start, match.index)));
    if (match[1]) {
      const href = match[2];
      if (/^https?:\/\//i.test(href)) { const link = el('a', '', match[1]); link.href = href; link.rel = 'noopener noreferrer'; link.target = '_blank'; parent.append(link); }
      else parent.append(document.createTextNode(match[1]));
    } else parent.append(el(match[3] ? 'code' : match[4] ? 'strong' : 'em', '', match[3] || match[4] || match[5]));
    start = pattern.lastIndex;
  }
  parent.append(document.createTextNode(text.slice(start)));
}
function markdown(body, parent) {
  const lines = String(body || '').split('\n'); let code = null, paragraph = [], list = null;
  const flush = () => { if (paragraph.length) { const p = el('p'); inlineMarkdown(paragraph.join(' '), p); parent.append(p); paragraph = []; } list = null; };
  for (const line of lines) {
    if (/^```/.test(line)) { flush(); if (code) { parent.append(code); code = null; } else code = el('pre'); continue; }
    if (code) { code.append(document.createTextNode(`${line}\n`)); continue; }
    if (!line.trim()) { flush(); continue; }
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) { flush(); const tag = `h${Math.min(headingMatch[1].length + 1, 6)}`; const h = el(tag); inlineMarkdown(headingMatch[2], h); parent.append(h); continue; }
    const listMatch = line.match(/^\s*(?:[-*+]\s+|\d+\.\s+)(.+)$/);
    if (listMatch) { if (paragraph.length) flush(); if (!list) { list = el(/^\s*\d/.test(line) ? 'ol' : 'ul'); parent.append(list); } const item = el('li'); inlineMarkdown(listMatch[1], item); list.append(item); continue; }
    if (/^\s*---\s*$/.test(line)) { flush(); parent.append(el('hr')); continue; }
    paragraph.push(line);
  }
  flush(); if (code) parent.append(code);
}
async function articleView(slug) {
  const article = state.articles.find(item => item.slug === slug);
  main.replaceChildren(); const wrapper = el('article', 'article-reading'); const back = el('a', 'text-link', '← Back to the journal'); back.href = '#research'; wrapper.append(back); main.append(wrapper);
  if (!article) { appendText(wrapper, 'h1', '', 'This note is unavailable.'); appendText(wrapper, 'p', '', 'Return to the research journal to find an available article.'); return; }
  appendText(wrapper, 'p', 'eyebrow', article.category || 'RESEARCH'); appendText(wrapper, 'h1', '', article.title);
  appendText(wrapper, 'p', 'article-provenance', `Source: ${article.source || 'Research library'} · ${article.status || 'Historical research'}${article.sourceSha256 || article.sha256 ? ` · Source SHA-256 ${article.sourceSha256 || article.sha256}` : ''}`);
  const body = el('div', 'article-body'); wrapper.append(body); appendText(body, 'p', '', 'Loading the original research note…');
  try {
    let content = article.body;
    if (content === undefined && article.bodyPath) {
      if (!/^\/research\/(?:bodies-[a-zA-Z0-9_-]+|articles\/[a-zA-Z0-9_-]+)\.json$/.test(article.bodyPath)) throw new Error('This article has an unsupported content path.');
      if (!researchShards.has(article.bodyPath)) researchShards.set(article.bodyPath, api(article.bodyPath).catch(error => { researchShards.delete(article.bodyPath); throw error; }));
      const response = await researchShards.get(article.bodyPath); content = article.bodyKey ? response.articles?.[article.bodyKey]?.body : response.body;
    }
    if (state.view !== 'research' || location.hash !== `#research/${encodeURIComponent(slug)}`) return;
    body.replaceChildren(); markdown(content || 'The full text is not available yet.', body);
  } catch (error) { body.replaceChildren(el('p', 'form-message', errorText(error))); }
}
function usagePanel() {
  const current = state.usage;
  if (!current?.policy) return null;
  const panel = el('section', 'panel usage-panel');
  panel.setAttribute('aria-label', 'Membership usage');
  appendText(panel, 'h3', '', `${current.policy.name} usage`);
  const bots = current.policy.botLimit === null ? `${current.bots} configured · unlimited bot slots` : `${current.bots} of ${current.policy.botLimit} configured bot slots`;
  const tests = current.policy.backtestsPerDay === null ? `${current.backtests} completed today · unlimited backtests` : `${current.backtests} of ${current.policy.backtestsPerDay} backtests completed today`;
  appendText(panel, 'p', '', bots);
  appendText(panel, 'p', '', `${tests}${current.reservedBacktests ? ` · ${current.reservedBacktests} in progress` : ''}. Resets at 00:00 UTC.`);
  if (current.policy.botLimit !== null && current.bots > current.policy.botLimit) appendText(panel, 'p', 'fine-print', 'Your saved configurations exceed this plan’s slots. You can read, pause or archive them. Free a slot before creating another configuration.');
  appendText(panel, 'p', 'fine-print', 'Configured bots reserve slots; execution is unavailable. Paused and archived configurations do not reserve slots. All plans keep per-run input, resource and concurrency limits.');
  return panel;
}
function pricingView() {
  main.innerHTML = heading('ROOM TO THINK. TOOLS TO TEST.', 'A more considered approach.', 'Choose the room your research needs. Seven days free on your first eligible subscription; then billed monthly in USD.');
  const grid = el('div', 'pricing-grid tier-grid');
  const plans = Array.isArray(state.config.plans) ? state.config.plans : [];
  for (const plan of plans) {
    const card = el('section', 'pricing-card'); card.dataset.plan = plan.id;
    appendText(card, 'p', 'eyebrow', 'ORACLEBOT MEMBERSHIP');
    const title = appendText(card, 'h2', '', plan.name); title.id = `plan-${plan.id}`; card.setAttribute('aria-labelledby', title.id);
    const price = appendText(card, 'div', 'pricing-big', currency(plan.monthlyUsd)); price.append(el('small', '', ' USD / month before applicable tax'));
    const features = el('ul', 'plan-features');
    features.append(el('li', '', plan.botLimit === null ? 'Unlimited bot slots' : `Up to ${plan.botLimit} configured bot slots`), el('li', '', plan.backtestsPerDay === null ? 'Unlimited backtests' : `${plan.backtestsPerDay} backtests per day (UTC)`), el('li', '', 'Research journal and strategy workspace'));
    card.append(features);
    appendText(card, 'p', '', 'Configured bots reserve slots; live execution is unavailable.');
    const subscribed = state.subscription && !['canceled', 'incomplete_expired'].includes(state.subscription.status);
    const samePlan = subscribed && state.subscription.plan?.id === plan.id;
    const canChange = subscribed && state.subscription.entitled && state.config.billingPlanChanges;
    const button = el('button', 'button button-lime button-full', samePlan ? 'Current plan' : canChange ? 'Review plan change' : subscribed ? 'Manage membership' : state.config.billingConfigured === true ? (state.subscription ? 'Continue to Checkout' : 'Start your free trial') : 'Trial signup unavailable');
    button.dataset.action = canChange && !samePlan ? 'change-plan' : subscribed ? 'portal' : 'trial'; button.dataset.plan = plan.id;
    button.disabled = samePlan || (!subscribed && state.config.billingConfigured !== true);
    button.setAttribute('aria-label', `${button.textContent} — ${plan.name}`); card.append(button);
    appendText(card, 'p', 'fine-print', 'Seven-day trial for eligible first subscriptions. Stripe shows applicable taxes and renewal terms before confirmation. Cancel through the billing portal.');
    grid.append(card);
  }
  if (!plans.length) appendText(grid, 'p', '', 'Membership plans are unavailable. Please try again later.');
  main.append(grid);
  const current = usagePanel(); if (current) main.append(current);
  const note = el('div', 'info-strip');
  note.append(el('span', '', 'ⓘ'), el('span', '', state.config.billingConfigured === true ? 'All plans retain risk controls and bounded backtest resources. A membership does not authorize trading.' : 'Membership checkout is being configured. No payment is collected and no trial starts until you complete Stripe Checkout. The research journal is available to browse now.'));
  main.append(note);
  if (state.portalAvailable || state.subscription?.status) { const portal = el('button', 'button button-outline', 'Manage or cancel membership'); portal.dataset.action = 'portal'; main.append(portal); }
}
function settingsView() {
  main.innerHTML = heading('YOUR WORKSPACE, YOUR TERMS', 'The details that matter.', 'Manage your account, membership and permissions. Keep your keys in your wallet.');
  const grid = el('div', 'settings-grid');
  const account = el('section', 'panel'); appendText(account, 'h3', '', 'Your account'); appendText(account, 'p', '', state.accountStatus !== 'ready' ? 'Your current wallet session has not been established.' : state.user ? 'Signed in using a verified wallet signature.' : 'Connect a Solana wallet and sign a one-time message to access your account.');
  if (state.user) appendText(account, 'span', 'settings-value', state.user.wallet);
  const accountButton = el('button', 'button button-outline', state.accountStatus !== 'ready' ? 'Retry account check' : state.user ? 'Sign out' : 'Connect wallet'); accountButton.dataset.action = state.accountStatus !== 'ready' ? 'refresh-account' : state.user ? 'logout' : 'wallet'; accountButton.disabled = state.accountStatus === 'loading'; account.append(accountButton);
  if (state.user) { const remove = el('button', 'button button-outline', 'Delete account'); remove.dataset.action = 'delete-account'; account.append(remove); appendText(account, 'p', 'fine-print', 'Deletes your account and saved configurations. Cancel subscriptions and finish or expire pending checkout first. A hashed trial-use record prevents repeat free trials.'); }
  const billing = el('section', 'panel'); appendText(billing, 'h3', '', 'Membership & billing'); appendText(billing, 'p', '', state.subscription?.status ? `Subscription status: ${state.subscription.status}. Manage payment details and cancellation through Stripe.` : 'No active subscription is recorded. The seven-day trial starts only after successful Stripe Checkout.');
  const canManage = state.portalAvailable || state.subscription?.status;
  const billingButton = el('button', 'button button-outline', canManage ? 'Manage or cancel membership' : 'Explore membership'); billingButton.dataset.action = canManage ? 'portal' : 'pricing'; billing.append(billingButton);
  const permissions = el('section', 'panel'); permissions.innerHTML = '<h3>Wallet & execution permissions</h3><p>Your sign-in signature only proves ownership of your wallet. It does not approve a transaction or grant spending permissions.</p><p>Bot configurations start in paper mode. Live Coinbase trading and Jupiter leveraged execution require separately provisioned, verified account connections.</p>';
  const risk = el('section', 'panel'); risk.innerHTML = '<h3>Risk & privacy</h3><p>Trading can result in loss. Leverage increases losses and can lead to liquidation. Past or simulated performance does not predict future results.</p><p>Your account stores your public wallet address, sessions, bot configurations and subscription references. Payment details are handled by Stripe. Never enter a wallet private key or seed phrase. Dedicated Coinbase trade-only API credentials use the account connection form.</p><p>Session cookies support sign-in. This workspace does not use advertising trackers.</p>';
  grid.append(account, billing, permissions, risk); main.append(grid);
  if (state.user && state.config.billingPlanChanges) membershipChanges(billing);
  if (state.user && state.accountStatus === 'ready') connectionSettings(permissions);
  const agents = el('div', 'agent-settings'); main.append(agents);
  if (state.accountStatus === 'ready' || state.accountTransition) agentAccess.mount(agents);
  else appendText(agents, 'p', 'fine-print', 'Agent access becomes available after your account is checked.');
  const current = usagePanel(); if (current) main.append(current);
}
async function reviewPlanChange(button) {
  if (!accountActionReady() || !state.user || !state.config.billingPlanChanges) return;
  const context = accountContext(); const navigation = state.navigationEpoch;
  const current = () => currentAccount(context) && state.navigationEpoch === navigation && button.isConnected;
  setBusy(button, true);
  try {
    const quote = await api('/api/billing/plan-change/quote', { method: 'POST', body: JSON.stringify({ plan: button.dataset.plan }) }, context.userId);
    if (!current()) return;
    if (quote.targetPlan !== button.dataset.plan || !['upgrade', 'downgrade'].includes(quote.kind) || quote.currency !== 'usd' ||
        !Number.isSafeInteger(quote.amountDueNowCents) || quote.amountDueNowCents < 0 || !Number.isSafeInteger(quote.renewalAmountCents) || quote.renewalAmountCents <= 0 || !Number.isSafeInteger(quote.effectiveAt) || typeof quote.quoteId !== 'string') throw new Error('The billing quote could not be verified.');
    $('#plan-change-dialog')?.remove();
    const dialog = el('dialog', 'plan-change-dialog'); dialog.id = 'plan-change-dialog';
    const content = el('div', 'panel'); content.append(el('h2', '', `Review ${quote.kind}`));
    appendText(content, 'p', '', `${quote.targetPlan} base rate: ${currency(quote.renewalAmountCents / 100)} USD per month${quote.renewalAmountExcludesTax === true ? ' + applicable tax' : ''}. Stripe confirms the renewal total.`);
    appendText(content, 'p', '', `Due now: ${currency(quote.amountDueNowCents / 100)} USD, including any tax in this quote.`);
    appendText(content, 'p', '', quote.kind === 'downgrade' ? `Your current plan continues until ${new Date(quote.effectiveAt * 1000).toLocaleString()}. The lower rate starts then.` : 'The change takes effect after any required payment is confirmed. Your original trial end does not move.');
    const message = el('p', 'form-message'); message.setAttribute('role', 'status');
    const confirm = el('button', 'button button-dark', 'Confirm this change'); confirm.type = 'button';
    const cancel = el('button', 'button button-outline', 'Keep current plan'); cancel.type = 'button'; cancel.addEventListener('click', () => dialog.remove());
    const usable = () => current() && dialog.isConnected;
    confirm.addEventListener('click', async () => {
      if (!usable()) return; setBusy(confirm, true); cancel.disabled = true;
      try {
        const operation = await api('/api/billing/plan-change/commit', { method: 'POST', body: JSON.stringify({ quoteId: quote.quoteId, idempotencyKey: crypto.randomUUID() }) }, context.userId);
        if (!usable()) return;
        dialog.remove();
        toast(operation.status === 'scheduled' ? 'Downgrade scheduled for the next billing period.' : operation.status === 'applied' ? 'Plan change verified. Membership access follows Stripe confirmation.' : 'Your change is saved and awaiting provider verification. Check it in Settings.');
        if (await refreshAccount() && currentAccount(context)) { location.hash = 'settings'; render(); }
      } catch (error) { if (usable()) message.textContent = `${errorText(error)} If the response was interrupted, check saved changes in Settings before trying again.`; }
      finally { setBusy(confirm, false); cancel.disabled = false; }
    });
    content.append(message, confirm, cancel); dialog.append(content); main.append(dialog); dialog.showModal();
  } catch (error) { if (current()) toast(errorText(error)); }
  finally { setBusy(button, false); }
}
async function membershipChanges(panel) {
  const context = accountContext(); const navigation = state.navigationEpoch;
  const current = () => currentAccount(context) && state.navigationEpoch === navigation && panel.isConnected;
  const section = el('div', 'membership-changes'); section.append(el('h4', '', 'Saved membership changes')); panel.append(section);
  const message = appendText(section, 'p', 'fine-print', 'Loading saved changes…');
  try {
    const result = await api('/api/billing/plan-changes', {}, context.userId); if (!current()) return;
    message.textContent = result.changes.length ? 'A saved operation is reconciled before another provider write.' : 'No pending changes.';
    for (const change of result.changes.slice(0, 10)) {
      const row = el('div', 'info-strip'); const label = el('span', '', `${change.kind.replaceAll('_', ' ')} · ${change.status}`); row.append(label);
      const refresh = el('button', 'button button-outline', 'Check status'); refresh.type = 'button';
      refresh.addEventListener('click', async () => {
        if (!current()) return; setBusy(refresh, true);
        try {
          const value = await api(`/api/billing/plan-changes/${change.changeId}`, {}, context.userId);
          if (current()) { label.textContent = `${value.kind.replaceAll('_', ' ')} · ${value.status}${value.requiresPayment ? ' · payment required in the billing portal' : ''}`; await refreshAccount(); }
        } catch (error) { if (current()) label.textContent = errorText(error); }
        finally { setBusy(refresh, false); }
      }); row.append(refresh);
      if (change.status === 'scheduled' && change.kind === 'plan_change') {
        const undo = el('button', 'button button-outline', 'Cancel scheduled downgrade'); undo.type = 'button';
        undo.addEventListener('click', async () => {
          if (!current()) return; setBusy(undo, true);
          try {
            const value = await api(`/api/billing/plan-changes/${change.changeId}/cancel`, { method: 'POST', body: JSON.stringify({ idempotencyKey: crypto.randomUUID() }) }, context.userId);
            if (current()) { label.textContent = `Downgrade undo · ${value.status}`; undo.remove(); }
          } catch (error) { if (current()) label.textContent = errorText(error); }
          finally { setBusy(undo, false); }
        }); row.append(undo);
      }
      section.append(row);
    }
  } catch (error) { if (current()) message.textContent = errorText(error); }
}
function clearConnectionCredentials() { for (const input of $$('.connection-form input[type="password"]')) input.value = ''; }
function coinbaseSecret(value) {
  if (value.length > 4096) throw new Error('Invalid Coinbase credential.');
  // Password inputs strip pasted line breaks. Restore only a recognized PEM envelope.
  const match = /^-----BEGIN (EC PRIVATE KEY|PRIVATE KEY)-----([A-Za-z0-9+/=\s]+)-----END \1-----$/.exec(value.trim().replace(/\\r\\n|\\n|\\r/g, '\n'));
  if (!match) throw new Error('Invalid Coinbase credential.');
  const pem = `-----BEGIN ${match[1]}-----\n${match[2].replace(/\s/g, '')}\n-----END ${match[1]}-----`;
  if (pem.length > 4096) throw new Error('Invalid Coinbase credential.');
  return pem;
}
function connectionSettings(panel) {
  const context = accountContext(); const navigation = state.navigationEpoch;
  const current = () => currentAccount(context) && state.navigationEpoch === navigation && panel.isConnected;
  appendText(panel, 'h4', '', 'Connect a Coinbase portfolio');
  appendText(panel, 'p', '', 'Enter a dedicated Coinbase ECDSA API key with View and Trade permissions only. Transfer permission is refused. Connecting an account does not start a bot or approve an agent policy.');
  const form = el('form', 'connection-form');
  form.autocomplete = 'off';
  const keyLabel = el('label', '', 'Key ID'); const keyId = el('input');
  const secretLabel = el('label', '', 'Secret'); const secret = el('input');
  for (const [input, name, limit] of [[keyId, 'coinbase-key-id', 256], [secret, 'coinbase-key-secret', 4096]]) {
    input.type = 'password'; input.name = name; input.required = true; input.maxLength = limit;
    input.autocomplete = 'off'; input.spellcheck = false; input.setAttribute('autocapitalize', 'none');
  }
  keyLabel.append(keyId); secretLabel.append(secret);
  const portfolioLabel = el('label', '', 'Dedicated portfolio ID (optional)'); const portfolio = el('input'); portfolio.name = 'portfolio'; portfolio.autocomplete = 'off'; portfolioLabel.append(portfolio);
  const submit = el('button', 'button button-outline', 'Verify and connect'); submit.type = 'submit';
  submit.disabled = !state.config.customerConnectionsConfigured;
  keyId.disabled = submit.disabled; secret.disabled = submit.disabled; portfolio.disabled = submit.disabled;
  const message = el('p', 'form-message'); message.setAttribute('role', 'status');
  if (submit.disabled) message.textContent = 'Customer account connections are not available yet.';
  form.append(keyLabel, secretLabel, portfolioLabel, submit, message); panel.append(form);
  appendText(panel, 'p', 'fine-print', 'Use the complete Key ID (organizations/…/apiKeys/…) and its ECDSA private-key Secret, including the BEGIN and END lines. No file is required. Never enter a wallet seed phrase or primary wallet private key. API credentials are encrypted on the server; these fields are cleared when submitted. Use Coinbase itself to revoke the API key at the venue.');
  const list = el('div', 'connections-list'); panel.append(list);
  async function load(cursor = null) {
    if (!state.config.customerConnectionsConfigured || !current()) return;
    const result = await api(`/api/connections${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`, {}, context.userId); if (!current()) return;
    if (!cursor) list.replaceChildren();
    $('.connection-more', list)?.remove();
    for (const connection of result.connections || []) {
      const row = el('div', 'info-strip');
      row.append(el('span', '', `Coinbase · ${connection.portfolioId} · ${connection.status}`));
      if (connection.status === 'verified') {
        const revoke = el('button', 'button button-outline', 'Revoke platform access'); revoke.type = 'button';
        revoke.addEventListener('click', async () => {
          if (!current()) return; setBusy(revoke, true);
          try {
            await api(`/api/connections/${connection.id}/revoke`, { method: 'POST', body: '{}' }, context.userId);
            if (current()) { message.textContent = 'Platform access revoked. Pending orders retain read-only reconciliation.'; await load(); }
          } catch (error) { if (current()) message.textContent = errorText(error); }
          finally { setBusy(revoke, false); }
        }); row.append(revoke);
      }
      list.append(row);
    }
    if (typeof result.nextCursor === 'string' && result.nextCursor && result.nextCursor !== cursor) {
      const more = el('button', 'button button-outline connection-more', 'Load more connection history'); more.type = 'button';
      more.addEventListener('click', async () => { if (!current()) return; setBusy(more,true); try { await load(result.nextCursor); } catch { if (current()) message.textContent='Connection history could not be loaded. Try again.'; } finally { setBusy(more,false); } }); list.append(more);
    }
  }
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (!current() || submit.disabled) return;
    let apiKeyName = keyId.value.trim(); let privateKey = secret.value; const portfolioId = portfolio.value.trim();
    keyId.value = ''; secret.value = ''; message.textContent = ''; setBusy(submit, true);
    try {
      if (!/^organizations\/[A-Za-z0-9-]{1,64}\/apiKeys\/[A-Za-z0-9-]{1,64}$/.test(apiKeyName)) throw new Error('Invalid Coinbase credential.');
      privateKey = coinbaseSecret(privateKey);
      const input = { venue: 'coinbase', apiKeyName, privateKey, idempotencyKey: crypto.randomUUID() };
      if (portfolioId) input.portfolioId = portfolioId;
      await api('/api/connections', { method: 'POST', body: JSON.stringify(input) }, context.userId);
      if (current()) { message.textContent = 'Trade-only portfolio verified. A separate finite agent authorization is required before trading.'; await load(); }
    } catch { if (current()) message.textContent = 'The Coinbase connection could not be verified. Check that the key has View and Trade permissions and no Transfer permission.'; }
    finally { apiKeyName = ''; privateKey = ''; keyId.value = ''; secret.value = ''; setBusy(submit, false); }
  });
  load().catch(error => { if (current()) message.textContent = errorText(error); });
}
function updateAccountUI() { for (const label of $$('[data-wallet-label]')) label.textContent = state.accountStatus !== 'ready' ? 'Account unchecked' : shortWallet(state.user?.wallet); $('#nav-bot-count').textContent = state.accountStatus !== 'ready' || state.botsUnavailable ? '—' : state.bots.filter(item => item.status !== 'archived').length; }
function render() {
  clearConnectionCredentials();
  agentAccess.invalidate();
  const [rawView, ...rest] = location.hash.slice(1).split('/'); const view = views[rawView] ? rawView : 'overview'; state.view = view;
  $('#page-label').textContent = views[view];
  for (const link of $$('[data-view]')) { const active = link.dataset.view === view; link.classList.toggle('active', active); if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current'); }
  document.title = `${views[view]} · Oraclebot`;
  $('#sidebar').classList.remove('open'); $('#menu-button').setAttribute('aria-expanded', 'false');
  if (view === 'research' && rest.length) { let slug; try { slug = decodeURIComponent(rest.join('/')); } catch { slug = ''; } articleView(slug); }
  else ({ overview, oracle: oracleView, bots: botsView, backtest: backtestView, research: researchView, pricing: pricingView, settings: settingsView })[view]();
  if (state.accountStatus !== 'ready') main.prepend(accountNotice());
  updateAccountUI();
}
async function loadOracle(coin = state.coin) {
  state.coin = coin; state.oracle = null; state.loadingOracle = true; const requestId = ++state.oracleRequest;
  if (state.view === 'overview' || state.view === 'oracle') render();
  try { const response = await api(`/api/oracle?coin=${encodeURIComponent(coin)}`); if (requestId === state.oracleRequest) state.oracle = response; }
  catch (error) { if (requestId === state.oracleRequest) state.oracle = { status: 'unavailable', message: errorText(error), topStrategy: null }; }
  finally { if (requestId === state.oracleRequest) { state.loadingOracle = false; if (state.view === 'overview' || state.view === 'oracle') render(); } }
}
async function refreshAccount({ allowTransition = false } = {}) {
  const context = accountContext(); const requestId = ++state.accountRequest; const previousStatus = state.accountStatus;
  const current = () => state.accountEpoch === context.epoch && state.accountRequest === requestId && (state.user?.id ?? null) === context.userId && state.accountTransition === allowTransition;
  try {
    const result = await api('/api/me', {}, context.userId);
    if (!current()) return false;
    if (!result || !(result.user === null || typeof result.user?.id === 'string' && typeof result.user?.wallet === 'string')) throw new Error('The account service returned an invalid identity.');
    if (context.userId && result.user && result.user.id !== context.userId) throw new Error('The account changed while it was being checked.');
    let bots = []; let botsNextPage = null; let botsUnavailable = false;
    if (result.user) {
      try { const page = await api('/api/bots', {}, result.user.id); bots = page.bots || []; botsNextPage = page.nextPage ?? null; }
      catch (error) { if (error?.code === 'account_changed') throw error; if (current()) { botsUnavailable = true; console.warn('Oraclebot bot list unavailable'); } }
    }
    if (!current()) return false;
    const identityEnded = Boolean(context.userId && !result.user);
    if (identityEnded) { state.accountEpoch++; agentAccess.invalidate(); clearAccount(); }
    Object.assign(state, { user: result.user, subscription: result.subscription, usage: result.usage || null, portalAvailable: result.portalAvailable === true, bots, botsNextPage, botsUnavailable, accountStatus: 'ready' });
    updateAccountUI(); if (!allowTransition && (identityEnded || previousStatus !== 'ready')) render(); return true;
  } catch {
    if (!current()) return false;
    state.accountEpoch++; agentAccess.invalidate(); clearAccount(); state.accountStatus = 'unavailable';
    console.warn('Oraclebot account refresh unavailable'); render(); return false;
  }
}
function openWallet() { $('#wallet-message').textContent = ''; $('#wallet-dialog').showModal(); }
async function connectWallet(name, button) {
  if (state.accountTransition) return;
  const provider = name === 'phantom' ? window.phantom?.solana || (window.solana?.isPhantom ? window.solana : null) : window.solflare;
  if (!provider) { $('#wallet-message').textContent = `No ${name === 'phantom' ? 'Phantom' : 'Solflare'} wallet was detected. Open this site in that wallet’s browser or install its browser extension, then try again.`; return; }
  const context = beginAccountTransition();
  setBusy(button, true); $('#wallet-message').textContent = 'Waiting for your wallet…';
  try {
    const connection = await provider.connect(); const wallet = (connection?.publicKey || provider.publicKey)?.toString();
    if (!wallet) throw new Error('Your wallet did not return a public address.');
    const challenge = await api('/api/auth/challenge', { method: 'POST', body: JSON.stringify({ wallet }) });
    $('#wallet-message').textContent = 'Sign the one-time message in your wallet. No funds will move.';
    const signed = await provider.signMessage(new TextEncoder().encode(challenge.message), 'utf8');
    const bytes = signed.signature || signed; const signature = btoa(String.fromCharCode(...new Uint8Array(bytes)));
    await api('/api/auth/verify', { method: 'POST', body: JSON.stringify({ id: challenge.id, signature }) });
    if (state.accountEpoch !== context.epoch || !state.accountTransition) return;
    const refreshed = await refreshAccount({ allowTransition: true });
    if (!refreshed) return;
    state.accountTransition = false; $('#wallet-dialog').close(); render(); toast('Wallet verified. Welcome to your workspace.');
  } catch (error) {
    if (state.accountEpoch === context.epoch && state.accountTransition) { state.accountStatus = 'unavailable'; $('#wallet-message').textContent = error?.code === 4001 || /reject|cancel/i.test(error?.message || '') ? 'Connection cancelled. You can try again whenever you are ready.' : errorText(error); }
  }
  finally { if (state.accountTransition) { state.accountTransition = false; render(); } setBusy(button, false); }
}
async function billingAction(action, button) {
  if (!accountActionReady()) return;
  if (action === 'checkout' && state.config.billingConfigured !== true) { location.hash = 'pricing'; toast('Stripe Checkout is not available yet. No payment or trial has started.'); return; }
  if (!state.user) { openWallet(); toast('Connect your wallet first to manage your membership.'); return; }
  const context = accountContext(); const navigation = state.navigationEpoch;
  const current = () => currentAccount(context) && state.navigationEpoch === navigation && button.isConnected;
  setBusy(button, true);
  try {
    const result = await api(`/api/billing/${action}`, { method: 'POST', body: JSON.stringify(action === 'checkout' ? { plan: button.dataset.plan } : {}) }, context.userId);
    if (!current()) return;
    const url = new URL(result.url); if (url.protocol !== 'https:' || !(url.hostname === 'checkout.stripe.com' || url.hostname === 'billing.stripe.com')) throw new Error('The billing service returned an unsupported checkout address.');
    location.assign(url.href);
  } catch (error) { if (current()) toast(errorText(error)); } finally { setBusy(button, false); }
}
function openBot() {
  if (!accountActionReady()) return;
  if (!state.user) { openWallet(); toast('Connect your wallet to create a bot configuration.'); return; }
  $('#bot-message').textContent = ''; populateSelects($('#bot-dialog')); $('#bot-dialog').showModal();
}
document.addEventListener('click', async event => {
  const close = event.target.closest('[data-close-dialog]'); if (close) { close.closest('dialog').close(); return; }
  const provider = event.target.closest('[data-provider]'); if (provider) { connectWallet(provider.dataset.provider, provider); return; }
  const coin = event.target.closest('[data-coin]'); if (coin) { loadOracle(coin.dataset.coin); return; }
  const bot = event.target.closest('[data-bot-id]');
  if (bot) {
    if (!accountActionReady() || !state.user) return;
    const context = accountContext(); const navigation = state.navigationEpoch;
    const current = () => currentAccount(context) && state.navigationEpoch === navigation && bot.isConnected;
    setBusy(bot, true);
    try { await api(`/api/bots/${encodeURIComponent(bot.dataset.botId)}`, { method: 'PATCH', body: JSON.stringify({ status: bot.dataset.botStatus }) }, context.userId); if (currentAccount(context) && await refreshAccount() && current()) { render(); toast(`Configuration ${bot.dataset.botStatus}.`); } }
    catch (error) { if (current()) toast(errorText(error)); } finally { setBusy(bot, false); } return;
  }
  const actionButton = event.target.closest('[data-action]'); if (!actionButton) return;
  const action = actionButton.dataset.action;
  if (action === 'wallet') { if (state.accountTransition) { accountActionReady(); return; } if (state.user) location.hash = 'settings'; else openWallet(); }
  if (action === 'refresh-account') {
    if (state.accountTransition || state.accountStatus === 'loading') { accountActionReady(); return; }
    const context = accountContext(); const navigation = state.navigationEpoch; setBusy(actionButton, true);
    try { if (await refreshAccount() && state.accountEpoch === context.epoch && state.navigationEpoch === navigation) render(); } finally { setBusy(actionButton, false); }
  }
  if (action === 'new-bot') openBot();
  if (action === 'more-bots' && state.botsNextPage !== null) {
    if (!accountActionReady() || !state.user) return;
    const context = accountContext(); const navigation = state.navigationEpoch;
    const userId = state.user?.id; const rows = state.bots; const page = state.botsNextPage;
    const current = () => currentAccount(context) && state.navigationEpoch === navigation && state.user?.id === userId && state.bots === rows && state.botsNextPage === page;
    setBusy(actionButton, true);
    try {
      const result = await api(`/api/bots?page=${page}`, {}, context.userId);
      if (current()) {
        state.bots = [...new Map([...rows, ...result.bots].map(bot => [bot.id, bot])).values()];
        state.botsNextPage = result.nextPage ?? null; render();
      }
    } catch (error) { if (current()) toast(errorText(error)); } finally { setBusy(actionButton, false); }
  }
  if (action === 'refresh-bots') {
    if (!accountActionReady()) return;
    const context = accountContext(); const navigation = state.navigationEpoch; setBusy(actionButton, true);
    try { if (await refreshAccount() && currentAccount(context) && state.navigationEpoch === navigation) render(); } finally { setBusy(actionButton, false); }
  }
  if (action === 'trial') billingAction('checkout', actionButton);
  if (action === 'portal') billingAction('portal', actionButton);
  if (action === 'change-plan') reviewPlanChange(actionButton);
  if (action === 'pricing') location.hash = 'pricing';
  if (action === 'delete-account') {
    if (!accountActionReady() || !state.user) return;
    if (!confirm('Delete your Oraclebot account and all saved configurations? This cannot be undone.')) return;
    const context = beginAccountTransition();
    setBusy(actionButton, true);
    try { await api('/api/me', { method: 'DELETE', body: '{}' }, context.userId); if (state.accountEpoch === context.epoch) { state.accountTransition = false; state.accountStatus = 'ready'; render(); toast('Your account and saved configurations were deleted.'); } }
    catch (error) { if (state.accountEpoch === context.epoch) { state.accountTransition = false; state.accountStatus = 'unavailable'; console.warn('Oraclebot account deletion unavailable'); render(); toast(errorText(error)); } } finally { setBusy(actionButton, false); }
  }
  if (action === 'logout') {
    if (!accountActionReady() || !state.user) return;
    const context = beginAccountTransition(); setBusy(actionButton, true);
    try { await api('/api/auth/logout', { method: 'POST', body: '{}' }, context.userId); if (state.accountEpoch === context.epoch) { state.accountTransition = false; state.accountStatus = 'ready'; render(); toast('You are signed out.'); } }
    catch (error) { if (state.accountEpoch === context.epoch) { state.accountTransition = false; state.accountStatus = 'unavailable'; console.warn('Oraclebot sign-out unavailable'); render(); toast(errorText(error)); } } finally { setBusy(actionButton, false); }
  }
});
document.addEventListener('submit', async event => {
  if (!['bot-form', 'backtest-form'].includes(event.target.id)) return;
  event.preventDefault(); const form = event.target; const values = Object.fromEntries(new FormData(form)); const button = $('button[type="submit"]', form); const isBot = form.id === 'bot-form'; const message = $(isBot ? '#bot-message' : '#backtest-message'); message.textContent = '';
  if (!accountActionReady()) return;
  if (!state.user) { openWallet(); message.textContent = 'Connect your wallet before starting this experiment.'; return; }
  const context = accountContext(); const navigation = state.navigationEpoch;
  const current = () => currentAccount(context) && state.navigationEpoch === navigation && form.isConnected && (isBot || $('#backtest-form') === form);
  values.leverage = Number(values.leverage || 1); if (isBot) { values.budget = Number(values.budget); values.mode = 'paper'; } else values.capital = Number(values.capital);
  if (isBot && values.venue === 'coinbase' && values.leverage !== 1) { message.textContent = 'Coinbase spot configurations use 1× leverage. Choose Jupiter for a leveraged configuration.'; return; }
  setBusy(button, true);
  try {
    if (isBot) {
      await api('/api/bots', { method: 'POST', body: JSON.stringify(values) }, context.userId);
      if (currentAccount(context) && await refreshAccount() && current()) { $('#bot-dialog').close(); location.hash = 'bots'; render(); toast('Paper configuration saved. No funds have moved.'); }
    } else {
      const result = state.config.durableBacktests
        ? await followBacktest(await api('/api/backtest-jobs', { method: 'POST', body: JSON.stringify({ idempotencyKey: crypto.randomUUID(), request: values }) }, context.userId), context, current, message)
        : await api('/api/backtests', { method: 'POST', body: JSON.stringify(values) }, context.userId);
      if (!currentAccount(context)) return;
      if (current() && result) renderBacktest(result);
      const account = await api('/api/me', {}, context.userId).catch(() => null);
      if (currentAccount(context) && account?.user?.id === context.userId) state.usage = account.usage || null;
    }
  } catch (error) { if (current()) message.textContent = errorText(error); } finally { setBusy(button, false); }
});
document.addEventListener('input', event => { if (event.target.id === 'research-search') { state.search = event.target.value; filterResearch(); } });
document.addEventListener('change', event => {
  if (event.target.id === 'research-category') { state.category = event.target.value; filterResearch(); }
  if (event.target.form?.id === 'bot-form' && event.target.name === 'venue') { const leverage = $('[name="leverage"]', event.target.form); if (event.target.value === 'coinbase') leverage.value = '1'; leverage.disabled = event.target.value === 'coinbase'; }
});
$('#menu-button').addEventListener('click', () => { const open = $('#sidebar').classList.toggle('open'); $('#menu-button').setAttribute('aria-expanded', String(open)); $('#menu-button').setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation'); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') { $('#sidebar').classList.remove('open'); $('#menu-button').setAttribute('aria-expanded', 'false'); } });
for (const dialog of $$('dialog')) dialog.addEventListener('click', event => { if (event.target !== dialog) return; const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); });
window.addEventListener('pagehide', clearConnectionCredentials);
window.addEventListener('hashchange', () => { state.navigationEpoch++; for (const dialog of $$('.automation-dialog')) dialog.remove(); render(); main.focus({ preventScroll: true }); window.scrollTo(0, 0); });
$('#year').textContent = new Date().getFullYear();
render();
async function initialize() {
  const epoch = state.accountEpoch; const navigation = state.navigationEpoch;
  const results = await Promise.allSettled([api('/api/config'), api('/research/catalog.json'), api('/api/strategies').catch(() => api('/research/strategies.json')), refreshAccount()]);
  if (results[0].status === 'fulfilled') { state.config = { ...state.config, ...results[0].value }; if (!Array.isArray(state.config.coins) || !state.config.coins.length) state.config.coins = ['SOL', 'BTC', 'ETH', 'ZEC']; }
  if (results[1].status === 'fulfilled') state.articles = results[1].value.articles || [];
  if (results[2].status === 'fulfilled') state.strategies = results[2].value.strategies || [];
  if (state.accountEpoch === epoch && state.navigationEpoch === navigation) {
    if (state.accountStatus === 'ready' && ['settings', 'backtest'].includes(state.view)) populateSelects(main);
    else render();
  }
  loadOracle();
}
initialize();
setInterval(() => { if (document.visibilityState === 'visible' && ['overview', 'oracle'].includes(state.view) && !state.loadingOracle) loadOracle(); }, TIMING.oraclePollMs);

function refreshVisibleOracle() {
  if (document.visibilityState === 'visible' && ['overview', 'oracle'].includes(state.view)) loadOracle();
}
document.addEventListener('visibilitychange', refreshVisibleOracle);
window.addEventListener('focus', refreshVisibleOracle);
setInterval(() => {
  if (state.oracle?.topStrategy && !freshStrategy(state.oracle)) {
    state.oracle = { ...state.oracle, status: 'unavailable', topStrategy: null, reason: 'The previous observation expired. Waiting for fresh evidence.' };
    if (['overview', 'oracle'].includes(state.view)) render();
  }
}, TIMING.evidenceCheckMs);
