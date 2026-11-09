// This design has no runtime adapters, persistence, account access or execution path.
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const money = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
const signed = (value) => `${value >= 0 ? '+' : '−'}${money(Math.abs(value))}`;
const names = { grid: 'Grid', dca: 'DCA', trend: 'Trend', council: 'Council', triangle: 'Arbitrage' };
const icons = { grid: '▦', dca: '≋', trend: '↗', council: '◈', triangle: '△' };
const statusNames = { running: 'Running', held: 'Held · stale inputs', paused: 'Entries paused', draft: 'Draft' };
const bots = [
  { id: 'grid', kind: 'grid', name: 'SOL range keeper', market: 'SOL / USD', state: 'running', pnl: 184.20, realized: 156.40, costs: 18.60, capital: 3000, version: 3, decision: 'Waiting for the next grid level', reason: 'Price is inside your range. No new entry is needed.', last: 'Held current ladder' },
  { id: 'trend', kind: 'trend', name: 'BTC momentum', market: 'BTC / USD', state: 'running', pnl: 96.80, realized: 71.80, costs: 10.40, capital: 2000, version: 2, decision: 'Holding the current long position', reason: 'The fast average remains above the slow average. No exit signal has fired.', last: 'Kept long exposure' },
  { id: 'dca', kind: 'dca', name: 'ETH accumulator', market: 'ETH / USD', state: 'running', pnl: -28.40, realized: -10.40, costs: 5.20, capital: 1500, version: 1, decision: 'Waiting for the next safety level', reason: 'The position is below cost. The next configured buy level has not been reached.', last: 'No safety order due' },
  { id: 'council', kind: 'council', name: 'SOL strategy council', market: 'SOL / USD', state: 'held', pnl: 59.20, realized: 44.20, costs: 8.40, capital: 1000, version: 4, decision: 'Holding entries: signals are stale', reason: 'The last signal set is 14 minutes old. Existing exposure remains visible; no fresh vote is inferred.', last: 'Signal freshness failed' },
  { id: 'triangle', kind: 'triangle', name: 'Triangle research', market: 'USD / SOL / ETH', state: 'draft', pnl: null, realized: null, costs: null, capital: 0, version: 1, decision: 'Draft: no test or observation started', reason: 'Three-leg execution needs quote and fee evidence for every leg. Candle-close proxies cannot prove an executable edge.', last: 'Not started' },
];
let selected = 'grid';
let step = 0;
let savedDraft = false;
let toastTimer;

function textNode(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function toast(message) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 6500);
}

function renderFleet() {
  const query = $('#bot-search').value.toLowerCase();
  const filter = $('#status-filter').value;
  const visible = bots.filter((bot) => `${bot.name} ${bot.market} ${names[bot.kind]}`.toLowerCase().includes(query) && (filter === 'all' || filter === bot.state));
  $('#bot-rows').replaceChildren(...visible.map((bot) => {
    const row = document.createElement('tr');
    if (bot.id === selected) row.className = 'selected';
    const nameCell = document.createElement('td');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'bot-row-name';
    button.setAttribute('aria-pressed', String(bot.id === selected));
    button.setAttribute('aria-label', `Inspect ${bot.name}`);
    const icon = textNode('span', icons[bot.kind], 'mini-icon');
    icon.setAttribute('aria-hidden', 'true');
    const description = document.createElement('span');
    description.append(textNode('strong', bot.name), textNode('small', `${bot.market} · ${names[bot.kind]}`));
    button.append(icon, description);
    button.addEventListener('click', () => { selected = bot.id; renderFleet(); renderInspector(); });
    nameCell.append(button);
    const statusCell = document.createElement('td');
    statusCell.append(textNode('span', statusNames[bot.state], `status ${bot.state}`));
    const pnl = textNode('td', bot.pnl === null ? '—' : signed(bot.pnl), `pnl-cell ${bot.pnl === null ? '' : bot.pnl >= 0 ? 'positive' : 'negative'}`);
    row.append(nameCell, statusCell, pnl, textNode('td', bot.last, 'decision-cell'));
    return row;
  }));
  $('#empty-results').hidden = visible.length > 0;
  $('#bot-count').textContent = String(bots.length);
  $('[data-nav="fleet"] small').textContent = String(bots.length);
  $('#fleet-summary').replaceChildren(document.createTextNode(`${bots.filter((bot) => bot.state === 'running').length} running `), textNode('em', `/ ${bots.filter((bot) => bot.state === 'held').length} held`));
  $('.summary-strip>div:last-child small').textContent = `${bots.filter((bot) => bot.state === 'draft').length} draft · ${bots.filter((bot) => bot.state === 'paused').length} paused · 0 live bots`;
}

function renderInspector() {
  const bot = bots.find((item) => item.id === selected);
  $('#selected-icon').textContent = icons[bot.kind];
  $('#selected-name').textContent = bot.name;
  $('#selected-subtitle').textContent = `${names[bot.kind]} · ${bot.market} · Coinbase data`;
  $('#selected-status').textContent = statusNames[bot.state];
  $('#selected-status').className = `status ${bot.state}`;
  $('#selected-version').textContent = `Config v${bot.version}`;
  $('#selected-decision').textContent = bot.state === 'paused' ? 'New entries paused by you' : bot.decision;
  $('#selected-reason').textContent = bot.state === 'paused' ? 'Open exposure and existing orders would still need monitoring. Pausing does not close a position.' : bot.reason;
  $('#selected-heartbeat').textContent = bot.state === 'draft' ? 'No worker started · local design draft' : 'Illustrative decision · Nov 9, 14:32:08 UTC';
  $('#selected-pnl').textContent = bot.pnl === null ? '—' : signed(bot.pnl);
  $('#selected-pnl').className = bot.pnl === null ? '' : bot.pnl >= 0 ? 'positive' : 'negative';
  $('#selected-capital').textContent = money(bot.capital);
  $('#selected-realized').textContent = bot.realized === null ? 'Unavailable' : signed(bot.realized);
  $('#selected-unrealized').textContent = bot.pnl === null ? 'Unavailable' : signed(bot.pnl - bot.realized);
  $('#selected-costs').textContent = bot.costs === null ? 'Unavailable' : money(bot.costs);
  $('#selected-test').textContent = bot.state === 'draft' ? 'Not run · no evidence' : 'Example run · costs included';
  $('#selected-observation').textContent = bot.state === 'draft' ? 'Not started' : bot.state === 'held' ? 'Held · fresh inputs required' : bot.state === 'paused' ? 'Entries paused · exposure remains' : 'Observing · no profitability conclusion';
  const evidenceMarks = $$('.readiness .evidence-mark');
  evidenceMarks[0].textContent = bot.state === 'draft' ? '○' : '✓';
  evidenceMarks[1].textContent = bot.state === 'draft' ? '○' : bot.state === 'held' ? '!' : '◉';
  $('#pause-one').textContent = bot.state === 'paused' ? 'Resume paper entries' : bot.state === 'held' ? 'Fresh inputs required' : 'Pause entries';
  $('#pause-one').disabled = !['running', 'paused'].includes(bot.state);
}

function addEvent(title, detail) {
  const row = document.createElement('li');
  const body = document.createElement('div');
  body.append(textNode('strong', title), textNode('p', detail));
  row.append(textNode('time', 'Demo action'), textNode('span', '', 'event-dot neutral-dot'), body, textNode('span', 'You · prototype', 'actor'));
  $('#event-list').prepend(row);
}

function showInfo(title, paragraphs, bullets = []) {
  $('#dialog-title').textContent = title;
  $('#dialog-body').replaceChildren(...paragraphs.map((text) => textNode('p', text)));
  if (bullets.length) {
    const list = document.createElement('ul');
    list.append(...bullets.map((text) => textNode('li', text)));
    $('#dialog-body').append(list);
  }
  $('#info-dialog').showModal();
}

function liveRequirements() {
  showInfo('Live readiness: unavailable', ['This is a design prototype. It has no connected account, signer, jobs or order route.', 'Production bot automation is a separate capability from a separately armed manual order path. A profitable backtest does not unlock it.'], ['Reconciled account and venue state, including unknown submissions.', 'Verified transaction economics and supported bot / venue capability.', 'Authoritative exposure, loss, slippage and freshness limits.', 'Version-bound configuration and evidence; explicit account and capital scope.', 'Jupiter Trigger signing and Jupiter V2 submission remain blocked under the current project rules.']);
}

function route() {
  const requested = location.hash.slice(1) || 'fleet';
  const view = ['fleet', 'create', 'evidence', 'activity'].includes(requested) ? requested : 'fleet';
  $('#fleet-view').hidden = !['fleet', 'activity'].includes(view);
  $('#create-view').hidden = view !== 'create';
  $('#evidence-view').hidden = view !== 'evidence';
  $('#crumb').textContent = { fleet: 'Bot fleet', create: 'Bot studio', evidence: 'Research & evidence', activity: 'Activity' }[view];
  $$('[data-nav]').forEach((link) => { if (link.dataset.nav === view) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current'); });
  if (view === 'activity') $('#activity-section').scrollIntoView({ block: 'start' });
  else window.scrollTo(0, 0);
  $('#main').focus({ preventScroll: true });
}

const ruleFields = {
  grid: [{ name: 'range', label: 'Range either side · %', value: 8, min: 0.1, max: 50, step: 0.1 }, { name: 'levels', label: 'Grid levels · count', value: 12, min: 2, max: 100, step: 1 }],
  dca: [{ name: 'base', label: 'Base order · USD', value: 100, min: 1, max: 1000, step: 1 }, { name: 'takeprofit', label: 'Take profit · %', value: 2, min: 0.1, max: 50, step: 0.1 }],
  trend: [{ name: 'fast', label: 'Fast average · bars', value: 10, min: 2, max: 99, step: 1 }, { name: 'slow', label: 'Slow average · bars', value: 40, min: 3, max: 200, step: 1 }],
  council: [{ name: 'agreement', label: 'Minimum agreement · %', value: 75, min: 51, max: 100, step: 1 }, { name: 'voters', label: 'Minimum eligible voters · count', value: 5, min: 2, max: 100, step: 1 }],
  triangle: [{ name: 'edge', label: 'Net edge after costs · basis points', value: 20, min: 1, max: 200, step: 1 }, { name: 'latency', label: 'Quote latency budget · milliseconds', value: 500, min: 1, max: 2000, step: 1 }],
};

function currentStrategy() { return new FormData($('#creator')).get('strategy'); }

function renderRules() {
  const strategy = currentStrategy();
  const fields = document.createElement('div');
  fields.className = 'fields';
  ruleFields[strategy].forEach((field) => {
    const label = textNode('label', field.label);
    const input = document.createElement('input');
    Object.assign(input, { name: field.name, type: 'number', value: String(field.value), min: String(field.min), max: String(field.max), step: String(field.step), required: true });
    label.append(input); fields.append(label);
  });
  if (strategy === 'grid') {
    const label = textNode('label', 'Order spacing');
    const select = document.createElement('select');
    select.name = 'spacing';
    for (const text of ['Arithmetic', 'Geometric']) { const option = textNode('option', text); option.value = text.toLowerCase(); select.append(option); }
    label.append(select, textNode('small', 'Compare both on the same data and costs.'));
    fields.append(label);
  }
  $('#strategy-rules').replaceChildren(fields);
  updatePreview();
}

function updatePreview() {
  const data = new FormData($('#creator'));
  const kind = data.get('strategy');
  $('#preview-strategy').textContent = names[kind];
  $('#preview-market').textContent = kind === 'triangle' ? 'USD / SOL / ETH' : data.get('market');
  const allocation = Number(data.get('allocation'));
  $('#preview-capital').textContent = Number.isFinite(allocation) && allocation > 0 ? money(allocation) : 'Set a valid budget';
  const recipes = {
    grid: `Maintain ${data.get('levels')} ${data.get('spacing')} levels across ±${data.get('range')}%. Pair each filled buy with an exit one level above it.`,
    dca: `Start with ${money(Number(data.get('base')))}. Add only at configured safety levels. Exit the basket at ${data.get('takeprofit')}% above its cost basis, accounting for fees.`,
    trend: `Enter long when the ${data.get('fast')}-bar average exceeds the ${data.get('slow')}-bar average. Close on reversal. No short position is implied.`,
    council: `Require at least ${data.get('voters')} eligible voters and ${data.get('agreement')}% agreement. Hold new entries when signals exceed the freshness limit.`,
    triangle: `Observe USD / SOL / ETH only when all three quotes fit the ${data.get('latency')} ms budget and the edge exceeds ${data.get('edge')} basis points after all costs. Research only.`,
  };
  $('#recipe-text').textContent = recipes[kind];
  const rows = [ ['Name', data.get('botName').trim() || 'Unnamed draft'], ['Strategy', names[kind]], ['Market', $('#preview-market').textContent], ['Capital / mode', `${$('#preview-capital').textContent} / paper`], ['Tuning', data.get('tuning') === 'manual' ? 'Manual · values frozen' : 'Automatic proposals · evidence-gated'], ['Daily loss / exposure', `${money(Number(data.get('loss')))} / ${money(Number(data.get('exposure')))}`], ['Slippage / input age', `${data.get('slippage')} bps / ${data.get('freshness')} seconds`], ['Execution', 'Disarmed · no account connected'] ];
  $('#review-summary').replaceChildren(...rows.map(([label, value]) => { const row = document.createElement('div'); row.append(textNode('span', label), textNode('strong', value)); return row; }));
}

function focusStep() {
  const heading = $$('.form-step')[step].querySelector('h2');
  heading.tabIndex = -1;
  heading.focus();
}

function renderStep() {
  $$('.form-step').forEach((element, index) => { element.hidden = index !== step; });
  $$('#step-list li').forEach((element, index) => { element.className = index === step ? 'current' : ''; if (index === step) element.setAttribute('aria-current', 'step'); else element.removeAttribute('aria-current'); });
  $('#next-step').textContent = step === 4 ? 'Save paper draft' : 'Continue';
  $('#back-step').disabled = step === 0;
  $('#form-error').hidden = true;
  updatePreview();
}

function validateStep() {
  const panel = $$('.form-step')[step];
  const invalid = [...panel.querySelectorAll('input, select')].find((input) => !input.checkValidity());
  let message = invalid ? 'Enter a value within the range shown for this field.' : '';
  if (invalid) invalid.reportValidity();
  const data = new FormData($('#creator'));
  if (step === 1 && !data.get('botName').trim()) message = 'Give this bot a name before continuing.';
  if (step === 2 && currentStrategy() === 'trend' && Number(data.get('fast')) >= Number(data.get('slow'))) message = 'The fast average must use fewer bars than the slow average.';
  if (step === 2 && currentStrategy() === 'dca' && Number(data.get('base')) > Number(data.get('allocation'))) message = 'The base order must not exceed the paper allocation.';
  if (step === 3 && (Number(data.get('exposure')) > Number(data.get('allocation')) || Number(data.get('loss')) > Number(data.get('allocation')))) message = 'Exposure and daily loss limits must not exceed the paper allocation.';
  if (step === 4 && !data.get('reviewed')) message = 'Review the paper scope and limits, then select the review checkbox.';
  $('#form-error').textContent = message;
  $('#form-error').hidden = !message;
  if (message && !invalid) { $('#form-error').setAttribute('tabindex', '-1'); $('#form-error').focus(); }
  return !message;
}

$('#creator').addEventListener('submit', (event) => {
  event.preventDefault();
  if (savedDraft || !validateStep()) return;
  if (step < 4) { step += 1; renderStep(); focusStep(); return; }
  savedDraft = true;
  const data = new FormData($('#creator'));
  const kind = data.get('strategy');
  const bot = { id: `draft-${bots.length}`, kind, name: data.get('botName').trim(), market: kind === 'triangle' ? 'USD / SOL / ETH' : data.get('market'), state: 'draft', pnl: null, realized: null, costs: null, capital: 0, version: 1, decision: 'Draft: no test or observation started', reason: 'This draft exists only in this page. Production would validate the configuration and data before starting a test.', last: 'Saved local draft' };
  bots.push(bot); selected = bot.id;
  $('#bot-search').value = ''; $('#status-filter').value = 'all';
  renderFleet(); renderInspector();
  addEvent('Paper draft created in the prototype', `${bot.name} · No job started, account connected or capital reserved.`);
  location.hash = 'fleet';
  toast('Paper draft added to the design. No test, job or trade started.');
});
$('#back-step').addEventListener('click', () => { if (step > 0) { step -= 1; renderStep(); focusStep(); } });
$('#creator').addEventListener('change', (event) => {
  if (event.target.name === 'strategy') {
    renderRules();
    $('#bot-name').value = `My ${new FormData($('#creator')).get('market').split(' / ')[0]} ${names[currentStrategy()].toLowerCase()}`;
  }
  if (savedDraft) { savedDraft = false; step = 0; renderStep(); }
  updatePreview();
});
$('#creator').addEventListener('input', updatePreview);
$('#bot-search').addEventListener('input', renderFleet);
$('#status-filter').addEventListener('change', renderFleet);
$('#pause-one').addEventListener('click', () => {
  const bot = bots.find((item) => item.id === selected);
  if (!['running', 'paused'].includes(bot.state)) return;
  bot.state = bot.state === 'paused' ? 'running' : 'paused';
  bot.last = bot.state === 'paused' ? 'Entries paused by you' : 'Paper entries resumed';
  addEvent(`${bot.name}: ${bot.last.toLowerCase()}`, 'Local demonstration only. Existing orders and open exposure are not canceled or closed.');
  renderFleet(); renderInspector();
  toast(`${bot.last}. Local demonstration only; no backend command was sent.`);
});
$('#pause-fleet').addEventListener('click', () => {
  const affected = bots.filter((bot) => bot.state === 'running');
  affected.forEach((bot) => { bot.state = 'paused'; bot.last = 'Entries paused by you'; });
  renderFleet(); renderInspector();
  addEvent(`Paused new entries for ${affected.length} paper bots`, 'Held and draft bots were unchanged. Pausing does not cancel orders, close positions or stop shared workers.');
  toast(`Paused ${affected.length} illustrative paper bots. Open exposure remains visible.`);
});
$('#inspect-incident').addEventListener('click', () => { selected = 'council'; renderFleet(); renderInspector(); $('#selected-name').setAttribute('tabindex', '-1'); $('#selected-name').focus(); });
$('#inspect-evidence').addEventListener('click', () => { const bot = bots.find((item) => item.id === selected); showInfo(`${bot.name}: evidence`, [bot.state === 'draft' ? 'No test has run for this draft. Do not infer results from its template.' : 'The screen uses an illustrative historical run and paper observation. No measured source result is attached.', 'Production evidence must bind configuration version, market, dataset hash, time interval, engine version and cost model. Incompatible runs stay separate.', 'Net P&L = realized after costs + unrealized net estimate. Modelled costs are already included; do not subtract them twice.']); });
$('#live-readiness').addEventListener('click', liveRequirements);
$('#evidence-live').addEventListener('click', liveRequirements);
$('#accounts').addEventListener('click', liveRequirements);
$('#close-dialog').addEventListener('click', () => $('#info-dialog').close());
$('#dialog-done').addEventListener('click', () => $('#info-dialog').close());

const commands = [ ['Open bot fleet', 'fleet'], ['Create a paper bot', 'create'], ['Review research and evidence', 'evidence'], ['Inspect activity', 'activity'] ];
function renderCommands() {
  const query = $('#command-query').value.toLowerCase();
  const matches = commands.filter(([title]) => title.toLowerCase().includes(query));
  $('#command-results').replaceChildren(...matches.map(([title, hash]) => { const button = textNode('button', title, 'command-result'); button.type = 'button'; button.addEventListener('click', () => { $('#command-dialog').close(); location.hash = hash; if (hash === 'create' && savedDraft) { savedDraft = false; step = 0; renderStep(); } }); return button; }));
  if (!matches.length) $('#command-results').append(textNode('p', 'No matching action. Try “bot”, “evidence” or “activity”.'));
}
function openCommands() { $('#command-query').value = ''; renderCommands(); $('#command-dialog').showModal(); $('#command-query').focus(); }
$('#search-command').addEventListener('click', openCommands);
$('#help').addEventListener('click', openCommands);
$('#command-query').addEventListener('input', renderCommands);
$('#close-command').addEventListener('click', () => $('#command-dialog').close());
document.addEventListener('keydown', (event) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k' && !document.querySelector('dialog[open]')) { event.preventDefault(); openCommands(); } });
window.addEventListener('hashchange', () => { if (location.hash === '#create' && savedDraft) { savedDraft = false; step = 0; renderStep(); $('#creator').elements.reviewed.checked = false; } route(); });
renderRules(); renderStep(); renderFleet(); renderInspector(); route();
