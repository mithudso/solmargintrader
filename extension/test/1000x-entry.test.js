import test from 'node:test';
import assert from 'node:assert/strict';

import { EntryTracker, ENTRY_LIMITS, SIZE_FRACTIONS, validateEntry, newPosition } from '../src/1000x/entry-plan.js';
import { resolveLevels, parseDistance, priceLike, positionKey } from '../src/1000x/exit-guard.js';
import { SlopeScore, HorizonScore, SCORE_HORIZONS, HORIZON_S, bustFraction } from '../src/1000x/scalp-model.js';
import '../src/1000x/page-bridge.js';

const bridge = globalThis.__smt1000xBridge;
const NOW = 1_800_000_000_000;
const form = (over = {}) => ({ recognized: true, mode: 'Classic', busy: false, longEnabled: true, shortEnabled: true, leverage: 1000, ...over });
const plan = (over = {}) => ({ side: 'long', fraction: 0.5, takeProfitBps: 10, stopLossBps: 5, bustBps: bustFraction(1000) * 1e4,
  form: form(), guardLive: false, pending: false, ...over });
const row = (over = {}) => ({ coin: 'SOL', side: 'long', leverage: 1000, entry: 100, entryText: '$100.0000', bust: 99.902, ...over });

test('levels in basis points become prices on the right side of the entry', () => {
  const long = resolveLevels({ unit: 'bp', takeProfitText: '10', stopLossText: '5', position: row() });
  assert.deepEqual(long.errors, []);
  assert.ok(Math.abs(long.takeProfit - 100.1) < 1e-9 && Math.abs(long.stopLoss - 99.95) < 1e-9);
  const short = resolveLevels({ unit: 'bp', takeProfitText: '10', stopLossText: '5', position: row({ side: 'short' }) });
  assert.ok(Math.abs(short.takeProfit - 99.9) < 1e-9 && Math.abs(short.stopLoss - 100.05) < 1e-9);
  assert.deepEqual(resolveLevels({ unit: 'bp', takeProfitText: ' ', stopLossText: '', position: row() }), { takeProfit: null, stopLoss: null, errors: [] });
  assert.deepEqual(resolveLevels({ unit: 'price', takeProfitText: '100.2', stopLossText: '', position: row() }), { takeProfit: 100.2, stopLoss: null, errors: [] });
  assert.match(resolveLevels({ unit: 'price', takeProfitText: '+10', position: row() }).errors.join(' '), /not a plain price/);
  assert.match(resolveLevels({ unit: 'bp', stopLossText: '5bp', position: row() }).errors.join(' '), /not a plain distance/);
  assert.match(resolveLevels({ unit: 'bp', takeProfitText: '10', position: row({ entry: null }) }).errors.join(' '), /entry price could not be read/);
  assert.match(resolveLevels({ unit: 'bp', takeProfitText: '10', position: null }).errors.join(' '), /entry price could not be read/);
  assert.match(resolveLevels({ unit: 'ticks', takeProfitText: '10', position: row() }).errors.join(' '), /Unknown level unit/);
  assert.equal(parseDistance('9.8'), 9.8);
  for (const bad of ['0', '-5', '10001', '5 bp', '', '1e2']) assert.equal(parseDistance(bad), null, bad);
});

test('a distance that looks like the market price is flagged as a price typed into the wrong unit', () => {
  assert.equal(priceLike(71.9, 71.7), true, 'SOL at 71.70 with 71.90 typed as bp');
  assert.equal(priceLike(70, 71.7), true);
  assert.equal(priceLike(73.8, 71.7), true);
  for (const [distance, price] of [[5, 71.7], [9.8, 71.7], [50, 71.7], [69, 71.7], [75, 71.7], [50, 59_900], [10, 735]]) assert.equal(priceLike(distance, price), false, `${distance} bp at ${price}`);
  for (const [distance, price] of [[null, 71.7], [71.9, null], [NaN, 71.7], [71.9, 0], [-71.9, 71.7]]) assert.equal(priceLike(distance, price), false);
});

test('an entry is checked before anything is sent', () => {
  assert.deepEqual(validateEntry(plan()), { ok: true, errors: [] });
  assert.equal(validateEntry(plan({ takeProfitBps: null, stopLossBps: null, bustBps: null })).ok, true, 'no levels need no bust distance');
  assert.deepEqual(SIZE_FRACTIONS, [0.25, 0.5, 0.75, 1]);
  for (const [over, pattern] of [
    [{ side: 'up' }, /long or short/], [{ fraction: 0.6 }, /Choose a size/], [{ pending: true }, /already out/],
    [{ guardLive: true }, /Disarm it first/], [{ form: { recognized: false } }, /could not be read/], [{ form: null }, /could not be read/],
    [{ form: form({ mode: 'Blitz' }) }, /Only Classic/], [{ form: form({ busy: true }) }, /busy/],
    [{ form: form({ longEnabled: false }) }, /Long button disabled/], [{ side: 'short', form: form({ shortEnabled: false }) }, /Short button disabled/],
    [{ takeProfitBps: -1 }, /positive distance/], [{ form: form({ leverage: null }) }, /leverage could not be read/], [{ stopLossBps: 9.8 }, /beyond the bust distance \(9\.8 bp\)/],
    [{ stopLossBps: 12 }, /liquidated first/], [{ bustBps: null }, /leverage could not be read/],
  ]) {
    const result = validateEntry(plan(over));
    assert.equal(result.ok, false, JSON.stringify(over));
    assert.match(result.errors.join(' '), pattern);
  }
});

test('the first press only arms the button; the second sends once', () => {
  const tracker = new EntryTracker();
  const request = { side: 'long', fraction: 0.5, takeProfitBps: 10, stopLossBps: 5, mode: 'close', before: ['a'], confirm: true };
  assert.deepEqual(tracker.begin({ ...request, nowMs: NOW }), { send: false, reason: 'confirm' });
  assert.equal(tracker.snapshot().state, 'confirming');
  assert.deepEqual(tracker.begin({ ...request, side: 'short', nowMs: NOW + 500 }), { send: false, reason: 'confirm' }, 'another side starts over');
  assert.deepEqual(tracker.begin({ ...request, side: 'short', fraction: 1, nowMs: NOW + 900 }), { send: false, reason: 'confirm' }, 'another size starts over');
  assert.deepEqual(tracker.begin({ ...request, side: 'short', fraction: 1, nowMs: NOW + 900 + ENTRY_LIMITS.confirmMs + 1 }), { send: false, reason: 'confirm' }, 'a late second press is a new first press');
  assert.equal(tracker.onTick(NOW + 20_000), true, 'an unconfirmed press lapses');
  assert.equal(tracker.snapshot().state, 'idle');
  tracker.begin({ ...request, nowMs: NOW + 30_000 });
  assert.deepEqual(tracker.begin({ ...request, nowMs: NOW + 30_150 }), { send: false, reason: 'confirm' }, 'the second half of a double-click does not confirm');
  assert.deepEqual(tracker.begin({ ...request, nowMs: NOW + 30_000 + ENTRY_LIMITS.confirmGapMs - 1 }), { send: false, reason: 'confirm' });
  assert.equal(tracker.snapshot().state, 'confirming');
  assert.deepEqual(tracker.begin({ ...request, nowMs: NOW + 31_000 }), { send: true });
  assert.equal(tracker.pending, true);
  assert.deepEqual(tracker.begin({ ...request, nowMs: NOW + 31_100 }), { send: false, reason: 'pending' }, 'no second request while one is out');
  assert.equal(tracker.reset(), false, 'a request that is out cannot be dropped');
  const quick = new EntryTracker();
  assert.deepEqual(quick.begin({ ...request, confirm: false, nowMs: NOW }), { send: true });
});

test('the opened position is the one new row for that market and side', () => {
  const tracker = new EntryTracker();
  const before = [row({ entryText: '$99.0000' }), row({ coin: 'BTC', entryText: '$60,000.00' })];
  tracker.begin({ side: 'long', fraction: 1, takeProfitBps: 10, stopLossBps: null, mode: 'alert', before: before.map(positionKey), confirm: false, nowMs: NOW });
  const ask = (positions, nowMs) => tracker.onPositions({ positions, coin: 'SOL', keyOf: positionKey, nowMs });
  assert.equal(ask([...before, row()], NOW + 100), null, 'nothing counts before the page confirmed the press');
  tracker.onReply({ clicked: true, amountText: '7.9', leverage: 1000 }, NOW + 200);
  assert.equal(ask(before, NOW + 300), null);
  assert.equal(ask(null, NOW + 400), null);
  assert.equal(ask([...before, row({ side: 'short' }), row({ coin: 'BTC' })], NOW + 500), null, 'another side or market is not it');
  const opened = ask([...before, row()], NOW + 600);
  assert.equal(opened.position.entryText, '$100.0000');
  assert.deepEqual([opened.request.takeProfitBps, opened.request.stopLossBps, opened.request.mode, opened.request.amountText], [10, null, 'alert', '7.9']);
  assert.equal(tracker.snapshot().state, 'opened');
  assert.equal(ask([...before, row()], NOW + 700), null, 'reported once');
  assert.equal(newPosition({ before: [], positions: [row(), row({ entryText: '$100.5000' })], coin: 'SOL', side: 'long', keyOf: positionKey }), null, 'two new rows are ambiguous');
  // Rows are counted: a new position with the same entry text as an old one is still the new one.
  const twin = newPosition({ before: [positionKey(row())], positions: [row(), row()], coin: 'SOL', side: 'long', keyOf: positionKey });
  assert.equal(twin?.entryText, '$100.0000');
  assert.equal(newPosition({ before: [positionKey(row())], positions: [row()], coin: 'SOL', side: 'long', keyOf: positionKey }), null);
  assert.equal(newPosition({ before: [], positions: [row({ leverage: 500 })], coin: 'SOL', side: 'long', leverage: 1000, keyOf: positionKey }), null, 'another leverage is not this entry');
  assert.equal(newPosition({ before: [], positions: [row({ leverage: 500 })], coin: 'SOL', side: 'long', leverage: 500, keyOf: positionKey })?.leverage, 500);
});

test('a press that fails or is never listed is reported and never repeated', () => {
  const failed = new EntryTracker();
  failed.begin({ side: 'short', fraction: 0.25, before: [], confirm: false, nowMs: NOW });
  failed.onReply({ clicked: false, reason: 'side_disabled' }, NOW + 100);
  assert.deepEqual([failed.snapshot().state, failed.snapshot().note, failed.pending], ['failed', 'side_disabled', false]);
  // No answer is not a "no": the page may have pressed. The entry stays out and watched.
  for (const reply of [null, { clicked: false, reason: 'page_timeout' }, { clicked: false, reason: 'page_unreachable' }, { clicked: false, reason: 'extension_unreachable' }]) {
    const silent = new EntryTracker();
    silent.begin({ side: 'short', fraction: 0.25, before: [], confirm: false, nowMs: NOW });
    silent.onReply(reply, NOW + 100);
    assert.deepEqual([silent.snapshot().state, silent.pending, silent.snapshot().request.uncertain], ['sent', true, true]);
    assert.deepEqual(silent.begin({ side: 'short', fraction: 0.25, before: [], confirm: false, nowMs: NOW + 200 }), { send: false, reason: 'pending' });
    const late = silent.onPositions({ positions: [row({ side: 'short' })], coin: 'SOL', keyOf: positionKey, nowMs: NOW + 9000 });
    assert.equal(late.position.side, 'short', 'the position it did open is still found and protected');
  }
  const unseen = new EntryTracker();
  unseen.begin({ side: 'long', fraction: 0.25, before: [], confirm: false, nowMs: NOW });
  unseen.onReply({ clicked: true }, NOW + 100);
  assert.equal(unseen.onPositions({ positions: [], coin: 'SOL', keyOf: positionKey, nowMs: NOW + 100 + ENTRY_LIMITS.appearMs - 1 }), null);
  assert.equal(unseen.snapshot().state, 'sent');
  // The wait ends even when the list cannot be read at all.
  unseen.onPositions({ positions: null, coin: 'SOL', keyOf: positionKey, nowMs: NOW + 100 + ENTRY_LIMITS.appearMs });
  assert.deepEqual([unseen.snapshot().state, unseen.snapshot().note, unseen.pending], ['unseen', 'position_not_seen', false]);
  // A wallet prompt answered late: the position is still adopted so its levels can be armed.
  const adopted = unseen.onPositions({ positions: [row()], coin: 'SOL', keyOf: positionKey, nowMs: NOW + 100 + ENTRY_LIMITS.appearMs + 30_000 });
  assert.equal(adopted.position.entryText, '$100.0000');
  const stale = new EntryTracker();
  stale.begin({ side: 'long', fraction: 0.25, before: [], confirm: false, nowMs: NOW });
  stale.onReply({ clicked: true }, NOW + 100);
  stale.onPositions({ positions: [], coin: 'SOL', keyOf: positionKey, nowMs: NOW + 100 + ENTRY_LIMITS.appearMs });
  stale.onPositions({ positions: [], coin: 'SOL', keyOf: positionKey, nowMs: NOW + 100 + ENTRY_LIMITS.lateMs });
  assert.equal(stale.onPositions({ positions: [row()], coin: 'SOL', keyOf: positionKey, nowMs: NOW + 200 + ENTRY_LIMITS.lateMs }), null, 'after ten minutes a new row is no longer tied to this request');
  assert.equal(stale.reset(), true);
});

test('the slope gauge scores each slope sign against the next 30 seconds', () => {
  const score = new SlopeScore();
  const rows = vote => [{ window: 5, ready: true, slopeVote: vote }, { window: 10, ready: false, slopeVote: null }];
  for (let t = 0; t < HORIZON_S; t++) score.observe({ time: 100 + t, close: 100 }, rows(t === 0 ? 1 : t === 1 ? -1 : 0));
  assert.deepEqual(score.stats().get(5), { hit: 0, miss: 0, n: 0, rate: null }, 'nothing settles before 30 seconds');
  score.observe({ time: 130, close: 101 }, rows(1));
  score.observe({ time: 131, close: 101 }, rows(0));
  assert.deepEqual(score.stats().get(5), { hit: 1, miss: 1, n: 2, rate: 0.5 });
  assert.equal(score.stats().get(10).n, 0, 'a window that is still warming makes no call');
  score.observe({ time: 131, close: 50 }, rows(1));
  assert.equal(score.stats().get(5).n, 2, 'a repeated second is ignored');
  score.reset();
  for (let t = 132; t <= 170; t++) score.observe({ time: t, close: 101 }, rows(0));
  assert.equal(score.stats().get(5).n, 2, 'calls open at a feed break are never settled');
  assert.equal(score.stats().size, 6);
});

test('each tile is scored at every interval against the move that followed', () => {
  assert.deepEqual(SCORE_HORIZONS, [5, 10, 20, 30, 60, 300]);
  const score = new HorizonScore(['a', 'b']);
  // Price rises one unit a second for 12 seconds: an up vote is right at 5 s and 10 s, a down vote wrong.
  for (let t = 0; t <= 12; t++) score.observe({ time: 100 + t, close: 100 + t }, { a: 1, b: t < 3 ? -1 : 0, c: 1 });
  const at = (key, horizon) => score.stats(key).find(row => row.horizon === horizon);
  assert.deepEqual(at('a', 5), { horizon: 5, hit: 8, n: 8, rate: 1 });
  assert.deepEqual(at('a', 10), { horizon: 10, hit: 3, n: 3, rate: 1 });
  assert.deepEqual(at('a', 20), { horizon: 20, hit: 0, n: 0, rate: null }, 'nothing settles before its interval has passed');
  assert.deepEqual(at('b', 5), { horizon: 5, hit: 0, n: 3, rate: 0 }, 'a neutral vote makes no call');
  assert.equal(score.stats('c').every(row => row.n === 0), true, 'an unknown tile is not scored');
  score.observe({ time: 112, close: 1 }, { a: -1 });
  assert.equal(at('a', 5).n, 8, 'a repeated second is ignored');
  // A flat outcome is not counted, and nothing is scored across a feed break.
  const flat = new HorizonScore(['a'], [5]);
  for (let t = 0; t <= 5; t++) flat.observe({ time: t + 1, close: 100 }, { a: 1 });
  assert.equal(flat.stats('a')[0].n, 0);
  const broken = new HorizonScore(['a'], [5]);
  for (let t = 1; t <= 4; t++) broken.observe({ time: t, close: 100 + t }, { a: 1 });
  broken.reset();
  for (let t = 5; t <= 9; t++) broken.observe({ time: t, close: 100 + t }, { a: 1 });
  assert.equal(broken.stats('a')[0].n, 0, 'calls made before the break are dropped');
  broken.observe({ time: 10, close: 200 }, { a: 1 });
  assert.deepEqual(broken.stats('a')[0], { horizon: 5, hit: 1, n: 1, rate: 1 });
  // Old results leave the running window.
  const rolling = new HorizonScore(['a'], [1], 10);
  for (let t = 1; t <= 40; t++) rolling.observe({ time: t, close: 100 + t }, { a: 1 });
  assert.equal(rolling.stats('a')[0].n, 11);
});

/* ------------------------------------------------------------- order form -- */

test('amounts are read exactly and three quarters is rounded down', () => {
  assert.equal(bridge.amount('15.80352'), '15.80352');
  assert.equal(bridge.amount('1,234.5'), '1234.5');
  for (const bad of ['', '0', '0.00', '1.234,5', '15.8 JupUSD', '-1', '.5', '1e3']) assert.equal(bridge.amount(bad), null, bad);
  assert.equal(bridge.threeQuarters('15.80352'), '11.85264');
  assert.equal(bridge.threeQuarters('10'), '7.5');
  assert.equal(bridge.threeQuarters('3'), '2.25');
  assert.equal(bridge.threeQuarters('0.5'), '0.375');
  assert.equal(bridge.threeQuarters('10.00'), '7.5');
  assert.equal(bridge.threeQuarters('0.000001'), '0');
  assert.equal(bridge.amount(bridge.threeQuarters('0.000001')), null, 'a result of zero is not an amount');
  assert.equal(bridge.threeQuarters('123456789012.123456789'), '92592591759.092592591');
});

/** A stand-in for the page's order form: quick-size buttons fill the input a moment later, as the page does. */
function fakeForm({ mode = 'Classic', max = '16', balance = max, leverage = '1,000×', sideDisabled = false, busy = false, error = '', acceptTyped = true,
  stateFollows = true, visible = true, quickWorks = true, start = '', presetWorks = true } = {}) {
  const pressed = [], pending = [];
  const shown = { leverage };
  const element = (textContent, attrs = {}, extra = {}) => ({ textContent, disabled: false, getAttribute: name => attrs[name] ?? null, ...extra });
  // `state` is what the page's own model holds; the line under the amount is drawn from it.
  const page = { state: start, mode };
  class Input { get value() { return this.shown; } set value(next) { pressed.push(`typed:${next}`); if (acceptTyped) { this.shown = next; if (stateFollows) page.state = next; } } }
  const input = new Input(); input.shown = start; input.dispatchEvent = () => true;
  const fill = (label, text) => element(label, {}, { click() { pressed.push(label); if (quickWorks) pending.push(() => { input.shown = text; page.state = text; }); } });
  const side = name => element(name, { 'data-side': name, 'aria-busy': busy ? 'true' : null }, { disabled: sideDisabled, click() { pressed.push(`side:${name}`); } });
  const buttons = [fill('25%', (Number(max) / 4).toString()), fill('Half', (Number(max) / 2).toString()), fill('Max', max),
    element('', { 'aria-label': `Available balance: ${balance} JupUSD` }), side('long'), side('short'),
    // The page's leverage presets: pressing one moves aria-pressed a moment later.
    ...[leverage, '500×', '700×'].map(text => ({ textContent: text, disabled: false, getAttribute: name => name === 'aria-pressed' ? String(shown.leverage === text) : null,
      click() { pressed.push(text); if (presetWorks) pending.push(() => { shown.leverage = text; }); } }))];
  const formNode = { getAttribute: name => name === 'aria-label' ? 'Degen market order' : null, getClientRects: () => visible ? [{}] : [],
    querySelector: selector => selector === '#degen-amount' ? input : selector === '#degen-amount-error' ? (error ? { textContent: error } : null)
      : selector === '#degen-amount-hint' ? { textContent: page.state ? `≈ $${page.state}` : '' } : null,
    querySelectorAll: selector => selector === 'button' ? buttons : [] };
  const doc = { querySelectorAll: selector => selector === 'form' ? [formNode] : [],
    querySelector: selector => selector.startsWith('nav') ? { textContent: ` ${page.mode} ` } : null };
  // Each wait lets the page "render" what the last click queued.
  const wait = async () => { for (const run of pending.splice(0)) run(); };
  return { doc, pressed, wait, input, page };
}

test('the order form is read without touching it', () => {
  const { doc, pressed } = fakeForm({ max: '15.80352' });
  assert.deepEqual(bridge.readOrderForm(doc), { recognized: true, mode: 'Classic', amountText: '', balanceText: '15.80352 JupUSD', leverage: 1000,
    longEnabled: true, shortEnabled: true, busy: false, error: '' });
  assert.deepEqual(pressed, []);
  assert.deepEqual(bridge.readOrderForm(fakeForm({ visible: false }).doc), { recognized: false, reason: 'order_form_not_found' });
  assert.equal(bridge.readOrderForm(fakeForm({ leverage: '1.5×' }).doc).leverage, null);
  assert.equal(bridge.readOrderForm(fakeForm({ sideDisabled: true, busy: true }).doc).longEnabled, false);
});

test('an entry presses the page’s own size button, then its side button once', async () => {
  let clock = 1_000_000;
  const options = fake => ({ now: () => clock, wait: fake.wait });
  for (const [fraction, label, amount] of [[0.25, '25%', '4'], [0.5, 'Half', '8'], [1, 'Max', '16']]) {
    const fake = fakeForm();
    clock += 10_000;
    assert.deepEqual(await bridge.openPosition(fake.doc, { side: 'long', fraction }, options(fake)), { clicked: true, amountText: amount, leverage: 1000 });
    assert.deepEqual(fake.pressed, [label, 'side:long']);
  }
  const three = fakeForm({ max: '15.80352' });
  clock += 10_000;
  assert.deepEqual(await bridge.openPosition(three.doc, { side: 'short', fraction: 0.75 }, options(three)), { clicked: true, amountText: '11.85264', leverage: 1000 });
  assert.deepEqual(three.pressed, ['Max', 'typed:11.85264', 'side:short'], 'three quarters reads the page’s Max and types the rest');
  // The page's Max may sit a little under the balance (a fee reserve); that still counts as all of it.
  const reserve = fakeForm({ max: '15.2', balance: '16' });
  clock += 10_000;
  assert.equal((await bridge.openPosition(reserve.doc, { side: 'long', fraction: 1 }, options(reserve))).clicked, true);
  const again = fakeForm();
  clock += 4000;
  assert.deepEqual(await bridge.openPosition(again.doc, { side: 'long', fraction: 1 }, options(again)), { clicked: false, reason: 'recently_opened' });
  assert.deepEqual(again.pressed, [], 'nothing is pressed inside five seconds of the last entry');
});

test('a chosen leverage presses the page’s own preset before the size', async () => {
  let clock = 2_000_000;
  const fake = fakeForm();
  assert.deepEqual(await bridge.openPosition(fake.doc, { side: 'long', fraction: 0.5, leverage: 500 }, { now: () => clock, wait: fake.wait }), { clicked: true, amountText: '8', leverage: 500 });
  assert.deepEqual(fake.pressed, ['500×', 'Half', 'side:long']);
  const same = fakeForm();
  clock += 10_000;
  assert.equal((await bridge.openPosition(same.doc, { side: 'long', fraction: 1, leverage: 1000 }, { now: () => clock, wait: same.wait })).leverage, 1000);
  assert.deepEqual(same.pressed, ['Max', 'side:long'], 'a preset that is already selected is not pressed');
  const stuck = fakeForm({ presetWorks: false });
  clock += 10_000;
  assert.deepEqual(await bridge.openPosition(stuck.doc, { side: 'short', fraction: 1, leverage: 500 }, { now: () => clock, wait: stuck.wait }), { clicked: false, reason: 'leverage_not_set' });
  assert.deepEqual(stuck.pressed, ['500×'], 'nothing else is pressed when the page keeps its leverage');
  for (const leverage of [700, 250, '500', 0]) {
    const bad = fakeForm();
    clock += 10_000;
    assert.deepEqual(await bridge.openPosition(bad.doc, { side: 'long', fraction: 1, leverage }, { now: () => clock, wait: bad.wait }), { clicked: false, reason: 'invalid_request' });
    assert.deepEqual(bad.pressed, []);
  }
});

test('two requests at once press once, and a slow page is not pressed late', async () => {
  let clock = 3_000_000;
  const fake = fakeForm();
  let release;
  const parked = new Promise(resolve => { release = resolve; });
  // The first call is parked in its first wait while the second arrives.
  const first = bridge.openPosition(fake.doc, { side: 'long', fraction: 1 }, { now: () => clock, wait: async () => { await parked; await fake.wait(); } });
  const second = await bridge.openPosition(fake.doc, { side: 'long', fraction: 1 }, { now: () => clock + 6000, wait: fake.wait });
  assert.deepEqual(second, { clicked: false, reason: 'page_busy' });
  release();
  assert.equal((await first).clicked, true);
  assert.deepEqual(fake.pressed, ['Max', 'side:long'], 'one side press for two requests');
  // A hidden tab runs timers slowly: by the time the form settled, the owner has stopped expecting the press.
  const slow = fakeForm();
  clock += 20_000;
  const started = clock;
  const result = await bridge.openPosition(slow.doc, { side: 'short', fraction: 0.5 }, { now: () => clock, wait: async () => { clock += 4000; await slow.wait(); } });
  assert.deepEqual(result, { clicked: false, reason: 'too_slow' });
  assert.ok(clock - started > 6000);
  assert.equal(slow.pressed.some(item => item.startsWith('side:')), false);
  // The page left this market while the form settled.
  const moved = fakeForm();
  clock += 20_000;
  assert.deepEqual(await bridge.openPosition(moved.doc, { side: 'long', fraction: 0.25 }, { now: () => clock, wait: moved.wait, stillValid: () => false }), { clicked: false, reason: 'page_changed' });
  assert.deepEqual(moved.pressed, ['25%']);
});

test('anything unexpected stops before the side button', async () => {
  let clock = 5_000_000;
  const attempt = async (options, request = { side: 'long', fraction: 0.5 }) => {
    const fake = fakeForm(options);
    clock += 10_000;
    const result = await bridge.openPosition(fake.doc, request, { now: () => clock, wait: fake.wait });
    assert.equal(fake.pressed.some(item => item.startsWith('side:')), false, JSON.stringify(options));
    return [result.reason, fake.pressed];
  };
  assert.deepEqual(await attempt({ mode: 'Blitz' }), ['mode_not_classic', []]);
  assert.deepEqual(await attempt({ visible: false }), ['order_form_not_found', []]);
  assert.deepEqual(await attempt({ busy: true }), ['page_busy', []]);
  assert.deepEqual(await attempt({ sideDisabled: true }), ['side_disabled', ['Half']]);
  assert.deepEqual(await attempt({ error: 'Not enough JupUSD.' }), ['amount_rejected', ['Half']]);
  assert.deepEqual(await attempt({ max: '0' }), ['balance_unreadable', []]);
  // A value left in the field is not taken for the size the button should have set.
  assert.deepEqual(await attempt({ quickWorks: false, start: '5' }), ['amount_unexpected', ['Half']]);
  assert.deepEqual(await attempt({ quickWorks: false, start: '5' }, { side: 'short', fraction: 0.75 }), ['amount_unexpected', ['Max']]);
  assert.deepEqual(await attempt({ quickWorks: false }), ['amount_unexpected', ['Half']]);
  assert.deepEqual(await attempt({ max: '8', balance: '16' }, { side: 'long', fraction: 1 }), ['amount_unexpected', ['Max']], 'a Max far under the balance is not "all"');
  assert.deepEqual(await attempt({ acceptTyped: false, max: '15.80352' }, { side: 'long', fraction: 0.75 }), ['amount_not_accepted', ['Max', 'typed:11.85264']]);
  // The field shows the typed amount but the page's own state never took it: the old Max would be submitted.
  assert.deepEqual(await attempt({ stateFollows: false, max: '15.80352' }, { side: 'long', fraction: 0.75 }), ['amount_not_accepted', ['Max', 'typed:11.85264']]);
  for (const bad of [null, {}, { side: 'up', fraction: 0.5 }, { side: 'long', fraction: 0.6 }, { side: 'long' }]) assert.deepEqual(await attempt({}, bad), ['invalid_request', []]);
});
