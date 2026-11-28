import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SCALP_EXPERIMENTS, VARIANTS, KINDS, HORIZONS, CALL_HORIZON, DEFAULT_ASSIGNMENTS, PROMOTION, RULES, WARMUP_BARS, ExperimentBook, CallTally, variantById,
  validAssignments, readSlots, weightedCall, measuredFor, findPromotions, leaderboard, wilsonLower } from '../src/1000x/scalp-experiments.js';
import { vote } from '../src/1000x/scalp-indicators.js';
import { TILES, SCORE_HORIZONS, HORIZON_S, readTiles, cone, likelyMoveBps } from '../src/1000x/scalp-model.js';

const fixture = JSON.parse(readFileSync(new URL('./fixtures/1000x-scalp-parity.json', import.meta.url), 'utf8'));
const bars = fixture.bars.map(([time, open, high, low, close]) => ({ time, open, high, low, close }));
const near = (a, b, message) => assert.ok(Math.abs(a - b) < 1e-9, `${message}: ${a} vs ${b}`);

/** Bars that rise one cent a second from `start`, or follow `closeAt(i)`. */
function series(count, closeAt = i => 100 + i * 0.01, start = 1_800_000_000) {
  return Array.from({ length: count }, (_, i) => {
    const close = closeAt(i), open = i ? closeAt(i - 1) : close;
    return { time: start + i, open, high: Math.max(open, close), low: Math.min(open, close), close };
  });
}
function feed(book, list) {
  let readings;
  for (let i = 1; i <= list.length; i++) readings = book.observe(list.slice(0, i));
  return readings;
}

test('the experiment grid is wide: hundreds of settings, most for the readings with the most parameters', () => {
  assert.ok(VARIANTS.length >= 300);
  const count = Object.fromEntries(KINDS.map(row => [row.kind, row.count]));
  assert.equal(KINDS.reduce((sum, row) => sum + row.count, 0), VARIANTS.length);
  // MACD is tested over every pairing of its fast and slow averages, each with several signal spans.
  const macd = VARIANTS.filter(variant => variant.kind === 'macd');
  const pairs = new Set(macd.map(variant => `${variant.params.fast}/${variant.params.slow}`));
  assert.ok(pairs.size >= 36, `${pairs.size} fast/slow pairs`);
  assert.ok(macd.length >= 100 && new Set(macd.map(variant => variant.params.signal)).size >= 3);
  assert.ok(macd.every(variant => variant.params.slow > variant.params.fast && variant.need === 3 * variant.params.slow));
  assert.ok(pairs.has('12/26') && variantById('macd_12_26_9').label === 'MACD 12/26/9');
  // The other readings with more than one parameter get a grid too.
  assert.ok(count.psar >= 36 && count.supertrend >= 36 && count.emacross >= 36, JSON.stringify(count));
  assert.ok(new Set(VARIANTS.filter(variant => variant.kind === 'psar').map(variant => variant.params.step)).size >= 3, 'the SAR step is varied on its own');
  for (const kind of ['roc', 'breakout', 'bop', 'zigzag', 'donchian', 'efficiency', 'slope', 'rsi', 'zscore']) assert.ok(count[kind] >= 10, `${kind}: ${count[kind]}`);
  // No setting needs more bars than the window keeps.
  assert.ok(Math.max(...VARIANTS.map(variant => variant.need)) <= 900);
  assert.equal(WARMUP_BARS, 78, 'the grid still warms up on its starting settings');
  assert.equal(new Set(VARIANTS.map(variant => variant.id)).size, VARIANTS.length);
  assert.deepEqual(HORIZONS, [3, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300]);
  assert.equal(CALL_HORIZON, 30);
  for (const variant of VARIANTS) {
    assert.equal(variant.prior.length, HORIZONS.length, variant.id);
    assert.ok(variant.prior.every(rate => rate === null || (rate > 0.3 && rate < 0.7)), `${variant.id} recorded rates are plausible`);
  }
  // Each tile of the main grid starts on the setting the study chose for it, of the same kind.
  assert.deepEqual(Object.keys(DEFAULT_ASSIGNMENTS), TILES.map(tile => tile.key));
  assert.equal(new Set(Object.values(DEFAULT_ASSIGNMENTS)).size, TILES.length);
  // The six intervals shown under each tile are among those tested.
  for (const horizon of SCORE_HORIZONS) assert.ok(HORIZONS.includes(horizon), `${horizon}s`);
  for (const variant of VARIANTS) assert.ok(variant.kindName && variant.describe && typeof variant.read === 'function', variant.id);
});

test('every setting votes exactly as the Python study does on the shared bars', () => {
  const tail = 40, first = bars.length - tail;
  const compared = new Map(VARIANTS.map(variant => [variant.id, 0]));
  for (let i = first; i < bars.length; i++) {
    const prefix = bars.slice(0, i + 1);
    for (const variant of VARIANTS) {
      const expected = fixture.variant_votes[variant.id][i - first];
      const actual = prefix.length >= variant.need ? vote(variant.read(prefix)) : null;
      assert.equal(actual, expected, `${variant.id} @${i}`);
      if (expected !== null) compared.set(variant.id, compared.get(variant.id) + 1);
    }
  }
  for (const [id, count] of compared) assert.ok(count > 0, `${id} was compared at least once`);
});

test('the default slots read the same values as the original tiles', () => {
  const book = new ExperimentBook();
  const readings = book.observe(bars);
  const slots = readSlots(DEFAULT_ASSIGNMENTS, readings, bars.length), tiles = readTiles(bars);
  for (const [i, tile] of tiles.entries()) {
    assert.equal(slots[i].key, tile.key);
    assert.equal(slots[i].vote, tile.vote, tile.key);
    assert.equal(slots[i].ready, tile.ready, tile.key);
    if (tile.value !== null) near(slots[i].value, tile.value, tile.key);
    assert.equal(slots[i].tuned, false);
  }
});

test('the book scores each setting against the move over each horizon, without looking ahead', () => {
  const book = new ExperimentBook();
  // A steady climb: every momentum setting votes up and is right at every horizon.
  feed(book, series(200));
  const up = book.stats('roc_2', 30);
  assert.ok(up.n > 100 && up.rate === 1, `rising market: ${up.hit}/${up.n}`);
  assert.ok(book.stats('roc_2', 300).n === 0, 'nothing settles at five minutes within 200 seconds');
  assert.equal(book.stats('roc_2', 3).rate, 1);
  // A call is counted only once its horizon has passed: 200 bars, need 3, horizon 30.
  assert.ok(up.n <= 200 - 30);
  assert.equal(book.stats('nope', 30).n, 0);
  assert.equal(book.stats('roc_2', 31).n, 0);
  // A flat outcome counts for nobody.
  const flat = new ExperimentBook();
  feed(flat, series(120, () => 100));
  assert.equal(flat.stats('roc_2', 30).n, 0);
});

test('a setting that is wrong scores below half, and a feed break settles nothing across the gap', () => {
  const book = new ExperimentBook();
  // Up for 60 s, then down for 60 s: momentum calls made just before the turn are wrong.
  feed(book, series(60));
  const before = book.stats('roc_2', 30).n;
  book.reset();
  const later = series(60, i => 100.6 - i * 0.01, 1_800_000_000 + 500);
  feed(book, later);
  const after = book.stats('roc_2', 30);
  assert.ok(after.n > before, 'counts survive the break');
  assert.equal(after.rate, 1, 'calls from before the break were never scored against prices after it');
  // The same bar twice, or an older bar, is ignored.
  const again = book.observe(later);
  assert.equal(again.size, 0);
});

test('counts decay, so the rates follow the market that is trading now', () => {
  const book = new ExperimentBook();
  feed(book, series(400));
  const n = book.stats('roc_2', 30).n;
  assert.ok(n < 400 - 30 - 2 && n > 300, `decayed count ${n}`);
  assert.equal(book.seconds, 400);
});

test('saved counts restore exactly, and anything that does not fit this grid is refused', () => {
  const book = new ExperimentBook();
  feed(book, series(150));
  const saved = JSON.parse(JSON.stringify(book));
  const copy = new ExperimentBook();
  assert.equal(copy.restore(saved), true);
  // Counts are saved to three decimals.
  assert.ok(Math.abs(copy.stats('roc_2', 30).n - book.stats('roc_2', 30).n) < 1e-3);
  assert.ok(Math.abs(copy.stats('roc_2', 30).hit - book.stats('roc_2', 30).hit) < 1e-3);
  assert.equal(copy.seconds, 150);
  for (const bad of [null, {}, { ...saved, version: 99 }, { ...saved, ids: saved.ids.slice(1) }, { ...saved, horizons: [1] }, { ...saved, ids: saved.ids.map(() => 'roc_2') },
    { ...saved, ids: saved.ids.map(id => `old_${id}`) }, { ...saved, horizons: saved.horizons.map(String) },
    { ...saved, hit: saved.hit.slice(1) }, { ...saved, n: saved.n.map(() => -1) }, { ...saved, hit: saved.hit.map(() => 'x') },
    { ...saved, hit: saved.n.map(value => value + 5) }, { ...saved, n: saved.n.map(() => Infinity) }]) {
    assert.equal(new ExperimentBook().restore(bad), false);
  }
  copy.clear();
  assert.equal(copy.stats('roc_2', 30).n, 0);
  assert.equal(copy.seconds, 0);
});

test('a record saved by the grid before this one is carried over setting by setting', () => {
  // The earlier grid: fewer settings, two of them under names that have since changed, one that is gone.
  const ids = ['roc_2', 'macd_1', 'psar_0p02_0p2', 'psar_0p05_0p3', 'slope_60'], horizons = [...HORIZONS], at = horizons.indexOf(30);
  const old = { version: 2, ids, horizons, seconds: 5000, hit: new Array(ids.length * horizons.length).fill(0), n: new Array(ids.length * horizons.length).fill(0) };
  for (const [row] of ids.entries()) { old.n[row * horizons.length + at] = 1000 + row; old.hit[row * horizons.length + at] = 500 + 10 * row; }
  const book = new ExperimentBook();
  assert.equal(book.restore(old), true);
  assert.deepEqual([book.stats('roc_2').n, book.stats('roc_2').hit], [1000, 500]);
  assert.deepEqual([book.stats('macd_12_26_9').n, book.stats('macd_12_26_9').hit], [1001, 510], 'MACD x1 is MACD 12/26/9');
  assert.equal(book.stats('psar_0p02_0p02_0p2').n, 1002, 'the old SAR used one number for start and step');
  assert.equal(book.stats('slope_60').n, 1004);
  assert.equal(book.stats('macd_3_10_5').n, 0, 'a new setting starts empty');
  assert.equal(book.stats('roc_2', 60).n, 0);
  assert.equal(book.seconds, 5000);
  // An interval the old grid lacked starts empty; one this grid lacks is dropped.
  const narrow = { ...old, horizons: [30, 7], hit: ids.flatMap((_, row) => [500 + row, 1]), n: ids.flatMap((_, row) => [1000 + row, 2]) };
  const other = new ExperimentBook();
  assert.equal(other.restore(narrow), true);
  assert.equal(other.stats('roc_2', 30).n, 1000); assert.equal(other.stats('roc_2', 3).n, 0);
  // A failed restore leaves the book as it was.
  assert.equal(book.restore({ ...old, hit: old.hit.map(() => -1) }), false);
  assert.equal(book.stats('roc_2').n, 1000);
  // Saved choices follow the renamed settings too, and so does a lookup by an old name.
  assert.deepEqual(validAssignments({ macd: 'macd_1', psar: 'psar_0p01_0p1', slope: 7 }), { ...DEFAULT_ASSIGNMENTS, psar: 'psar_0p01_0p01_0p1' });
  assert.equal(variantById('macd_1'), variantById('macd_12_26_9')); assert.equal(variantById('macd_2'), null);
  // A saved count of seconds no record could hold is not believed; the rates still are.
  const absurd = new ExperimentBook();
  assert.equal(absurd.restore({ ...old, seconds: 1e12 }), true);
  assert.deepEqual([absurd.seconds, absurd.stats('roc_2').n], [0, 1000]);
});

test('with no live record, a tile weighs in by how far its recorded rate is above a coin flip', () => {
  const book = new ExperimentBook();
  const tiles = readSlots(DEFAULT_ASSIGNMENTS, book.observe(bars), bars.length);
  const call = weightedCall(tiles, book);
  assert.equal(call.ready, true);
  near(call.weights.reduce((a, b) => a + b, 0), 1, 'weights sum to one');
  const at30 = HORIZONS.indexOf(30);
  const edges = tiles.map(tile => Math.max(0, variantById(tile.variant).prior[at30] - 0.5));
  const total = edges.reduce((a, b) => a + b, 0);
  for (const [i, tile] of tiles.entries()) near(call.weights[i], edges[i] / total, `weight of ${tile.key}`);
  near(call.score, tiles.reduce((sum, tile, i) => sum + call.weights[i] * tile.vote, 0), 'score');
  // The two breakout tiles carry the best recorded record, so the most weight.
  const heaviest = tiles[call.weights.indexOf(Math.max(...call.weights))];
  assert.equal(heaviest.kind, 'breakout');
  assert.ok(Math.abs(call.score) <= 1);
});

test('the weighted call: tiers from the weighted share, a tile at or under half has no say', () => {
  const rates = { a: 0.6, b: 0.55, c: 0.5, d: 0.4 };
  const book = { blended: id => rates[id] };
  const tile = (variant, vote, ready = true) => ({ key: variant, variant, vote, ready });
  // a carries 2/3 of the weight, b 1/3; c and d none.
  let call = weightedCall([tile('a', 1), tile('b', 1), tile('c', -1), tile('d', -1)], book);
  near(call.score, 1, 'the losing tiles do not count');
  assert.deepEqual([call.tier, call.direction, call.up, call.down, call.net], ['strong', 'up', 2, 2, 0]);
  near(call.weights[0], 2 / 3, 'weight a'); assert.equal(call.weights[2], 0); assert.equal(call.weights[3], 0);
  call = weightedCall([tile('a', 1), tile('b', -1), tile('c', 1), tile('d', 1)], book);
  near(call.score, 1 / 3, 'a against b');
  assert.deepEqual([call.tier, call.direction], ['mixed', 'flat']);
  call = weightedCall([tile('a', -1), tile('b', 0), tile('c', 1), tile('d', 1)], book);
  near(call.score, -2 / 3, 'a alone');
  assert.deepEqual([call.tier, call.direction], ['lean', 'down']);
  assert.equal(call.measured, SCALP_EXPERIMENTS.measured.lean);
  // Not ready until every tile has a reading.
  call = weightedCall([tile('a', 1), tile('b', null, false)], book);
  assert.deepEqual([call.ready, call.tier, call.direction, call.score, call.measured], [false, 'warming', 'flat', 0, null]);
  // Nobody above half: fall back to one tile, one vote.
  call = weightedCall([tile('c', 1), tile('d', 1), tile('d', -1), tile('c', 1)], book);
  near(call.score, 0.5, 'unweighted fallback');
  assert.equal(call.tier, 'lean');
});

test('a live record moves a weight away from the recorded rate', () => {
  const book = new ExperimentBook();
  feed(book, series(400));
  const id = 'roc_2', at30 = HORIZONS.indexOf(30), prior = variantById(id).prior[at30];
  const { hit, n } = book.stats(id, 30);
  near(book.blended(id), (hit + SCALP_EXPERIMENTS.prior_seconds * prior) / (n + SCALP_EXPERIMENTS.prior_seconds), 'blend');
  assert.ok(book.blended(id) > prior + 0.2, 'a run of right calls lifts it');
  near(new ExperimentBook().blended(id), prior, 'no record: the recorded rate');
});

test('Wilson lower bound', () => {
  assert.ok(Math.abs(wilsonLower(0.5, 100, 1.96) - 0.40383) < 1e-5, 'textbook value');
  assert.equal(wilsonLower(0.6, 0), 0);
  assert.equal(wilsonLower(NaN, 10), 0);
  assert.ok(wilsonLower(0.6, 400) > wilsonLower(0.6, 40));
});

/** A stand-in book with chosen records at the call horizon. */
function fakeBook(records) {
  const stats = id => { const row = records[id]; return row ? { ...row, rate: row.n > 0.5 ? row.hit / row.n : null, eff: row.n / CALL_HORIZON, prior: row.prior ?? 0.52 } : { hit: 0, n: 0, rate: null, eff: 0, prior: 0.52 }; };
  // The same blend as the real book: the live record pulled toward the recorded rate.
  return { stats, blended: id => { const row = stats(id); return (row.hit + SCALP_EXPERIMENTS.prior_seconds * row.prior) / (row.n + SCALP_EXPERIMENTS.prior_seconds); } };
}

test('the default rule: a tile takes the setting of its kind with the highest hit rate, once both are known and it is a point ahead', () => {
  assert.equal(PROMOTION.rule, 'best');
  assert.deepEqual(RULES, ['best', 'clear', 'off']);
  assert.deepEqual([PROMOTION.bestMinEff, PROMOTION.bestLockS, PROMOTION.bestMargin], [40, 1800, 0.01]);
  const enough = PROMOTION.bestMinEff * CALL_HORIZON * 6;
  const record = (rate, n = enough, prior = 0.52) => ({ hit: rate * n, n, prior });
  const run = (records, extra = {}) => findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, book: fakeBook(records), nowS: 10_000, ...extra });
  const only = (changes, slot) => changes.filter(change => change.slot === slot).map(change => [change.from, change.to]);
  // Two points ahead is enough: no cautious estimate is asked for.
  let changes = run({ slope_60: record(0.52), slope_5: record(0.54) });
  assert.deepEqual(only(changes, 'slope'), [['slope_60', 'slope_5']]);
  assert.ok(changes.find(change => change.slot === 'slope').rate > changes.find(change => change.slot === 'slope').incumbentRate + PROMOTION.bestMargin);
  // Under a point ahead is not enough.
  assert.deepEqual(only(run({ slope_60: record(0.52), slope_5: record(0.527) }), 'slope'), []);
  // Both settings need 40 independent calls' worth first: 1,200 settled calls at 30 seconds.
  assert.deepEqual(only(run({ slope_60: record(0.5), slope_5: record(0.9, 1199) }), 'slope'), []);
  assert.deepEqual(only(run({ slope_60: record(0.5), slope_5: record(0.9, 1200) }), 'slope'), [['slope_60', 'slope_5']]);
  assert.deepEqual(only(run({ slope_60: record(0.5, 100), slope_5: record(0.9) }), 'slope'), []);
  assert.deepEqual(run({ slope_60: record(0, 0, 0.51), slope_10: record(0, 0, 0.55) }), [], 'the recording alone switches nothing');
  // A tile that changed keeps its setting for half an hour.
  assert.deepEqual(only(run({ slope_60: record(0.5), slope_5: record(0.6) }, { locks: { slope: 10_000 - PROMOTION.bestLockS + 1 } }), 'slope'), []);
  assert.equal(only(run({ slope_60: record(0.5), slope_5: record(0.6) }, { locks: { slope: 10_000 - PROMOTION.bestLockS } }), 'slope').length, 1);
  // A setting that needs many bars may take a slot.
  assert.ok(variantById('macd_20_90_9').need > WARMUP_BARS);
  assert.deepEqual(only(run({ macd_12_26_9: record(0.5), macd_20_90_9: record(0.6) }), 'macd'), [['macd_12_26_9', 'macd_20_90_9']]);
  // The best of several wins; the setting in use stays when it is the best, or tied for it.
  assert.deepEqual(only(run({ slope_60: record(0.5), slope_5: record(0.6), slope_10: record(0.66) }), 'slope'), [['slope_60', 'slope_10']]);
  assert.deepEqual(only(run({ slope_60: record(0.7), slope_5: record(0.6) }), 'slope'), []);
  const level = Object.fromEntries(VARIANTS.filter(variant => variant.kind === 'slope').map(variant => [variant.id, record(0.55)]));
  assert.deepEqual(only(run(level), 'slope'), [], 'equal estimates change nothing');
  // Another kind never takes the slot, however good.
  assert.deepEqual(only(run({ slope_60: record(0.6), breakout_120: record(0.9) }), 'slope'), []);
  // Off changes nothing, and an unknown rule is refused.
  assert.deepEqual(run({ slope_60: record(0.5), slope_5: record(0.9) }, { rule: 'off' }), []);
  assert.throws(() => run({}, { rule: 'sometimes' }), RangeError);
});

test('the default rule fills the slots of one kind with different settings, best first', () => {
  const enough = PROMOTION.bestMinEff * CALL_HORIZON * 6, record = rate => ({ hit: rate * enough, n: enough, prior: 0.52 });
  // Momentum has three slots. The three best momentum settings end up in them, each once.
  const records = { roc_2: record(0.5), roc_5: record(0.5), roc_60: record(0.5), roc_13: record(0.7), roc_21: record(0.65), roc_34: record(0.6), roc_8: record(0.55) };
  let assignments = { ...DEFAULT_ASSIGNMENTS };
  for (const change of findPromotions({ assignments, book: fakeBook(records), nowS: 0 })) assignments = { ...assignments, [change.slot]: change.to };
  assert.deepEqual([assignments.impulse, assignments.momentum5, assignments.momentum60], ['roc_13', 'roc_21', 'roc_34']);
  assert.equal(new Set(Object.values(assignments)).size, TILES.length);
  // A second look changes nothing for those slots: the rule has settled.
  assert.deepEqual(findPromotions({ assignments, book: fakeBook(records), nowS: 30 }).filter(change => change.from.startsWith('roc_')), []);
});

test('the cautious rule: a setting takes a slot only when it is clearly ahead of the one in use', () => {
  const enough = PROMOTION.minEff * CALL_HORIZON * 6;
  const record = (rate, n = enough, prior = 0.52) => ({ hit: rate * n, n, prior });
  const assignments = { ...DEFAULT_ASSIGNMENTS };
  const run = (records, extra = {}) => findPromotions({ assignments, book: fakeBook(records), nowS: 10_000, rule: 'clear', ...extra });
  // slope_60 is in use at 50%; slope_5 at 62% over plenty of calls is clearly ahead.
  let changes = run({ slope_60: record(0.5), slope_5: record(0.62) });
  assert.deepEqual(changes.map(change => [change.slot, change.from, change.to]), [['slope', 'slope_60', 'slope_5']]);
  assert.ok(changes[0].lower > 0.5 && changes[0].lower < 0.62);
  // Ahead, but not clearly: the cautious estimate is under the incumbent's rate.
  assert.deepEqual(run({ slope_60: record(0.5), slope_5: record(0.53) }), []);
  // Too few calls on either side.
  assert.deepEqual(run({ slope_60: record(0.5), slope_5: record(0.9, 100) }), []);
  assert.deepEqual(run({ slope_60: record(0.5, 100), slope_5: record(0.62) }), []);
  // Better than the incumbent but not an edge at all.
  assert.deepEqual(run({ slope_60: record(0.3), slope_5: record(0.45) }), []);
  // The recording says the opposite.
  assert.deepEqual(run({ slope_60: record(0.5, enough, 0.53), slope_5: record(0.62, enough, 0.51) }), []);
  // A slot that changed recently is left alone.
  assert.deepEqual(run({ slope_60: record(0.5), slope_5: record(0.62) }, { locks: { slope: 10_000 - PROMOTION.lockS + 1 } }), []);
  assert.equal(run({ slope_60: record(0.5), slope_5: record(0.62) }, { locks: { slope: 10_000 - PROMOTION.lockS } }).length, 1);
  // Another kind never takes the slot, however good.
  assert.deepEqual(run({ slope_60: record(0.5), breakout_120: record(0.7) }), []);
  // The best of several challengers wins.
  changes = run({ slope_60: record(0.5), slope_5: record(0.6), slope_10: record(0.66) });
  assert.equal(changes[0].to, 'slope_10');
});

test('the cautious rule never puts one setting in two slots', () => {
  const enough = PROMOTION.minEff * CALL_HORIZON * 6, record = rate => ({ hit: rate * enough, n: enough, prior: 0.52 });
  // Both breakout slots are weak and breakout_45 is the only clear winner: one slot gets it.
  const changes = findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, nowS: 0, rule: 'clear',
    book: fakeBook({ breakout_20: record(0.5), breakout_60: record(0.5), breakout_45: record(0.64) }) });
  assert.equal(changes.length, 1);
  assert.equal(changes[0].to, 'breakout_45');
  // A setting in use elsewhere is not a candidate: roc_5 is the momentum5 slot's.
  assert.deepEqual(findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, nowS: 0, rule: 'clear',
    book: fakeBook({ roc_2: record(0.5), roc_5: record(0.7) }) }), []);
});

test('saved assignments are kept only where they are valid', () => {
  assert.deepEqual(validAssignments(null), DEFAULT_ASSIGNMENTS);
  assert.deepEqual(validAssignments({ slope: 'slope_5' }), { ...DEFAULT_ASSIGNMENTS, slope: 'slope_5' });
  // Unknown, wrong kind, and a duplicate each fall back to the slot's default.
  assert.deepEqual(validAssignments({ slope: 'nope', rsi: 'slope_5', breakout20: 'breakout_120', breakout60: 'breakout_120', __proto__: { x: 1 } }),
    { ...DEFAULT_ASSIGNMENTS, breakout20: 'breakout_120' });
  // A slot whose own setting was taken by another starts on the first free one of its kind, and every other choice is kept.
  const swapped = validAssignments({ impulse: 'roc_5', slope: 'slope_5', momentum5: 'bogus' });
  assert.equal(new Set(Object.values(swapped)).size, TILES.length);
  assert.deepEqual(swapped, { ...DEFAULT_ASSIGNMENTS, impulse: 'roc_5', momentum5: 'roc_1', slope: 'slope_5' });
  assert.deepEqual(Object.keys(swapped), Object.keys(DEFAULT_ASSIGNMENTS));
  // The three momentum tiles holding the three fastest settings, as the default rule leaves them, come back as saved.
  const fastest = { impulse: 'roc_1', momentum5: 'roc_2', momentum60: 'roc_3' };
  assert.deepEqual(validAssignments(fastest), { ...DEFAULT_ASSIGNMENTS, ...fastest });
  // A tuned slot is marked, and reads its new setting.
  const book = new ExperimentBook();
  const slots = readSlots({ ...DEFAULT_ASSIGNMENTS, slope: 'slope_5' }, book.observe(bars), bars.length);
  const slope = slots.find(slot => slot.key === 'slope');
  assert.deepEqual([slope.variant, slope.tuned, slope.label, slope.need], ['slope_5', true, 'Slope 5s', 5]);
});

test('the leaderboard ranks by the best current estimate: the recording first, live results as they settle', () => {
  const book = new ExperimentBook();
  const cold = leaderboard(book, 30);
  assert.equal(cold.length, VARIANTS.length);
  assert.ok(cold.every(row => row.rate === null && row.lower === 0));
  for (let i = 1; i < cold.length; i++) assert.ok((cold[i - 1].prior ?? 0.5) >= (cold[i].prior ?? 0.5), 'recorded order while nothing is live');
  assert.equal(cold[0].kind, 'breakout');
  near(cold[0].blended, cold[0].prior, 'no live calls: the recorded rate');
  feed(book, series(300));
  const warm = leaderboard(book, 30);
  assert.ok(warm[0].rate === 1 && warm[0].lower > 0.5 && warm[0].blended > cold[0].blended);
  for (let i = 1; i < warm.length; i++) assert.ok(warm[i - 1].blended >= warm[i].blended);
  // Other intervals rank on their own records.
  assert.equal(leaderboard(book, 300).every(row => row.n === 0), true);
  near(book.blended('roc_2', 300), variantById('roc_2').prior[HORIZONS.indexOf(300)], 'an interval with no live calls');
});

test('the Python study and this module run the same record, the same weighted call and the same switch rule', () => {
  const rule = fixture.rule;
  assert.equal(rule.horizon, CALL_HORIZON);
  assert.equal(CALL_HORIZON, HORIZON_S, 'the call, the chart and the score book share one horizon');
  // 1. The running record after the shared bars: decay order and scoring, setting by setting.
  const book = new ExperimentBook();
  const readings = feed(book, bars);
  for (const variant of VARIANTS) {
    const [hit, n] = rule.counts[variant.id], live = book.stats(variant.id, CALL_HORIZON);
    assert.ok(Math.abs(live.hit - hit) < 1e-6 && Math.abs(live.n - n) < 1e-6, `${variant.id}: ${live.hit}/${live.n} vs ${hit}/${n}`);
  }
  assert.ok(Object.values(rule.counts).some(([, n]) => n > 100), 'the record is not empty');
  // 2. The weighted call at the last bar.
  const tiles = readSlots(DEFAULT_ASSIGNMENTS, readings, bars.length), call = weightedCall(tiles, book);
  assert.deepEqual(tiles.map(tile => tile.vote), rule.votes);
  for (const [i, weight] of rule.weights.entries()) near(call.weights[i], weight, `weight ${tiles[i].key}`);
  near(call.score, rule.score, 'score');
  assert.equal(call.tier, rule.tier);
  // 3. A made-up record with many calls everywhere: the weights and every switch the rule makes.
  const saved = JSON.parse(JSON.stringify(new ExperimentBook())), at = HORIZONS.indexOf(CALL_HORIZON);
  for (const variant of VARIANTS) {
    saved.n[variant.index * HORIZONS.length + at] = rule.made_up.calls;
    saved.hit[variant.index * HORIZONS.length + at] = rule.made_up.rates[variant.index] * rule.made_up.calls;
  }
  const made = new ExperimentBook();
  assert.equal(made.restore(saved), true);
  const allUp = tiles.map(tile => ({ ...tile, ready: true, vote: 1 }));
  for (const [i, weight] of rule.made_up.weights.entries()) near(weightedCall(allUp, made).weights[i], weight, `made-up weight ${tiles[i].key}`);
  for (const name of ['clear', 'best']) {
    const switches = findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, book: made, nowS: 0, rule: name });
    assert.deepEqual(switches.map(change => [DEFAULT_ASSIGNMENTS[change.slot], change.to]), rule.switches[name], `${name} rule`);
  }
  assert.ok(rule.switches.clear.length >= 3 && rule.switches.clear.length < TILES.length, 'the made-up record makes the cautious rule choose');
  assert.ok(rule.switches.best.length >= rule.switches.clear.length, 'on a long record the default rule switches at least as often as the cautious one');
  // 4. The inverse-vote aggregate: the same score as the study's, on the real record and the made-up one.
  near(weightedCall(tiles, book, { inverse: true }).score, rule.inverse_score, 'inverse score');
  near(weightedCall(allUp, made, { inverse: true }).score, rule.made_up.inverse_score_all_up, 'made-up inverse score');
  assert.ok(Math.abs(rule.made_up.inverse_score_all_up) < 1, 'some made-up tiles are under half and vote the other way');
});

test('inverse votes: a reading under half votes the other way, by how far under it is', () => {
  const rates = { a: 0.6, b: 0.55, c: 0.5, d: 0.4 };
  const book = { blended: id => rates[id] };
  const tile = (variant, vote, ready = true) => ({ key: variant, variant, vote, ready });
  // Edges 0.10, 0.05, 0 and 0.10 the wrong way: d carries as much say as a, turned round.
  const tiles = [tile('a', 1), tile('b', 1), tile('c', -1), tile('d', -1)];
  const call = weightedCall(tiles, book, { inverse: true });
  near(call.weights[0], 0.4, 'a'); near(call.weights[1], 0.2, 'b'); assert.equal(call.weights[2], 0); near(call.weights[3], 0.4, 'd');
  assert.deepEqual(call.inverted, [false, false, false, true]);
  near(call.score, 1, 'd says down, so its inverse vote is up');
  assert.deepEqual([call.tier, call.direction, call.inverse], ['strong', 'up', true]);
  // The same tiles without inverse votes: d sits out, and nothing is marked.
  const plain = weightedCall(tiles, book);
  near(plain.score, 1, 'a and b only'); assert.deepEqual(plain.inverted, [false, false, false, false]); assert.equal(plain.inverse, false);
  // The wrong reading agreeing with the good ones now pulls against them.
  near(weightedCall([tile('a', 1), tile('b', 1), tile('c', 1), tile('d', 1)], book, { inverse: true }).score, 0.2, 'a + b - d');
  // Nobody off a coin flip: one tile, one vote, nothing inverted.
  const flat = weightedCall([tile('c', 1), tile('c', -1), tile('c', 1), tile('c', 1)], book, { inverse: true });
  near(flat.score, 0.5, 'unweighted'); assert.deepEqual(flat.inverted, [false, false, false, false]);
  // Each choice quotes its own replayed record.
  assert.equal(weightedCall(tiles, book).measured, SCALP_EXPERIMENTS.measured.strong);
  assert.equal(weightedCall(tiles, book, { measured: measuredFor({ rule: 'best' }) }).measured, SCALP_EXPERIMENTS.measured_rules.best.strong);
  assert.equal(measuredFor({ rule: 'clear' }), SCALP_EXPERIMENTS.measured_rules.clear);
  assert.equal(measuredFor({ rule: 'off' }), SCALP_EXPERIMENTS.measured);
  assert.equal(measuredFor({ rule: 'best', inverse: true }), SCALP_EXPERIMENTS.measured_inverse.best);
  assert.equal(measuredFor({ rule: 'clear', inverse: true }), SCALP_EXPERIMENTS.measured_inverse.off);
  for (const table of [SCALP_EXPERIMENTS.measured_rules.best, SCALP_EXPERIMENTS.measured_rules.clear, SCALP_EXPERIMENTS.measured_inverse.off, SCALP_EXPERIMENTS.measured_inverse.best]) {
    assert.ok(table.strong.hit > 0.45 && table.strong.hit < 0.6 && table.strong.live && table.strong.path_bps.length === 6);
  }
});

test('the inverse-vote experiment keeps a live record of both aggregates, call by call', () => {
  const tally = new CallTally(), call = (tier, score) => ({ ready: true, tier, score });
  // Price rises one cent a second. Sit-out calls up (right); inverse calls down (wrong).
  const list = series(100);
  for (const bar of list) tally.observe(bar, { sitout: call('strong', 0.9), inverse: call('lean', -0.5) });
  let stats = tally.stats();
  assert.ok(stats.sitout.strong.n > 60 && stats.sitout.strong.n <= 70, `settled only after 30 s: ${stats.sitout.strong.n}`);
  assert.equal(stats.sitout.strong.rate, 1); assert.equal(stats.inverse.lean.rate, 0);
  assert.equal(stats.sitout.lean.n, 0); assert.equal(stats.sitout.lean.rate, null);
  near(stats.sitout.called.n, stats.sitout.strong.n, 'called is strong and lean together');
  near(stats.sitout.strong.eff, stats.sitout.strong.n / CALL_HORIZON, 'independent calls');
  // A mixed score is scored by its sign; a warming call, or a zero score, is not scored.
  const quiet = new CallTally();
  for (const bar of list) quiet.observe(bar, { sitout: call('mixed', 0.1), inverse: { ready: false, tier: 'warming', score: 0 } });
  assert.equal(quiet.stats().sitout.mixed.rate, 1); assert.equal(quiet.stats().sitout.called.n, 0); assert.equal(quiet.stats().inverse.called.n, 0);
  // A feed break settles nothing across the gap, the same bar twice is ignored, and counts are kept.
  const before = stats.sitout.strong.n;
  tally.reset();
  for (const bar of series(20, i => 50 - i, 1_800_000_000 + 1000)) tally.observe(bar, { sitout: call('strong', 0.9), inverse: call('strong', -0.9) });
  stats = tally.stats();
  assert.ok(stats.sitout.strong.n < before && stats.sitout.strong.n > before - 1 && stats.sitout.strong.rate === 1, 'only decay moved the count');
  // Saved and restored exactly; anything else is refused.
  const saved = JSON.parse(JSON.stringify(tally)), copy = new CallTally();
  assert.equal(copy.restore(saved), true);
  assert.ok(Math.abs(copy.stats().sitout.strong.n - stats.sitout.strong.n) < 1e-3);
  for (const bad of [null, {}, { ...saved, version: 2 }, { ...saved, tiers: ['strong'] }, { ...saved, hit: saved.hit.slice(1) }, { ...saved, n: saved.n.map(() => -1) },
    { ...saved, hit: saved.n.map(value => value + 5) }, { ...saved, n: saved.n.map(() => 1e300) }]) assert.equal(new CallTally().restore(bad), false);
  copy.clear();
  assert.equal(copy.stats().sitout.strong.n, 0);
});

test('a reversal is scored call by call: exact counts, not just a rising market', () => {
  // Up one cent a second for 100 seconds, then down. Momentum 2s is right until the turn comes within 30 seconds.
  const count = 200, closeAt = i => 100 + 0.01 * (i <= 100 ? i : 200 - i), list = series(count, closeAt);
  const book = new ExperimentBook();
  feed(book, list);
  const decay = Math.exp(-Math.LN2 / SCALP_EXPERIMENTS.half_life_s);
  for (const horizon of [3, 30, 60]) {
    let hit = 0, n = 0, wrong = 0;
    for (let i = 2; i + horizon < count; i++) {
      const vote = Math.sign(closeAt(i) - closeAt(i - 2)), outcome = Math.sign(closeAt(i + horizon) - closeAt(i));
      if (!vote || !outcome) continue;
      // Scored when bar i + horizon closes, then faded once for every bar after that.
      const weight = decay ** (count - 1 - (i + horizon));
      n += weight; if (vote === outcome) hit += weight; else wrong += 1;
    }
    const live = book.stats('roc_2', horizon);
    assert.ok(Math.abs(live.n - n) < 1e-9 && Math.abs(live.hit - hit) < 1e-9, `${horizon}s: ${live.hit}/${live.n} vs ${hit}/${n}`);
    assert.ok(wrong > 0 && live.rate < 1 && live.rate > 0.5, `${horizon}s has wrong calls around the turn`);
  }
  // A setting that keeps pointing the wrong way scores under half: a fade of the same market.
  const fade = new ExperimentBook();
  feed(fade, series(count, i => 100 + 0.2 * Math.sin(i / 3)));
  assert.ok(fade.stats('roc_60', 10).n > 20);
  assert.ok(fade.stats('roc_2', 10).rate < 0.5, 'two-second momentum on a ten-second swing is wrong more often than right');
});

test('every setting gives a number once it has its bars, and the measured tiers ship their own path', () => {
  for (const variant of VARIANTS) {
    if (bars.length < variant.need) continue;
    const value = variant.read(bars.slice(0, Math.max(variant.need, 120)));
    assert.ok(value === null ? variant.kind === 'zigzag' : Number.isFinite(value), `${variant.id} at its need: ${value}`);
  }
  for (const tier of ['mixed', 'lean', 'strong']) {
    const measured = SCALP_EXPERIMENTS.measured[tier];
    assert.ok(measured && measured.hit > 0.45 && measured.hit < 0.6 && measured.live, `${tier} is measured`);
    assert.deepEqual(measured.path_bps.map(point => point[0]), [5, 10, 15, 20, 25, 30]);
    near(measured.path_bps.at(-1)[1], measured.mean_follow_bps, `${tier} path ends at its average move`);
  }
  // The chart's likely line follows the path it is handed, and is flat when handed none.
  const path = SCALP_EXPERIMENTS.measured.strong.path_bps;
  const line = cone({ price: 100, sigmaBps: 1, direction: 'down', tier: 'strong', path });
  near((line.at(-1).mid / 100 - 1) * 1e4, -path.at(-1)[1], 'weighted path at 30 s');
  near(likelyMoveBps('strong', 7.5, path), (path[0][1] + path[1][1]) / 2, 'interpolated');
  assert.ok(cone({ price: 100, sigmaBps: 1, direction: 'up', tier: 'strong', path: [] }).every(step => step.mid === 100));
});

test('a switched-in setting never lengthens the warm-up or holds the call back', () => {
  // MACD 20/90/9 needs 270 bars. Until the window has them its tile stays on the starting setting.
  const long = variantById('macd_20_90_9'), assignments = { ...DEFAULT_ASSIGNMENTS, macd: long.id };
  assert.equal(long.need, 270);
  const early = new ExperimentBook(), first = readSlots(assignments, feed(early, bars.slice(0, 100)), 100).find(slot => slot.key === 'macd');
  assert.deepEqual([first.variant, first.tuned, first.waiting, first.ready, first.need], ['macd_12_26_9', false, long.id, true, 78]);
  assert.equal(weightedCall(readSlots(assignments, feed(new ExperimentBook(), bars.slice(0, 100)), 100), early).ready, true, 'the call is ready on the starting warm-up');
  const later = readSlots(assignments, feed(new ExperimentBook(), bars.slice(0, 300)), 300).find(slot => slot.key === 'macd');
  assert.deepEqual([later.variant, later.tuned, later.waiting, later.ready], [long.id, true, null, true]);
  assert.equal(readSlots(DEFAULT_ASSIGNMENTS, new Map(), 0).every(slot => slot.waiting === null), true);
  // A waiting tile never reads a setting another tile is reading. Here the first breakout tile waits for
  // Breakout 450s while the second has taken the first one's starting setting: the first reads the next free one.
  const crossed = { ...DEFAULT_ASSIGNMENTS, breakout20: 'breakout_450', breakout60: 'breakout_20' };
  const tiles = readSlots(crossed, feed(new ExperimentBook(), bars.slice(0, 100)), 100);
  assert.equal(new Set(tiles.map(tile => tile.variant)).size, tiles.length, 'sixteen tiles, sixteen settings');
  const waitingTile = tiles.find(tile => tile.key === 'breakout20');
  assert.deepEqual([waitingTile.variant, waitingTile.waiting, waitingTile.ready, tiles.find(tile => tile.key === 'breakout60').variant], ['breakout_5', 'breakout_450', true, 'breakout_20']);
  // Once it has its bars each tile reads what was chosen for it.
  assert.deepEqual(readSlots(crossed, feed(new ExperimentBook(), bars.slice(0, 460)), 460).filter(tile => tile.kind === 'breakout').map(tile => [tile.variant, tile.waiting]),
    [['breakout_450', null], ['breakout_20', null]]);
  // ZigZag has no reading before its first swing. As a starting tile that is warming; as a switched-in one it is neutral.
  const flat = series(80, () => 100), book = new ExperimentBook(), readings = feed(book, flat);
  const starting = readSlots(DEFAULT_ASSIGNMENTS, readings, flat.length).find(slot => slot.key === 'zigzag');
  assert.deepEqual([starting.ready, starting.vote], [false, null]);
  const switched = readSlots({ ...DEFAULT_ASSIGNMENTS, zigzag: 'zigzag_5' }, readings, flat.length).find(slot => slot.key === 'zigzag');
  assert.deepEqual([switched.ready, switched.vote, switched.tuned], [true, 0, true]);
  // Before it has its bars it is still warming.
  assert.equal(readSlots({ ...DEFAULT_ASSIGNMENTS, zigzag: 'zigzag_5' }, new Map(), 10).find(slot => slot.key === 'zigzag').ready, false);
});

test('stored counts larger than a live record can ever reach are refused', () => {
  const saved = JSON.parse(JSON.stringify(new ExperimentBook()));
  const limit = 1 / (1 - Math.exp(-Math.LN2 / SCALP_EXPERIMENTS.half_life_s));
  saved.n[0] = limit; saved.hit[0] = limit * 0.9;
  assert.equal(new ExperimentBook().restore(saved), true, 'the largest live value is accepted');
  saved.n[0] = limit * 2; saved.hit[0] = limit * 2;
  assert.equal(new ExperimentBook().restore(saved), false);
  saved.n[0] = 1e300; saved.hit[0] = 1e300;
  assert.equal(new ExperimentBook().restore(saved), false);
});
