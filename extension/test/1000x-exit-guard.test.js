import test from 'node:test';
import assert from 'node:assert/strict';

import { ExitGuard, GUARD_LIMITS, parseLevel, validateLevels, crossed, quoteFresh, positionKey } from '../src/1000x/exit-guard.js';
import '../src/1000x/page-bridge.js';

const bridge = globalThis.__smt1000xBridge;
const long = { coin: 'SOL', side: 'long', leverage: 1000, entry: 100, entryText: '$100.00', bust: 99.902 };
const short = { ...long, side: 'short', bust: 100.098 };
const quote = (price, nowMs, age = 100) => ({ price, exchangeMs: nowMs - age, receivedMs: nowMs - age + 20 });
const NOW = 1_800_000_000_000;

test('levels are plain decimals; anything else is refused rather than guessed', () => {
  assert.equal(parseLevel('71.68'), 71.68);
  assert.equal(parseLevel(' 71 '), 71);
  for (const bad of ['', '71,68', '$71.68', '1e3', '-5', '0', '71.', '.5', 'abc', null, 71.68]) assert.equal(parseLevel(bad), null, String(bad));
});

test('a take profit must be on the winning side and a stop loss between price and bust', () => {
  const ok = validateLevels({ position: long, price: 100, takeProfit: 100.2, stopLoss: 99.95 });
  assert.deepEqual([ok.ok, ok.errors], [true, []]);
  assert.equal(validateLevels({ position: short, price: 100, takeProfit: 99.8, stopLoss: 100.05 }).ok, true);
  assert.equal(validateLevels({ position: long, price: 100, takeProfit: 100.2 }).ok, true, 'one level is enough');
  const cases = [
    [{ position: long, price: 100 }, /take profit, a stop loss/],
    [{ position: long, price: 100, takeProfit: 99.9 }, /above the current price/],
    [{ position: long, price: 100, stopLoss: 100.1 }, /below the current price/],
    [{ position: long, price: 100, stopLoss: 99.9 }, /beyond the bust price/],
    [{ position: short, price: 100, takeProfit: 100.1 }, /below the current price/],
    [{ position: short, price: 100, stopLoss: 100.2 }, /beyond the bust price/],
    [{ position: long, price: NaN, takeProfit: 101 }, /No live price/],
    [{ position: { ...long, entry: null }, price: 100, takeProfit: 101 }, /entry price could not be read/],
    [{ position: { ...long, entry: 10_000 }, price: 100, takeProfit: 101 }, /probably misread/],
    [{ position: long, price: 100, takeProfit: -1 }, /positive price/],
    [{ position: null, price: 100, takeProfit: 101 }, /No position/],
  ];
  for (const [input, pattern] of cases) {
    const result = validateLevels(input);
    assert.equal(result.ok, false);
    assert.match(result.errors.join(' '), pattern);
  }
});

test('crossing is inclusive, side-aware and prefers the stop when both are reached', () => {
  assert.equal(crossed({ side: 'long', price: 100.2, takeProfit: 100.2, stopLoss: 99.95 }), 'takeProfit');
  assert.equal(crossed({ side: 'long', price: 99.95, takeProfit: 100.2, stopLoss: 99.95 }), 'stopLoss');
  assert.equal(crossed({ side: 'long', price: 100.1, takeProfit: 100.2, stopLoss: 99.95 }), null);
  assert.equal(crossed({ side: 'short', price: 99.8, takeProfit: 99.8, stopLoss: 100.05 }), 'takeProfit');
  assert.equal(crossed({ side: 'short', price: 100.06, takeProfit: 99.8, stopLoss: 100.05 }), 'stopLoss');
  assert.equal(crossed({ side: 'long', price: 100, takeProfit: 100, stopLoss: 100 }), 'stopLoss');
  assert.equal(crossed({ side: 'long', price: NaN, takeProfit: 1, stopLoss: null }), null);
  assert.equal(crossed({ side: 'long', price: 500, takeProfit: null, stopLoss: null }), null);
});

test('only a fresh quote on both clocks can trigger', () => {
  assert.equal(quoteFresh(quote(100, NOW), NOW), true);
  assert.equal(quoteFresh(quote(100, NOW, GUARD_LIMITS.quoteMaxAgeMs + 1), NOW), false);
  assert.equal(quoteFresh({ price: 100, exchangeMs: NOW - 10, receivedMs: NOW - 5000 }, NOW), false);
  assert.equal(quoteFresh({ price: 100, exchangeMs: NOW + 5000, receivedMs: NOW }, NOW), false, 'a quote from the future');
  assert.equal(quoteFresh({ price: 0, exchangeMs: NOW, receivedMs: NOW }, NOW), false);
  assert.equal(quoteFresh(null, NOW), false);
});

test('auto-close: one trigger, one click request, closed only when the row leaves', () => {
  const guard = new ExitGuard();
  assert.deepEqual(guard.arm({ position: long, price: 100, takeProfit: 100.2, stopLoss: 99.95, mode: 'close', nowMs: NOW }), { ok: true, errors: [] });
  assert.equal(guard.arm({ position: long, price: 100, takeProfit: 100.3, mode: 'close', nowMs: NOW }).ok, false, 'already armed');
  assert.equal(guard.onQuote(quote(100.1, NOW + 500), NOW + 500), null);
  assert.equal(guard.onQuote(quote(100.3, NOW + 9000, 5000), NOW + 9000), null, 'a stale quote beyond the level does nothing');
  assert.equal(guard.snapshot().state, 'armed');
  const action = guard.onQuote(quote(100.25, NOW + 1000), NOW + 1000);
  assert.deepEqual(action, { type: 'close', reason: 'takeProfit', price: 100.25,
    expect: { coin: 'SOL', side: 'long', leverage: 1000, entryText: '$100.00' } });
  assert.equal(guard.onQuote(quote(100.4, NOW + 1200), NOW + 1200), null, 'a trigger is not issued twice');
  assert.equal(guard.onCloseResult({ clicked: false, retry: true, reason: 'close_locked' }, NOW + 1300), true);
  assert.equal(guard.snapshot().state, 'triggered');
  assert.equal(guard.onCloseResult({ clicked: true, label: 'Close' }, NOW + 4000), false);
  assert.equal(guard.snapshot().state, 'clicked');
  assert.equal(guard.disarm('user', NOW + 4100), false, 'a click that is out cannot be withdrawn');
  assert.equal(guard.onPositions([long], NOW + 5000), null);
  assert.equal(guard.onPositions(null, NOW + 6000), null, 'an unreadable list proves nothing');
  assert.equal(guard.onPositions([{ ...long, entryText: '$101.00' }], NOW + 7000), 'closed');
  assert.equal(guard.snapshot().state, 'closed');
  assert.deepEqual(guard.snapshot().journal.map(entry => entry.event), ['armed', 'triggered', 'clicked', 'closed']);
  assert.equal(guard.arm({ position: long, price: 100, stopLoss: 99.95, mode: 'close', nowMs: NOW + 8000 }).ok, true, 'a finished guard can be armed again');
});

test('a click that the page never confirms is reported, never repeated', () => {
  const guard = new ExitGuard();
  guard.arm({ position: short, price: 100, stopLoss: 100.05, mode: 'close', nowMs: NOW });
  assert.equal(guard.onQuote(quote(100.06, NOW + 100), NOW + 100).reason, 'stopLoss');
  guard.onCloseResult({ clicked: true }, NOW + 200);
  assert.equal(guard.onPositions([short], NOW + 200 + GUARD_LIMITS.confirmMs - 1), null);
  assert.equal(guard.onPositions([short], NOW + 200 + GUARD_LIMITS.confirmMs), 'unconfirmed');
  assert.equal(guard.onQuote(quote(100.2, NOW + 60_000), NOW + 60_000), null);
  assert.equal(guard.onCloseResult({ clicked: true }, NOW + 60_100), false);
  assert.equal(guard.snapshot().state, 'unconfirmed');
});

test('close failures end the guard loudly; the lock wait is bounded', () => {
  for (const reply of [{ clicked: false, reason: 'ambiguous_position' }, { clicked: false, reason: 'position_not_listed' }, null, undefined, {}]) {
    const guard = new ExitGuard();
    guard.arm({ position: long, price: 100, stopLoss: 99.95, mode: 'close', nowMs: NOW });
    guard.onQuote(quote(99.94, NOW + 100), NOW + 100);
    assert.equal(guard.onCloseResult(reply, NOW + 200), false);
    assert.equal(guard.snapshot().state, 'failed');
  }
  const guard = new ExitGuard();
  guard.arm({ position: long, price: 100, stopLoss: 99.95, mode: 'close', nowMs: NOW });
  guard.onQuote(quote(99.94, NOW + 100), NOW + 100);
  assert.equal(guard.onTimeout(NOW + 200), false);
  assert.equal(guard.onCloseResult({ clicked: false, retry: true, reason: 'close_locked' }, NOW + 100 + GUARD_LIMITS.closeWaitMs), false, 'retries stop at the limit');
  assert.equal(guard.snapshot().state, 'failed');
  const silent = new ExitGuard();
  silent.arm({ position: long, price: 100, stopLoss: 99.95, mode: 'close', nowMs: NOW });
  silent.onQuote(quote(99.94, NOW + 100), NOW + 100);
  assert.equal(silent.onTimeout(NOW + 100 + GUARD_LIMITS.closeWaitMs), true);
  assert.equal(silent.snapshot().note, 'close_window_elapsed');
  const already = new ExitGuard();
  already.arm({ position: long, price: 100, stopLoss: 99.95, mode: 'close', nowMs: NOW });
  already.onQuote(quote(99.94, NOW + 100), NOW + 100);
  already.onCloseResult({ clicked: false, already: true, label: 'Closing…' }, NOW + 200);
  assert.equal(already.snapshot().state, 'clicked');
});

test('alert mode never asks for a click, and a vanished position disarms', () => {
  const guard = new ExitGuard();
  assert.equal(guard.arm({ position: long, price: 100, takeProfit: 100.2, nowMs: NOW }).ok, true);
  assert.equal(guard.snapshot().mode, 'alert', 'alert only is the default');
  assert.deepEqual(guard.onQuote(quote(100.2, NOW + 100), NOW + 100), { type: 'alert', reason: 'takeProfit', price: 100.2 });
  assert.equal(guard.snapshot().state, 'alerted');
  assert.equal(guard.onCloseResult({ clicked: true }, NOW + 200), false);
  assert.equal(guard.snapshot().state, 'alerted');
  const gone = new ExitGuard();
  gone.arm({ position: long, price: 100, stopLoss: 99.95, mode: 'close', nowMs: NOW });
  assert.equal(gone.onPositions(null, NOW + 100), null);
  assert.equal(gone.onPositions([], NOW + 200), 'position_gone');
  assert.equal(gone.snapshot().state, 'idle');
  assert.equal(gone.onQuote(quote(99.9, NOW + 300), NOW + 300), null);
  assert.equal(new ExitGuard().arm({ position: long, price: 100, takeProfit: 101, mode: 'market', nowMs: NOW }).ok, false);
  assert.equal(positionKey(long), 'SOL|long|1000|$100.00');
});

/* ------------------------------------------------------------ page bridge -- */

const cells = (over = {}) => ({ coinText: 'SOL #2', sideText: '1,000× Long', modeText: 'Classic', entryMarkText: '$71.6802 / $71.7001',
  bustText: '$71.6100', sizeText: '$10,000.00', collateralText: '$10.00 JupUSD', valueText: '$12.10 +$2.10',
  buttons: [{ text: '', disabled: false }, { text: 'Close', disabled: false }], ...over });

test('a table row is read exactly or refused', () => {
  const parsed = bridge.parseRow(cells());
  assert.equal(parsed.ok, true);
  assert.deepEqual({ ...parsed.row, close: parsed.row.close.state }, { coin: 'SOL', side: 'long', leverage: 1000, entry: 71.6802,
    entryText: '$71.6802', mark: 71.7001, bust: 71.61, size: '$10,000.00', collateral: '$10.00 JupUSD', value: '$12.10 +$2.10',
    mode: 'Classic', close: 'ready' });
  assert.equal(bridge.parseRow(cells({ coinText: 'GOLD', sideText: '500× Short' })).row.coin, 'XAU');
  assert.equal(bridge.parseRow(cells({ sideText: '500× Short' })).row.leverage, 500);
  assert.equal(bridge.parseRow(cells({ entryMarkText: '$59,905.26 / $59,900.00' })).row.entry, 59905.26);
  for (const [over, reason] of [
    [{ coinText: 'SOL #21,000× Long' }, 'coin_unreadable'], [{ coinText: '' }, 'coin_unreadable'],
    [{ sideText: '1,000× Largo' }, 'side_unreadable'], [{ sideText: '5,000× Long' }, 'leverage_unreadable'],
    [{ entryMarkText: 'Pending / $71.70' }, 'entry_unreadable'], [{ entryMarkText: '71,6802 / 71,70' }, 'entry_unreadable'],
    [{ entryMarkText: '$71.68' }, 'entry_unreadable'],
  ]) assert.deepEqual(bridge.parseRow(cells(over)), { ok: false, reason });
  assert.equal(bridge.money('$1,234.5'), 1234.5);
  for (const bad of ['1.234,5', '1,23', '$', '-5', '0', 'N/A', '$1 2']) assert.equal(bridge.money(bad), null, bad);
});

test('only an enabled button that says exactly Close is ready', () => {
  const state = buttons => bridge.closeState(buttons).state;
  assert.equal(state([{ text: 'Close', disabled: false }]), 'ready');
  assert.equal(state([{ text: 'Close', disabled: true }]), 'disabled');
  assert.equal(state([{ text: 'Close in 12s', disabled: true }]), 'locked');
  assert.equal(state([{ text: 'Closing…', disabled: true }]), 'closing');
  for (const label of ['Close all', 'Close position', 'Locked', 'Settling', '', 'Close in soon']) assert.equal(state([{ text: label, disabled: false }]), 'none', label);
  assert.equal(state([]), 'none');
  assert.equal(state(undefined), 'none');
});

/** The smallest DOM the bridge touches: enough to prove which button it presses. */
function fakeDocument(rows, { headers = ['Position', 'Value / PnL', 'Entry / Mark price', 'Bust price', 'Size', 'Collateral', 'Held', 'Status'], tab = false } = {}) {
  const pressed = [];
  const element = (textContent, extra = {}) => ({ textContent, children: [], getAttribute: () => null, querySelector: () => null, querySelectorAll: () => [], ...extra });
  const button = (label, disabled, id) => element(label, { disabled, click() { pressed.push(id); } });
  const trs = rows.map((row, r) => {
    const side = element(row.side, { nextElementSibling: element(row.mode ?? 'Classic') });
    const position = element('', { querySelector: selector => selector === 'strong' ? element(row.coin) : null,
      querySelectorAll: selector => selector === 'span' ? [element(row.coin), side] : [] });
    const buttons = row.buttons.map(([label, disabled], b) => button(label, disabled, `row${r}:button${b}:${label}`));
    const status = element('', { querySelectorAll: selector => selector === 'button' ? buttons : [] });
    const tds = [position, element(row.value ?? ''), element(row.entryMark), element(row.bust ?? '$1.00'), element('$10,000'), element('$10 JupUSD'), element('12s'), status];
    return element('', { children: tds, getAttribute: name => name === 'aria-busy' && row.busy ? 'true' : null });
  });
  const table = element('', { querySelectorAll: selector => selector === 'thead th' ? headers.map(text => element(text)) : selector === 'tbody tr' ? trs : [] });
  const tabButton = button('Positions (1)', false, 'tab');
  const closeAll = button('Close all', false, 'close-all');
  return { pressed, querySelectorAll: selector => selector === 'table' ? (headers ? [table] : []) : selector === 'button' ? [closeAll, ...(tab ? [tabButton] : [])] : [] };
}
const expect = { coin: 'SOL', side: 'long', leverage: 1000, entryText: '$71.6802' };
const row = (over = {}) => ({ coin: 'SOL', side: '1,000× Long', entryMark: '$71.6802 / $71.70', buttons: [['', false], ['Close', false]], ...over });

test('the bridge presses Close for the one matching row and nothing else', () => {
  const doc = fakeDocument([row({ coin: 'BTC', entryMark: '$59,905.26 / $59,900.00' }), row(), row({ side: '1,000× Short' })]);
  const read = bridge.readPositions(doc);
  assert.deepEqual([read.recognized, read.positions.length, read.pending, read.unreadable, read.problems], [true, 3, 0, 0, []]);
  assert.equal(JSON.stringify(read).includes('click'), false, 'no DOM handle leaves the bridge');
  assert.deepEqual(bridge.closePosition(doc, expect, 1000), { clicked: true, label: 'Close' });
  assert.deepEqual(doc.pressed, ['row1:button1:Close']);
  assert.deepEqual(bridge.closePosition(doc, expect, 2000), { clicked: false, already: true, reason: 'recently_clicked', label: 'Close' });
  assert.deepEqual(doc.pressed, ['row1:button1:Close'], 'no second press inside ten seconds');
});

test('the bridge refuses ambiguity, locks, other modes and unknown pages', () => {
  const other = { ...expect, entryText: '$70.0000' };
  const twins = fakeDocument([row({ entryMark: '$70.0000 / $71' }), row({ entryMark: '$70.0000 / $71' })]);
  assert.deepEqual(bridge.closePosition(twins, other, 1), { clicked: false, reason: 'ambiguous_position' });
  assert.deepEqual(bridge.closePosition(fakeDocument([row()]), other, 1), { clicked: false, reason: 'position_not_listed' });
  const locked = fakeDocument([row({ entryMark: '$70.0000 / $71', buttons: [['Close in 9s', true]] })]);
  assert.deepEqual(bridge.closePosition(locked, other, 1), { clicked: false, retry: true, reason: 'close_locked', label: 'Close in 9s' });
  const busy = fakeDocument([row({ entryMark: '$70.0000 / $71', buttons: [['Close', true]] })]);
  assert.deepEqual(bridge.closePosition(busy, other, 1), { clicked: false, retry: true, reason: 'close_disabled', label: 'Close' });
  const closing = fakeDocument([row({ entryMark: '$70.0000 / $71', buttons: [['Closing…', true]] })]);
  assert.deepEqual(bridge.closePosition(closing, other, 1), { clicked: false, already: true, label: 'Closing…' });
  const lockedMode = fakeDocument([row({ entryMark: '$70.0000 / $71', buttons: [['Locked', true]] })]);
  assert.deepEqual(bridge.closePosition(lockedMode, other, 1), { clicked: false, reason: 'close_unavailable', label: 'Locked' });
  for (const doc of [twins, locked, busy, closing, lockedMode]) assert.deepEqual(doc.pressed, []);
  const opening = fakeDocument([row({ busy: true }), row({ coin: '???' })]);
  assert.deepEqual([bridge.readPositions(opening).pending, bridge.readPositions(opening).unreadable, bridge.readPositions(opening).problems], [1, 1, ['coin_unreadable']]);
  const foreign = fakeDocument([row()], { headers: ['Posición', 'Valor'] });
  assert.deepEqual(bridge.readPositions(foreign), { recognized: false, reason: 'positions_table_not_found', positions: [] });
  assert.deepEqual(bridge.closePosition(foreign, expect, 1), { clicked: false, reason: 'positions_table_not_found' });
  const hidden = fakeDocument([], { headers: null, tab: true });
  assert.deepEqual(bridge.closePosition(hidden, other, 1), { clicked: false, retry: true, reason: 'opened_positions_tab' });
  assert.deepEqual(hidden.pressed, ['tab'], 'selecting the Positions tab is the only other click');
  for (const bad of [null, {}, { ...expect, leverage: '1000' }, { ...expect, side: 'up' }, { ...expect, entryText: '' }]) {
    assert.deepEqual(bridge.closePosition(fakeDocument([row()]), bad, 1), { clicked: false, reason: 'invalid_request' });
  }
});
