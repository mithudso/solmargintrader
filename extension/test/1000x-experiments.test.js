import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SCALP_EXPERIMENTS, VARIANTS, HORIZONS, CALL_HORIZON, DEFAULT_ASSIGNMENTS, PROMOTION, ExperimentBook, variantById,
  validAssignments, readSlots, weightedCall, findPromotions, leaderboard, wilsonLower } from '../src/1000x/scalp-experiments.js';
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

test('the experiment grid is wide: many settings, horizons beyond the six on the main view', () => {
  assert.ok(VARIANTS.length >= 70);
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
  for (const bad of [null, {}, { ...saved, version: 99 }, { ...saved, ids: saved.ids.slice(1) }, { ...saved, horizons: [1] },
    { ...saved, hit: saved.hit.slice(1) }, { ...saved, n: saved.n.map(() => -1) }, { ...saved, hit: saved.hit.map(() => 'x') },
    { ...saved, hit: saved.n.map(value => value + 5) }, { ...saved, n: saved.n.map(() => Infinity) }]) {
    assert.equal(new ExperimentBook().restore(bad), false);
  }
  copy.clear();
  assert.equal(copy.stats('roc_2', 30).n, 0);
  assert.equal(copy.seconds, 0);
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
  return { stats: id => { const row = records[id]; return row ? { ...row, rate: row.n > 0.5 ? row.hit / row.n : null, eff: row.n / CALL_HORIZON, prior: row.prior ?? 0.52 } : { hit: 0, n: 0, rate: null, eff: 0, prior: 0.52 }; } };
}

test('a setting takes a slot only when it is clearly ahead of the one in use', () => {
  const enough = PROMOTION.minEff * CALL_HORIZON * 6;
  const record = (rate, n = enough, prior = 0.52) => ({ hit: rate * n, n, prior });
  const assignments = { ...DEFAULT_ASSIGNMENTS };
  const run = (records, extra = {}) => findPromotions({ assignments, book: fakeBook(records), nowS: 10_000, ...extra });
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

test('one setting is never used by two slots', () => {
  const enough = PROMOTION.minEff * CALL_HORIZON * 6, record = rate => ({ hit: rate * enough, n: enough, prior: 0.52 });
  // Both breakout slots are weak and breakout_45 is the only clear winner: one slot gets it.
  const changes = findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, nowS: 0,
    book: fakeBook({ breakout_20: record(0.5), breakout_60: record(0.5), breakout_45: record(0.64) }) });
  assert.equal(changes.length, 1);
  assert.equal(changes[0].to, 'breakout_45');
  // A setting in use elsewhere is not a candidate: roc_5 is the momentum5 slot's.
  assert.deepEqual(findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, nowS: 0,
    book: fakeBook({ roc_2: record(0.5), roc_5: record(0.7) }) }), []);
});

test('saved assignments are kept only where they are valid', () => {
  assert.deepEqual(validAssignments(null), DEFAULT_ASSIGNMENTS);
  assert.deepEqual(validAssignments({ slope: 'slope_5' }), { ...DEFAULT_ASSIGNMENTS, slope: 'slope_5' });
  // Unknown, wrong kind, and a duplicate each fall back to the slot's default.
  assert.deepEqual(validAssignments({ slope: 'nope', rsi: 'slope_5', breakout20: 'breakout_120', breakout60: 'breakout_120', __proto__: { x: 1 } }),
    { ...DEFAULT_ASSIGNMENTS, breakout20: 'breakout_120' });
  // A slot may not take another slot's default out from under it.
  const swapped = validAssignments({ impulse: 'roc_5' });
  assert.equal(new Set(Object.values(swapped)).size, TILES.length);
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
  const switches = findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, book: made, nowS: 0 });
  assert.deepEqual(switches.map(change => [DEFAULT_ASSIGNMENTS[change.slot], change.to]), rule.switches);
  assert.ok(rule.switches.length >= 3 && rule.switches.length < TILES.length, 'the made-up record makes the rule choose');
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

test('a setting that needs a longer warm-up than the grid is never switched in, and a switched tile never holds the call back', () => {
  const enough = PROMOTION.minEff * CALL_HORIZON * 6, record = rate => ({ hit: rate * enough, n: enough, prior: 0.52 });
  assert.ok(variantById('macd_5').need > PROMOTION.maxNeed && variantById('breakout_120').need > PROMOTION.maxNeed);
  assert.deepEqual(findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, nowS: 0,
    book: fakeBook({ macd_1: record(0.5), macd_5: record(0.7), breakout_20: record(0.5), breakout_60: record(0.5), breakout_120: record(0.7), breakout_300: record(0.7) }) }), []);
  assert.equal(findPromotions({ assignments: { ...DEFAULT_ASSIGNMENTS }, nowS: 0,
    book: fakeBook({ breakout_20: record(0.5), breakout_45: record(0.7) }) })[0].to, 'breakout_45');
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
