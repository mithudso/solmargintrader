import test from 'node:test';
import assert from 'node:assert/strict';
import '../src/1000x/perps-bridge.js';

const bridge = globalThis.__smtPerpsBridge;

/* A stand-in for the few DOM calls the bridge makes. Shapes follow the live order form and the page's own code. */
function el(tag, attrs = {}, children = []) {
  const node = { tag, attrs: { ...attrs }, children: [], parent: null, clicks: 0, hidden: false, onClick: null, own: '', writes: 0 };
  let value = attrs.value ?? '';
  Object.defineProperty(node, 'value', { get: () => value, set: next => { node.writes += 1; value = String(next); } });
  node.page = next => { value = String(next); }; // the page's own update, not counted as a write by the bridge
  Object.defineProperty(node, 'disabled', { get: () => node.attrs.disabled === true, set: next => { node.attrs.disabled = next; } });
  Object.defineProperty(node, 'textContent', { get: () => node.own + node.children.map(child => child.textContent).join('') });
  node.getAttribute = name => (name in node.attrs && node.attrs[name] !== true && node.attrs[name] !== false ? String(node.attrs[name]) : name in node.attrs && node.attrs[name] === true ? '' : null);
  node.hasAttribute = name => name in node.attrs && node.attrs[name] !== false;
  node.getClientRects = () => (node.hidden || (node.parent && node.parent.getClientRects().length === 0) ? [] : [1]);
  node.click = () => { node.clicks += 1; node.onClick?.(node); };
  node.append = (...more) => { for (const child of more) { child.parent = node; node.children.push(child); } return node; };
  node.remove = () => { if (node.parent) node.parent.children = node.parent.children.filter(child => child !== node); node.parent = null; };
  const matches = (candidate, selector) => {
    const parsed = /^([a-z]*)((?:\.[\w-]+|\[[\w-]+="[^"]*"\])*)$/.exec(selector.trim());
    if (!parsed) throw new Error(`selector not supported by the stand-in: ${selector}`);
    if (parsed[1] && candidate.tag !== parsed[1]) return false;
    for (const part of parsed[2].match(/\.[\w-]+|\[[\w-]+="[^"]*"\]/g) ?? []) {
      if (part[0] === '.') { if (!String(candidate.attrs.class ?? '').split(' ').includes(part.slice(1))) return false; }
      else { const [, name, wanted] = /^\[([\w-]+)="([^"]*)"\]$/.exec(part); if (candidate.getAttribute(name) !== wanted) return false; }
    }
    return true;
  };
  node.querySelectorAll = selector => {
    const out = [], walk = current => { for (const child of current.children) { if (selector.split(',').some(one => matches(child, one))) out.push(child); walk(child); } };
    walk(node);
    return out;
  };
  for (const child of children) node.append(typeof child === 'string' ? Object.assign(el('span'), { own: child }) : child);
  return node;
}
const text = (tag, content, attrs = {}) => Object.assign(el(tag, attrs), { own: content });

function positionRow({ coin = 'HYPE', badge = 'Long 25x', entry = '$63.529', mark = '$63.510', liq = '$61.20', quick = {}, cells = 8 } = {}) {
  const quickButton = el('button', { type: 'button', 'aria-label': `Quick close ${coin}`, ...quick });
  const close = text('button', 'Close', { type: 'button' });
  const parts = [
    el('div', {}, [text('button', coin, { type: 'button' }), text('span', badge)]),
    el('div', {}, [text('span', '$12.40'), text('span', '(+$0.20)')]),
    el('div', {}, [el('span', {}, [entry, text('span', '/')]), text('span', mark)]),
    el('div', {}, [text('span', liq)]),
    el('div', {}, [text('span', '$250.00'), text('span', '3.93 HYPE')]),
    el('div', {}, [text('span', '$10.00')]),
    el('div', {}, [text('span', '-- / --')]),
    el('div', {}, [text('button', '', { 'aria-label': `Share ${coin}` }), quickButton, close]),
  ].slice(0, cells);
  return Object.assign(el('div', { class: 'grid perps-position-table-row h-[62px]' }, parts), { quickButton, closeButton: close });
}

function page({ rows = [positionRow()], positionsSelected = true, emptyText = '', balance = '120.5 USDC', orderType = 'Market', side = 'long', leverage = '10', tabLabel = 'Positions' } = {}) {
  const doc = el('body');
  doc.body = doc;
  const positionsTab = text('button', tabLabel, { role: 'tab', 'aria-selected': String(positionsSelected) });
  const tabs = el('div', {}, [positionsTab, text('button', 'Open Orders', { role: 'tab', 'aria-selected': String(!positionsSelected) })]);
  const closeAll = text('button', 'Close All', { type: 'button' });
  const list = el('div', {}, [...rows, ...(emptyText ? [text('p', emptyText)] : [])]);
  const long = text('button', 'Long/Buy', { role: 'radio', 'aria-label': 'Long', ...(side === 'long' ? { 'data-checked': true } : {}) });
  const short = text('button', 'Short/Sell', { role: 'radio', 'aria-label': 'Short', ...(side === 'short' ? { 'data-checked': true } : {}) });
  const input = el('input', { type: 'text', 'aria-label': 'Collateral amount', inputmode: 'decimal' });
  const range = el('input', { type: 'range', 'aria-label': 'Leverage', value: leverage });
  const half = text('button', 'HALF'), max = text('button', 'MAX'), balanceButton = text('button', balance);
  const presets = [1.1, 5, 10, 15, 20, 25].map(value => Object.assign(text('button', `${value}x`, { 'aria-label': `Set leverage to ${value}x` }), { onClick: () => range.page(value) }));
  const submit = text('button', side === 'long' ? 'Long/Buy' : 'Short/Sell', { type: 'button', disabled: true });
  const amount = Number(balance.split(' ')[0].replaceAll(',', ''));
  half.onClick = () => { input.page((amount / 2).toFixed(4)); submit.disabled = false; };
  max.onClick = () => { input.page((amount * 0.998).toFixed(4)); submit.disabled = false; };
  const choose = which => () => { for (const [name, radio] of [['long', long], ['short', short]]) { if (name === which) radio.attrs['data-checked'] = true; else delete radio.attrs['data-checked']; } submit.own = which === 'long' ? 'Long/Buy' : 'Short/Sell'; };
  long.onClick = choose('long'); short.onClick = choose('short');
  const form = el('div', {}, [long, short,
    text('button', 'Market', { role: 'tab', 'aria-selected': String(orderType === 'Market') }), text('button', 'Limit', { role: 'tab', 'aria-selected': String(orderType === 'Limit') }),
    balanceButton, half, max, input, range, ...presets, submit]);
  doc.append(tabs, closeAll, list, form);
  const openDialog = ({ confirm = true, title = 'Close Entire Position?', coin = 'HYPE' } = {}) => {
    const yes = text('button', 'Confirm'), no = text('button', 'Dismiss');
    const dialog = el('div', { role: 'dialog' }, [text('h2', title), text('p', `This will send an order to close your ${coin} position.`), ...(confirm ? [yes] : []), no]);
    doc.append(dialog);
    return { dialog, yes, no };
  };
  return { doc, tabs, positionsTab, closeAll, list, long, short, input, range, half, max, submit, presets, balanceButton, openDialog };
}
const instant = { wait: async () => {} };
const expect = { coin: 'HYPE', side: 'long', leverage: 25, entryText: '$63.529' };
// Each call gets its own clock so the bridge's own spacing rules do not couple the tests.
let clock = 1_800_000_000_000;
const later = () => { clock += 60_000; const at = clock; return () => at; };

test('a listed position is read strictly from its row', () => {
  const { doc } = page();
  const read = bridge.readPositions(doc);
  assert.equal(read.recognized, true);
  assert.deepEqual(read.positions, [{ coin: 'HYPE', side: 'long', leverage: 25, entry: 63.529, entryText: '$63.529', mark: 63.51, bust: 61.2,
    size: '$250.003.93 HYPE', collateral: '$10.00', value: '$12.40(+$0.20)', mode: 'Perps', close: { state: 'ready', label: 'Quick close' } }]);
  assert.deepEqual([read.pending, read.unreadable], [0, 0]);
  // Fractional leverage and a short.
  assert.deepEqual(bridge.readPositions(page({ rows: [positionRow({ coin: 'ZEC', badge: 'Short 21.9x' })] }).doc).positions.map(row => [row.coin, row.side, row.leverage]), [['ZEC', 'short', 21.9]]);
  assert.equal(bridge.leverageOf('25x'), 25);
  for (const bad of ['25', 'x25', '250x', '0.5x', '2.555x', '']) assert.equal(bridge.leverageOf(bad), null, bad);
  assert.equal(bridge.money('$1,234.50'), 1234.5);
  for (const bad of ['$0', '-5', '1.2.3', '$', '63,5']) assert.equal(bridge.money(bad), null, bad);
});

test('anything that does not look exactly like a position row is refused, never guessed', () => {
  for (const [row, reason] of [
    [positionRow({ badge: 'Long Short 25x' }), 'side_unreadable'], [positionRow({ badge: '25x' }), 'side_unreadable'],
    [positionRow({ badge: 'Long' }), 'leverage_unreadable'], [positionRow({ badge: 'Long 25x 50x' }), 'leverage_unreadable'],
    [positionRow({ entry: '63,529' }), 'entry_unreadable'], [positionRow({ entry: '$63.5/$63.6' }), 'entry_unreadable'],
    [positionRow({ coin: 'hype' }), 'coin_unreadable'], [positionRow({ cells: 7 }), 'row_unreadable'],
  ]) {
    const read = bridge.readPositions(page({ rows: [row] }).doc);
    assert.deepEqual([read.recognized, read.positions.length, read.unreadable, read.problems[0]], [true, 0, 1, reason], reason);
  }
  // The list itself must be on screen, or say that it is empty.
  assert.deepEqual(bridge.readPositions(page({ positionsSelected: false }).doc), { recognized: false, reason: 'positions_tab_not_shown', positions: [] });
  assert.deepEqual(bridge.readPositions(page({ rows: [] }).doc), { recognized: false, reason: 'positions_table_not_found', positions: [] });
  assert.deepEqual(bridge.readPositions(page({ rows: [], emptyText: 'No positions' }).doc), { recognized: true, positions: [], pending: 0, unreadable: 0, problems: [] });
  assert.equal(bridge.readPositions(page({ rows: [], emptyText: 'Loading positions' }).doc).pending, 1);
  // With positions listed the tab may carry a count, as it does on 1000x. Any other label is not the Positions tab.
  for (const label of ['Positions (1)', 'Positions 2', 'Positions(12)']) assert.equal(bridge.readPositions(page({ tabLabel: label }).doc).positions.length, 1, label);
  for (const label of ['Positions closed', 'Open Positions', 'Position']) assert.equal(bridge.readPositions(page({ tabLabel: label }).doc).recognized, false, label);
  // A row with no quick-close button, or one that is disabled, says so.
  const none = positionRow(); none.quickButton.remove();
  assert.equal(bridge.readPositions(page({ rows: [none] }).doc).positions[0].close.state, 'none');
  assert.equal(bridge.readPositions(page({ rows: [positionRow({ quick: { disabled: true } })] }).doc).positions[0].close.state, 'disabled');
});

test('closing presses the matching row’s own Quick close, answers the page’s question once, and touches nothing else', async () => {
  const other = positionRow({ coin: 'ZEC', badge: 'Short 50x', entry: '$739.97' });
  const mine = positionRow();
  const view = page({ rows: [other, mine] });
  let dialog;
  mine.quickButton.onClick = () => { dialog = view.openDialog(); };
  const result = await bridge.closePosition(view.doc, expect, { ...instant, now: later() });
  assert.deepEqual(result, { clicked: true, label: 'Quick close', confirmed: true });
  assert.deepEqual([mine.quickButton.clicks, dialog.yes.clicks, dialog.no.clicks], [1, 1, 0]);
  assert.deepEqual([other.quickButton.clicks, other.closeButton.clicks, mine.closeButton.clicks, view.closeAll.clicks, view.submit.clicks], [0, 0, 0, 0, 0]);
});

test('with the page’s question switched off the one press is the whole close', async () => {
  const mine = positionRow({ entry: '$70.001' });
  const view = page({ rows: [mine] });
  const result = await bridge.closePosition(view.doc, { ...expect, entryText: '$70.001' }, { ...instant, now: later() });
  assert.deepEqual(result, { clicked: true, label: 'Quick close', confirmed: false });
  assert.equal(mine.quickButton.clicks, 1);
});

test('a close is refused, not improvised, whenever the page is not as expected', async () => {
  const fresh = entry => { const row = positionRow({ entry }); return { row, view: page({ rows: [row] }), want: { ...expect, entryText: entry } }; };
  // No such position, the wrong side, two rows alike.
  let { row, view, want } = fresh('$71.000');
  assert.deepEqual(await bridge.closePosition(view.doc, { ...want, entryText: '$1.00' }, { ...instant, now: later() }), { clicked: false, reason: 'position_not_listed' });
  assert.deepEqual(await bridge.closePosition(view.doc, { ...want, side: 'short' }, { ...instant, now: later() }), { clicked: false, reason: 'position_not_listed' });
  assert.equal((await bridge.closePosition(page({ rows: [positionRow({ entry: '$71.000' }), positionRow({ entry: '$71.000' })] }).doc, want, { ...instant, now: later() })).reason, 'ambiguous_position');
  assert.equal(row.quickButton.clicks, 0);
  // A disabled button is waited on; a missing one is a refusal.
  ({ row, view, want } = fresh('$72.000'));
  row.quickButton.disabled = true;
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: later() }), { clicked: false, retry: true, reason: 'close_disabled', label: 'Quick close' });
  row.quickButton.remove();
  assert.equal((await bridge.closePosition(view.doc, want, { ...instant, now: later() })).reason, 'close_unavailable');
  // The Positions tab not showing: it is selected and the caller asks again. A list caught mid-render is asked again too.
  const away = page({ positionsSelected: false });
  assert.deepEqual(await bridge.closePosition(away.doc, expect, { ...instant, now: later() }), { clicked: false, retry: true, reason: 'opened_positions_tab' });
  assert.equal(away.positionsTab.clicks, 1);
  assert.deepEqual(await bridge.closePosition(page({ rows: [] }).doc, expect, { ...instant, now: later() }), { clicked: false, retry: true, reason: 'positions_table_not_found' });
  for (const bad of [null, {}, { ...expect, side: 'up' }, { ...expect, entryText: '' }, { ...expect, coin: 5 }]) {
    assert.deepEqual(await bridge.closePosition(page().doc, bad, { ...instant, now: later() }), { clicked: false, reason: 'invalid_request' });
  }
  // A question already open belongs to something else: nothing is pressed.
  ({ row, view, want } = fresh('$73.000'));
  const stale = view.openDialog();
  assert.equal((await bridge.closePosition(view.doc, want, { ...instant, now: later() })).reason, 'close_dialog_already_open');
  assert.deepEqual([row.quickButton.clicks, stale.yes.clicks], [0, 0]);
  // The page asks, but its Confirm is not there: reported as not closed. Another dialog is never confirmed.
  ({ row, view, want } = fresh('$74.000'));
  let asked;
  row.quickButton.onClick = () => { asked = view.openDialog({ confirm: false }); };
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: later() }), { clicked: false, reason: 'close_confirm_unavailable' });
  assert.equal(asked.no.clicks, 0);
  // The page asks about another market: never confirmed.
  ({ row, view, want } = fresh('$74.500'));
  let wrong;
  row.quickButton.onClick = () => { wrong = view.openDialog({ coin: 'ZEC' }); };
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: later() }), { clicked: false, reason: 'close_confirm_unavailable' });
  assert.equal(wrong.yes.clicks, 0);
  // Two questions at once, before or after the press: nothing is confirmed.
  ({ row, view, want } = fresh('$74.700'));
  const pair = [view.openDialog(), view.openDialog()];
  assert.equal((await bridge.closePosition(view.doc, want, { ...instant, now: later() })).reason, 'close_dialog_already_open');
  assert.deepEqual([row.quickButton.clicks, pair[0].yes.clicks, pair[1].yes.clicks], [0, 0, 0]);
  ({ row, view, want } = fresh('$75.000'));
  let unrelated;
  row.quickButton.onClick = () => { unrelated = view.openDialog({ title: 'Close All Positions?' }); };
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: later() }), { clicked: true, label: 'Quick close', confirmed: false });
  assert.equal(unrelated.yes.clicks, 0);
});

test('a question the bridge caused is still its own on the next request; a failed press is not reported as out', async () => {
  // Confirm is disabled at first (the page is preparing the order): the request ends as "ask again".
  const row = positionRow({ entry: '$76.000' }), view = page({ rows: [row] }), want = { ...expect, entryText: '$76.000' };
  let dialog;
  row.quickButton.onClick = () => { dialog = view.openDialog(); dialog.yes.disabled = true; };
  // A clock that moves, so the wait ends on time rather than on a count.
  const ticking = start => { let t = start; return () => (t += 500); };
  const begin = later()();
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: ticking(begin) }), { clicked: false, retry: true, reason: 'close_confirm_unavailable' });
  // The retry does not press Quick close again; it answers the question that is already open.
  dialog.yes.disabled = false;
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: ticking(begin + 8_000) }), { clicked: true, label: 'Quick close', confirmed: true });
  assert.deepEqual([row.quickButton.clicks, dialog.yes.clicks, dialog.no.clicks], [1, 1, 0]);
  // A question for a different position, or one that has gone stale, is not this request's to answer.
  const other = positionRow({ entry: '$77.000' }), second = page({ rows: [other] });
  const stale = second.openDialog();
  assert.equal((await bridge.closePosition(second.doc, { ...expect, entryText: '$77.000' }, { ...instant, now: later() })).reason, 'close_dialog_already_open');
  assert.equal(stale.yes.clicks, 0);
});

test('while one close is being carried out, another request is told to ask again, not that a press is out', async () => {
  const row = positionRow({ entry: '$78.000' }), view = page({ rows: [row] }), want = { ...expect, entryText: '$78.000' };
  let release; const gate = new Promise(resolve => { release = resolve; });
  const at = later();
  const first = bridge.closePosition(view.doc, want, { wait: () => gate, now: at });
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: at }), { clicked: false, retry: true, reason: 'page_busy' });
  release();
  assert.equal((await first).clicked, true);
  assert.equal(row.quickButton.clicks, 1);
});

test('one press per position: a second request within ten seconds presses nothing', async () => {
  const row = positionRow({ entry: '$80.000' }), view = page({ rows: [row] }), want = { ...expect, entryText: '$80.000' };
  const at = later();
  assert.equal((await bridge.closePosition(view.doc, want, { ...instant, now: at })).clicked, true);
  assert.deepEqual(await bridge.closePosition(view.doc, want, { ...instant, now: () => at() + 9_000 }), { clicked: false, already: true, reason: 'recently_clicked', label: 'Quick close' });
  assert.equal(row.quickButton.clicks, 1);
  assert.equal((await bridge.closePosition(view.doc, want, { ...instant, now: () => at() + 10_001 })).clicked, true);
  assert.equal(row.quickButton.clicks, 2);
});

test('the order form is read without touching it', () => {
  const view = page({ side: 'short', leverage: '21.9' });
  assert.deepEqual(bridge.readOrderForm(view.doc), { recognized: true, mode: 'Market', amountText: '', balanceText: '120.5 USDC', leverage: 21.9, side: 'short',
    longEnabled: true, shortEnabled: true, busy: false, error: '' });
  assert.equal(bridge.readOrderForm(page({ orderType: 'Limit' }).doc).mode, 'Limit');
  assert.equal(bridge.readOrderForm(page({ balance: '0 USDC' }).doc).balanceText, '0 USDC');
  // An attribute that says "not checked" is not a selection, and two sides checked at once is no selection at all.
  const explicit = page({ side: 'long' }); explicit.short.attrs['data-checked'] = 'false';
  assert.equal(bridge.readOrderForm(explicit.doc).side, 'long');
  const both = page({ side: 'long' }); both.short.attrs['data-checked'] = true;
  assert.equal(bridge.readOrderForm(both.doc).side, null);
  const broken = page(); broken.input.remove();
  assert.deepEqual(bridge.readOrderForm(broken.doc), { recognized: false, reason: 'order_form_not_found' });
  assert.deepEqual([view.long.clicks, view.short.clicks, view.submit.clicks, view.input.writes], [0, 0, 0, 0]);
});

test('an entry sets side, leverage and size with the page’s own buttons, presses submit once, and never types an amount', async () => {
  const view = page({ side: 'short', leverage: '10' });
  const result = await bridge.openPosition(view.doc, { side: 'long', fraction: 0.5, leverage: 25 }, { ...instant, now: later() });
  assert.deepEqual(result, { clicked: true, amountText: '60.2500', leverage: null, formLeverage: 25 });
  assert.deepEqual([view.long.clicks, view.short.clicks, view.half.clicks, view.max.clicks, view.submit.clicks], [1, 0, 1, 0, 1]);
  assert.equal(view.presets.find(button => button.getAttribute('aria-label') === 'Set leverage to 25x').clicks, 1);
  assert.equal(view.input.writes, 0, 'the bridge never writes the amount field');
  assert.equal(view.submit.textContent, 'Long/Buy');
  // All of it, at the leverage the page already shows, on the side already chosen.
  const all = page({ side: 'short', leverage: '20' });
  assert.deepEqual(await bridge.openPosition(all.doc, { side: 'short', fraction: 1 }, { ...instant, now: later() }), { clicked: true, amountText: '120.2590', leverage: null, formLeverage: 20 });
  assert.deepEqual([all.short.clicks, all.max.clicks, all.submit.clicks, all.presets.reduce((sum, button) => sum + button.clicks, 0)], [0, 1, 1, 0]);
});

test('an entry is refused before the submit press whenever anything is off', async () => {
  const attempt = async (setup, request = { side: 'long', fraction: 0.5 }, options = {}) => {
    const view = page(setup.page ?? {});
    setup.change?.(view);
    const result = await bridge.openPosition(view.doc, request, { ...instant, now: later(), ...options });
    assert.equal(view.submit.clicks, 0, JSON.stringify(result));
    assert.equal(view.input.writes, 0);
    return result.reason;
  };
  for (const request of [null, { side: 'up', fraction: 0.5 }, { side: 'long', fraction: 0.25 }, { side: 'long', fraction: 0.75 }, { side: 'long', fraction: 0.5, leverage: 12.5 }, { side: 'long', fraction: 0.5, leverage: 500 }]) {
    assert.equal(await attempt({}, request), 'invalid_request', JSON.stringify(request));
  }
  assert.equal(await attempt({ page: { orderType: 'Limit' } }), 'mode_not_market');
  assert.equal(await attempt({ page: { balance: '0 USDC' } }), 'no_balance');
  assert.equal(await attempt({ change: view => { view.balanceButton.own = 'Loading'; } }), 'balance_unreadable');
  assert.equal(await attempt({ change: view => { view.range.remove(); } }), 'order_form_not_found');
  assert.equal(await attempt({ change: view => { view.half.onClick = null; } }), 'amount_unexpected');
  // The page fills in something other than half the balance.
  assert.equal(await attempt({ change: view => { view.half.onClick = () => view.input.page('120.5'); } }), 'amount_unexpected');
  assert.equal(await attempt({ change: view => { view.half.disabled = true; } }), 'size_button_unavailable');
  assert.equal(await attempt({ change: view => { view.half.onClick = () => view.input.page('60.25'); } }), 'side_disabled');
  assert.equal(await attempt({ change: view => { view.short.onClick = null; } }, { side: 'short', fraction: 0.5 }), 'side_not_set');
  assert.equal(await attempt({ change: view => { for (const preset of view.presets) preset.onClick = null; } }, { side: 'long', fraction: 0.5, leverage: 25 }), 'leverage_not_set');
  assert.equal(await attempt({}, { side: 'long', fraction: 0.5, leverage: 50 }), 'leverage_button_unavailable');
  assert.equal(await attempt({}, undefined, { stillValid: () => false }), 'page_changed');
  // The page's own leverage moves while the form settles (a side switch can do that): the planned figure is gone, so no press.
  assert.equal(await attempt({ page: { side: 'short' }, change: view => { const flip = view.long.onClick; view.long.onClick = node => { flip(node); view.range.page(25); }; } }), 'page_changed');
  assert.equal(await attempt({ change: view => { view.range.page('abc'); } }), 'leverage_unreadable');

  // A hidden tab's timers crawl: a press that would come late is not made.
  let ticks = 0; const base = later()();
  assert.equal(await attempt({}, undefined, { now: () => base + (ticks++ ? 7_000 : 0) }), 'too_slow');
});

test('entries are spaced and never overlap', async () => {
  const view = page(), at = later();
  assert.equal((await bridge.openPosition(view.doc, { side: 'long', fraction: 0.5 }, { ...instant, now: at })).clicked, true);
  assert.deepEqual(await bridge.openPosition(view.doc, { side: 'long', fraction: 0.5 }, { ...instant, now: () => at() + 4_000 }), { clicked: false, reason: 'recently_opened' });
  assert.equal(view.submit.clicks, 1);
  // Two requests at once: the second is refused while the first is parked.
  const slow = page(); let release; const gate = new Promise(resolve => { release = resolve; });
  const begin = later();
  const first = bridge.openPosition(slow.doc, { side: 'long', fraction: 1 }, { wait: () => gate, now: begin });
  assert.deepEqual(await bridge.openPosition(slow.doc, { side: 'long', fraction: 1 }, { ...instant, now: () => begin() + 60_000 }), { clicked: false, reason: 'page_busy' });
  release();
  assert.equal((await first).clicked, true);
  assert.equal(slow.submit.clicks, 1);
});
