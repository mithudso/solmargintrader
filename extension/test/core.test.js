import test from 'node:test';
import assert from 'node:assert/strict';

import {
  gridLevels,
  planGrid,
  sideForLevel,
  intentKey,
  capitalRequirement,
  rungWidthBps,
  pairedExitLevel,
  nearestLevelIndex,
  expectedRoundTripUsd,
  SPACING,
  SIDE,
  DIRECTION,
} from '../src/core/grid.js';

import { reconcile, tick, pricesMatch, matchIntent } from '../src/core/engine.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { INTENT_STATUS, ConfigStore } from '../src/storage/store.js';
import { normaliseOrders } from '../src/venues/triggerVenue.js';

import {
  evaluate,
  admitBatch,
  normaliseState,
  VERDICT,
  DEFAULT_LIMITS,
  dayKey,
} from '../src/core/risk.js';

import { matchFifo, snapshot, equityCurve, maxDrawdown, fillsToCsv } from '../src/core/pnl.js';

const near = (a, b, eps = 1e-9) =>
  assert.ok(Math.abs(a - b) < eps, `expected ${a} to be within ${eps} of ${b}`);

// ---------------------------------------------------------------- grid levels

test('arithmetic spacing matches the hand-computed ladder', () => {
  assert.deepEqual(gridLevels({ lower: 100, upper: 200, rungs: 5, spacing: SPACING.ARITH }), [
    100, 125, 150, 175, 200,
  ]);
});

test('geometric spacing gives every rung an equal ratio', () => {
  const levels = gridLevels({ lower: 100, upper: 200, rungs: 5, spacing: SPACING.GEOM });
  const ratio = 2 ** 0.25; // 1.189207115...
  near(levels[1], 100 * ratio, 1e-9);
  near(levels[2], 100 * ratio ** 2, 1e-9); // 141.4213562
  near(levels[3], 100 * ratio ** 3, 1e-9);
  // Endpoints are pinned exactly, not left to float drift.
  assert.equal(levels[0], 100);
  assert.equal(levels[4], 200);
  for (let i = 1; i < levels.length; i++) near(levels[i] / levels[i - 1], ratio, 1e-12);
});

test('rung width in bps is the per-round-trip gross edge', () => {
  // 2^(1/4) - 1 = 18.9207115% -> 1892.07 bps
  near(rungWidthBps({ lower: 100, upper: 200, rungs: 5 }), (2 ** 0.25 - 1) * 10_000, 1e-6);
});

test('degenerate grid configs are rejected, not silently coerced', () => {
  assert.throws(() => gridLevels({ lower: 0, upper: 200, rungs: 5 }), RangeError);
  assert.throws(() => gridLevels({ lower: 200, upper: 100, rungs: 5 }), RangeError);
  assert.throws(() => gridLevels({ lower: 100, upper: 200, rungs: 1 }), RangeError);
  assert.throws(() => gridLevels({ lower: 100, upper: 200, rungs: 2.5 }), RangeError);
  assert.throws(() => gridLevels({ lower: 100, upper: 200, rungs: 5, spacing: 'nope' }), RangeError);
});

// ------------------------------------------------------------- side selection

test('bids sit below the market, offers above, deadband stays empty', () => {
  assert.equal(sideForLevel({ level: 100, price: 150 }), SIDE.BUY);
  assert.equal(sideForLevel({ level: 200, price: 150 }), SIDE.SELL);
  // 25bps of 150 is 0.375, so 150.2 is inside the band.
  assert.equal(sideForLevel({ level: 150.2, price: 150 }), null);
  assert.equal(sideForLevel({ level: 150.5, price: 150 }), SIDE.SELL);
});

// ------------------------------------------------------------------ planning

const CONFIG = {
  gridId: 'g1',
  lower: 100,
  upper: 200,
  rungs: 5,
  spacing: SPACING.ARITH,
  notionalPerRungUsd: 25,
  direction: DIRECTION.NEUTRAL,
};

test('a fresh grid with no lots plans only the bids', () => {
  const { intents, skipped } = planGrid({ config: CONFIG, price: 150, openLots: [] });
  assert.deepEqual(
    intents.map((i) => [i.side, i.level]),
    [
      [SIDE.BUY, 100],
      [SIDE.BUY, 125],
    ],
  );
  assert.equal(skipped.find((s) => s.level === 150).reason, 'inside-deadband');
  assert.equal(skipped.find((s) => s.level === 175).reason, 'above-market-entry-not-taken');
});

test('an exit rests one rung ABOVE the lot it closes, never at the same level', () => {
  // A lot bought at rung 125 must be offered at 150, the next rung up.
  const { intents } = planGrid({
    config: CONFIG,
    price: 150,
    openLots: [{ baseQty: 0.2, priceUsd: 125 }],
  });
  const sells = intents.filter((i) => i.side === SIDE.SELL);
  assert.equal(sells.length, 1);
  assert.equal(sells[0].level, 150);
  assert.notEqual(sells[0].level, 125); // the bug this test exists for
  assert.equal(sells[0].entryPriceUsd, 125);
  near(sells[0].baseQty, 0.2);
});

test('a lot below the market is still offered one rung up, not at its own price', () => {
  // Price gapped below the entry — the case that produced a zero-spread offer.
  const { intents } = planGrid({
    config: CONFIG,
    price: 110,
    openLots: [{ baseQty: 0.2, priceUsd: 125 }],
  });
  const sells = intents.filter((i) => i.side === SIDE.SELL);
  assert.equal(sells[0].level, 150);
});

test('captured spread per round trip equals the rung width', () => {
  // The economic contract: gross on a round trip is notional x rung width.
  const geom = { ...CONFIG, spacing: SPACING.GEOM };
  const levels = gridLevels(geom);
  const entry = levels[1];
  const exit = pairedExitLevel({ levels, entryPrice: entry });

  assert.equal(exit, levels[2]);

  const gross = expectedRoundTripUsd({ config: geom, level: entry });
  const widthFrac = rungWidthBps(geom) / 10_000;
  near(gross, geom.notionalPerRungUsd * widthFrac, 1e-9);
  assert.ok(gross > 0, 'a round trip must capture a positive gross spread');
});

test('a lot at the top rung is extrapolated up, not sold flat', () => {
  const levels = gridLevels(CONFIG);
  const top = levels.at(-1);
  const exit = pairedExitLevel({ levels, entryPrice: top });
  assert.ok(exit > top, `exit ${exit} must exceed the top rung ${top}`);
});

test('nearest level snaps an off-grid entry price to its rung', () => {
  const levels = gridLevels(CONFIG); // [100,125,150,175,200]
  assert.equal(nearestLevelIndex(levels, 124.99), 1);
  assert.equal(nearestLevelIndex(levels, 126), 1);
  assert.equal(nearestLevelIndex(levels, 173), 3);
});

test('a level already holding a lot is not bid again', () => {
  const { intents, skipped } = planGrid({
    config: CONFIG,
    price: 150,
    openLots: [{ baseQty: 0.2, priceUsd: 125 }],
  });
  const buys = intents.filter((i) => i.side === SIDE.BUY);
  assert.deepEqual(
    buys.map((b) => b.level),
    [100],
  );
  assert.equal(skipped.find((s) => s.level === 125).reason, 'lot-already-held-at-level');
});

test('an exit too small for the venue minimum is refused', () => {
  const { intents, skipped } = planGrid({
    config: CONFIG,
    price: 150,
    openLots: [{ baseQty: 0.001, priceUsd: 125 }], // 0.001 * 150 = $0.15
  });
  assert.equal(intents.filter((i) => i.side === SIDE.SELL).length, 0);
  assert.ok(skipped.some((s) => s.reason === 'below-venue-minimum-10usd'));
});

test('an already-resting rung is not re-planned', () => {
  const key = intentKey({ gridId: 'g1', side: SIDE.BUY, level: 100 });
  const { intents, skipped } = planGrid({
    config: CONFIG,
    price: 150,
    openIntentKeys: [key],
    openLots: [],
  });
  assert.deepEqual(
    intents.map((i) => i.level),
    [125],
  );
  assert.equal(skipped.find((s) => s.level === 100).reason, 'already-resting');
});

test('intent keys are stable across recomputation and distinct per side', () => {
  const a = intentKey({ gridId: 'g1', side: SIDE.BUY, level: 141.42135623 });
  const b = intentKey({ gridId: 'g1', side: SIDE.BUY, level: 141.42135623 });
  const c = intentKey({ gridId: 'g1', side: SIDE.SELL, level: 141.42135623 });
  assert.equal(a, b);
  assert.notEqual(a, c);
});

test('rungs under the venue minimum are refused with a named reason', () => {
  const { intents, skipped } = planGrid({
    config: { ...CONFIG, notionalPerRungUsd: 5 },
    price: 150,
    inventoryBase: 10,
  });
  assert.equal(intents.length, 0);
  assert.ok(skipped.every((s) => s.reason !== 'ok'));
  assert.ok(skipped.some((s) => s.reason === 'below-venue-minimum-10usd'));
});

test('capital requirement is the bids only — exits are self-funding', () => {
  const req = capitalRequirement({ config: CONFIG, price: 150 });
  assert.equal(req.quoteUsd, 50); // two bids at $25
  // Base acquired if both bids fill, which then backs their paired exits.
  near(req.baseQty, 25 / 100 + 25 / 125);
  near(req.totalUsd, 50); // no base balance needed to start
});

// --------------------------------------------------------------- reconcile --

const RECON_CONFIG = { ...CONFIG, gridId: 'g1' };

/** Journal an intent the way the engine does before submitting. */
async function seedResting(store, { side, level, venueOrderId }) {
  const key = intentKey({ gridId: RECON_CONFIG.gridId, side, level });
  await store.putIntent({
    intentKey: key,
    gridId: RECON_CONFIG.gridId,
    side,
    level,
    notionalUsd: 25,
    status: INTENT_STATUS.SUBMITTING,
    venueOrderId,
  });
  return key;
}

test('price matching tolerates the venue echoing fewer decimals', () => {
  // 1bp tolerance: 69.238424 and 69.2384 are the same order.
  assert.ok(pricesMatch(69.238424, 69.2384));
  assert.ok(pricesMatch(141.42135623, 141.4214));
  // A whole rung apart is NOT a match.
  assert.equal(pricesMatch(125, 150), false);
  assert.equal(pricesMatch(69.24, 69.3), false);
});

test('a resting order echoed with fewer decimals is matched, not duplicated', async () => {
  // This is the live-mode path: normaliseOrders output carries NO intentKey,
  // and the venue rounds triggerPriceUsd. Exact key equality would fail here.
  const store = new MemoryStore();
  const level = 141.42135623;
  const key = await seedResting(store, { side: 'sell', level, venueOrderId: 'ord-1' });

  const venue = {
    async getOpenOrders() {
      // Shaped exactly like the real client's output: no intentKey, 4 decimals.
      return normaliseOrders([
        {
          id: 'ord-1',
          status: 'active',
          triggerCondition: 'above',
          triggerPriceUsd: '141.4214',
          inputMint: 'base',
          outputMint: 'quote',
        },
      ]);
    },
  };

  const rec = await reconcile({ venue, store, config: RECON_CONFIG });

  assert.deepEqual(rec.restingKeys, [key], 'the live order must map back to the seeded intent key');
  assert.deepEqual(rec.orphaned, [], 'a matched order must not be orphaned');
  assert.deepEqual(rec.adopted, [key]);

  const intent = await store.getIntent(key);
  assert.equal(intent.status, INTENT_STATUS.RESTING);
  // Exactly one journal entry: no duplicate was created for the same rung.
  assert.equal((await store.allIntents()).length, 1);
});

test('a submitted order missing from the venue is orphaned, never auto-retried', async () => {
  const store = new MemoryStore();
  const key = await seedResting(store, { side: 'buy', level: 125, venueOrderId: 'ord-2' });
  const venue = { async getOpenOrders() { return []; } };

  const rec = await reconcile({ venue, store, config: RECON_CONFIG });

  assert.deepEqual(rec.orphaned, [key]);
  assert.deepEqual(rec.restingKeys, []);
  assert.equal((await store.getIntent(key)).status, INTENT_STATUS.UNKNOWN);
});

test('an unknown live order is adopted so it occupies cap space', async () => {
  const store = new MemoryStore();
  const venue = {
    async getOpenOrders() {
      return normaliseOrders([
        { id: 'ord-3', status: 'active', triggerCondition: 'below', triggerPriceUsd: 100 },
      ]);
    },
  };

  const rec = await reconcile({ venue, store, config: RECON_CONFIG });

  assert.equal(rec.restingKeys.length, 1);
  const intents = await store.allIntents();
  assert.equal(intents.length, 1);
  assert.equal(intents[0].adoptedFromVenue, true);
  assert.equal(intents[0].side, 'buy'); // 'below' maps to a bid
});

test('matchIntent refuses to match across sides', () => {
  const journal = [{ intentKey: 'k', side: 'buy', level: 125 }];
  assert.equal(matchIntent({ order: { side: 'sell', triggerPriceUsd: 125 }, journal }), null);
  assert.ok(matchIntent({ order: { side: 'buy', triggerPriceUsd: 125 }, journal }));
});

test('two live orders a hair apart do not both bind to one intent', async () => {
  const store = new MemoryStore();
  await seedResting(store, { side: 'buy', level: 125, venueOrderId: 'ord-a' });

  const venue = {
    async getOpenOrders() {
      return normaliseOrders([
        { id: 'ord-a', status: 'active', triggerCondition: 'below', triggerPriceUsd: 125 },
        { id: 'ord-b', status: 'active', triggerCondition: 'below', triggerPriceUsd: 125.001 },
      ]);
    },
  };

  const rec = await reconcile({ venue, store, config: RECON_CONFIG });
  // Both live orders must be accounted for; neither may silently disappear.
  assert.equal(rec.restingKeys.length, 2, 'both live orders must occupy cap space');
});

// ------------------------------------------------------- lot aggregation ---

test('two lots on one rung produce a single exit order, not a duplicate key', () => {
  const { intents } = planGrid({
    config: CONFIG,
    price: 150,
    openLots: [
      { baseQty: 0.1, priceUsd: 125 },
      { baseQty: 0.15, priceUsd: 125 }, // same rung: a partial fill or a refill
    ],
  });
  const sells = intents.filter((i) => i.side === SIDE.SELL);
  assert.equal(sells.length, 1, 'one order per exit level, or the rung is submitted twice');
  near(sells[0].baseQty, 0.25, 1e-12); // combined
  assert.equal(sells[0].lotCount, 2);

  // No duplicate intentKey anywhere in the batch.
  const keys = intents.map((i) => i.intentKey);
  assert.equal(new Set(keys).size, keys.length);
});

test('lots on different rungs still get their own exits', () => {
  const { intents } = planGrid({
    config: CONFIG,
    price: 150,
    openLots: [
      { baseQty: 0.1, priceUsd: 100 },
      { baseQty: 0.1, priceUsd: 125 },
    ],
  });
  const sells = intents.filter((i) => i.side === SIDE.SELL).map((s) => s.level).sort((a, b) => a - b);
  assert.deepEqual(sells, [125, 150]);
});

// --------------------------------------------------- rails fail closed ----

test('a missing state field does not disable its rail', () => {
  // realizedPnlUsdToday absent: `undefined <= -50` is false, so a naive
  // implementation silently stops enforcing the daily loss limit.
  const s = normaliseState({ openNotionalUsd: 0, openOrderCount: 0 });
  assert.equal(s.realizedPnlUsdToday, 0);
  assert.equal(s.leverage, 1);
  assert.ok(s.problems.some((p) => p.includes('realizedPnlUsdToday')));
});

test('a NaN state field is neutralised and reported, not trusted', () => {
  const s = normaliseState({ openNotionalUsd: NaN, openOrderCount: 3 });
  assert.equal(s.openNotionalUsd, 0);
  assert.ok(s.problems.some((p) => p.includes('openNotionalUsd')));
});

test('an order with unusable numbers is blocked outright', () => {
  for (const order of [
    { notionalUsd: NaN, slippageBps: 100 },
    { notionalUsd: 25, slippageBps: undefined },
    {},
  ]) {
    const r = evaluate({ order, state: STATE });
    assert.equal(r.verdict, VERDICT.BLOCK);
    assert.ok(r.blockedBy.includes('unusable-order'));
  }
});

test('rails still fire normally through the normalised path', () => {
  const r = evaluate({
    order: { notionalUsd: 25, slippageBps: 100 },
    state: { realizedPnlUsdToday: -60 }, // every other field missing
    limits: { dailyLossLimitUsd: 50 },
  });
  assert.equal(r.verdict, VERDICT.BLOCK);
  assert.ok(r.blockedBy.includes('daily-loss-limit'));
});

// ------------------------------------------------------------ tick guards --

/** Minimal venue stub: fixed price, no orders, no fills. */
const stubVenue = (price) => ({
  kind: 'spot',
  async getPrice() {
    return price;
  },
  async getOpenOrders() {
    return [];
  },
  async getFills() {
    return [];
  },
  async getCarryCosts() {
    return [];
  },
  async placeOrder({ intent }) {
    return { venueOrderId: `v-${intent.intentKey}`, simulated: true };
  },
});

test('an unusable venue price aborts the tick instead of poisoning P&L', async () => {
  for (const bad of [NaN, 0, -5, Infinity]) {
    const store = new MemoryStore();
    const configStore = new ConfigStore(null);
    await configStore.setRuntime({ armed: true });
    const result = await tick({ venue: stubVenue(bad), store, configStore });

    assert.ok(
      result.errors.some((e) => /unusable price/.test(e.error)),
      `price ${bad} should abort the tick`,
    );
    assert.equal(result.pnl, null, 'no P&L may be computed from an unusable price');
    // Runtime must not have recorded a NaN daily figure.
    const runtime = await configStore.getRuntime();
    assert.ok(
      runtime.realizedPnlUsdToday === 0 || Number.isFinite(runtime.realizedPnlUsdToday),
      'daily P&L must stay finite',
    );
  }
});

test("the daily loss counter measures TODAY, not lifetime realized P&L", async () => {
  const store = new MemoryStore();
  const configStore = new ConfigStore(null);
  await configStore.setConfig({ lower: 85, upper: 115, rungs: 5, notionalPerRungUsd: 12 });
  await configStore.setRuntime({ armed: true });

  // A closed round trip well in the past: lifetime realized is -$20.
  await store.putFill({ id: 'f1', gridId: 'grid-1', side: 'buy', baseQty: 1, priceUsd: 100, feeUsd: 0, tsMs: 1 });
  await store.putFill({ id: 'f2', gridId: 'grid-1', side: 'sell', baseQty: 1, priceUsd: 80, feeUsd: 0, tsMs: 2 });

  const result = await tick({ venue: stubVenue(100), store, configStore });

  assert.ok(result.pnl.realizedNetUsd < -19, 'lifetime realized should be about -$20');
  // First tick of a new day: today's figure is 0, because the baseline is set
  // to whatever lifetime realized already was.
  near(result.realizedPnlUsdToday, 0, 1e-9);

  const runtime = await configStore.getRuntime();
  near(runtime.dayStartRealizedUsd, result.pnl.realizedNetUsd, 1e-9);
});

test('a short grid on a spot venue says so instead of sitting idle', async () => {
  const store = new MemoryStore();
  const configStore = new ConfigStore(null);
  await configStore.setConfig({ direction: 'short' });
  await configStore.setRuntime({ armed: true });

  const result = await tick({ venue: stubVenue(100), store, configStore });
  assert.ok(result.errors.some((e) => /cannot be expressed on a spot venue/.test(e.error)));
  assert.equal(result.placed.length, 0);
});

// ---------------------------------------------------------------- risk rails

const STATE = {
  openNotionalUsd: 0,
  openOrderCount: 0,
  realizedPnlUsdToday: 0,
  leverage: 1,
  liquidationDistancePct: null,
};

test('a clean order passes every rail', () => {
  const r = evaluate({ order: { notionalUsd: 25, slippageBps: 100 }, state: STATE });
  assert.equal(r.verdict, VERDICT.ALLOW);
  assert.deepEqual(r.blockedBy, []);
});

test('the kill switch blocks unconditionally', () => {
  const r = evaluate({
    order: { notionalUsd: 1, slippageBps: 1 },
    state: STATE,
    limits: { killSwitch: true },
  });
  assert.equal(r.verdict, VERDICT.BLOCK);
  assert.ok(r.blockedBy.includes('kill-switch'));
});

test('each rail fires on its own breach and names itself', () => {
  const cases = [
    ['slippage-bound', { notionalUsd: 25, slippageBps: 5000 }, STATE, {}],
    ['per-order-notional', { notionalUsd: 5000, slippageBps: 100 }, STATE, {}],
    [
      'total-notional',
      { notionalUsd: 100, slippageBps: 100 },
      { ...STATE, openNotionalUsd: 480 },
      {},
    ],
    ['concurrent-orders', { notionalUsd: 25, slippageBps: 100 }, { ...STATE, openOrderCount: 12 }, {}],
    ['leverage-cap', { notionalUsd: 25, slippageBps: 100 }, { ...STATE, leverage: 3 }, {}],
    [
      'daily-loss-limit',
      { notionalUsd: 25, slippageBps: 100 },
      { ...STATE, realizedPnlUsdToday: -50 },
      {},
    ],
    [
      'liquidation-distance',
      { notionalUsd: 25, slippageBps: 100 },
      { ...STATE, liquidationDistancePct: 5 },
      {},
    ],
  ];
  for (const [railId, order, state, limits] of cases) {
    const r = evaluate({ order, state, limits });
    assert.equal(r.verdict, VERDICT.BLOCK, `${railId} should block`);
    assert.ok(r.blockedBy.includes(railId), `expected ${railId} in ${r.blockedBy}`);
    assert.ok(r.reasons.length > 0);
  }
});

test('liquidation distance is ignored when the venue does not report one', () => {
  const r = evaluate({
    order: { notionalUsd: 25, slippageBps: 100 },
    state: { ...STATE, liquidationDistancePct: null },
    limits: { minLiquidationDistancePct: 99 },
  });
  assert.equal(r.verdict, VERDICT.ALLOW);
});

test('a batch cannot collectively breach a cap its members each pass', () => {
  // Six $100 orders each pass the per-order cap but the total cap is $500.
  const intents = Array.from({ length: 6 }, (_, i) => ({
    intentKey: `k${i}`,
    notionalUsd: 100,
  }));
  const { admitted, rejected } = admitBatch({
    intents,
    state: STATE,
    slippageBps: 100,
    limits: { maxOrdersPerTick: 10 },
  });
  assert.equal(admitted.length, 5);
  assert.equal(rejected.length, 1);
  assert.ok(rejected[0].blockedBy.includes('total-notional'));
});

test('the per-tick budget caps a cold start', () => {
  const intents = Array.from({ length: 10 }, (_, i) => ({ intentKey: `k${i}`, notionalUsd: 10 }));
  const { admitted, rejected } = admitBatch({ intents, state: STATE, slippageBps: 100 });
  assert.equal(admitted.length, DEFAULT_LIMITS.maxOrdersPerTick);
  assert.ok(rejected.every((r) => r.blockedBy.includes('tick-budget')));
});

test('dayKey rolls on UTC date', () => {
  assert.equal(dayKey(Date.UTC(2026, 7, 3, 23, 59)), '2026-08-03');
  assert.equal(dayKey(Date.UTC(2026, 7, 4, 0, 1)), '2026-08-04');
});

// ----------------------------------------------------------------- P&L math

const fill = (o) => ({ id: o.id, gridId: 'g1', feeUsd: 0, ...o });

test('one round trip nets gross minus both fees (hand-computed)', () => {
  // buy 1 @ 100 fee 0.50, sell 1 @ 110 fee 0.55
  // gross 10.00, fees 1.05, net 8.95
  const fills = [
    fill({ id: 'a', side: 'buy', baseQty: 1, priceUsd: 100, feeUsd: 0.5, tsMs: 1 }),
    fill({ id: 'b', side: 'sell', baseQty: 1, priceUsd: 110, feeUsd: 0.55, tsMs: 2 }),
  ];
  const m = matchFifo(fills);
  assert.equal(m.roundTrips.length, 1);
  near(m.realizedGrossUsd, 10);
  near(m.realizedFeeUsd, 1.05);
  near(m.realizedNetUsd, 8.95);
  assert.equal(m.openLots.length, 0);
});

test('carry cost is subtracted from realized P&L, never assumed', () => {
  const fills = [
    fill({ id: 'a', side: 'buy', baseQty: 1, priceUsd: 100, feeUsd: 0.5, tsMs: 1 }),
    fill({ id: 'b', side: 'sell', baseQty: 1, priceUsd: 110, feeUsd: 0.55, tsMs: 2 }),
  ];
  const s = snapshot({
    fills,
    markPriceUsd: 110,
    carryEntries: [{ tsMs: 2, costUsd: 2 }],
  });
  near(s.realizedNetUsd, 6.95); // 8.95 - 2.00 carry
  near(s.carryUsd, 2);
  near(s.feeTotalUsd, 1.05 + 2);
});

test('a partial close realizes only its share of the entry fee', () => {
  // buy 2 @ 100 fee 1.00; sell 1 @ 110 fee 0.50
  // entry fee share 0.50, exit fee 0.50, gross 10 -> net 9.00
  // remaining lot: 1 @ 100 carrying 0.50 of unrealized fee
  const fills = [
    fill({ id: 'a', side: 'buy', baseQty: 2, priceUsd: 100, feeUsd: 1, tsMs: 1 }),
    fill({ id: 'b', side: 'sell', baseQty: 1, priceUsd: 110, feeUsd: 0.5, tsMs: 2 }),
  ];
  const s = snapshot({ fills, markPriceUsd: 120 });
  near(s.realizedNetUsd, 9);
  near(s.openBaseQty, 1);
  near(s.avgEntryUsd, 100);
  near(s.unrealizedNetUsd, 120 - 100 - 0.5); // 19.50
  near(s.totalNetUsd, 9 + 19.5);
});

test('FIFO consumes the oldest lot first', () => {
  const fills = [
    fill({ id: 'a', side: 'buy', baseQty: 1, priceUsd: 100, tsMs: 1 }),
    fill({ id: 'b', side: 'buy', baseQty: 1, priceUsd: 120, tsMs: 2 }),
    fill({ id: 'c', side: 'sell', baseQty: 1, priceUsd: 130, tsMs: 3 }),
  ];
  const m = matchFifo(fills);
  near(m.roundTrips[0].entryUsd, 100); // the $100 lot, not the $120 one
  near(m.realizedNetUsd, 30);
  near(m.openLots[0].priceUsd, 120);
});

test('a sell with no lot behind it is surfaced, not swallowed', () => {
  const m = matchFifo([fill({ id: 'a', side: 'sell', baseQty: 2, priceUsd: 100, tsMs: 1 })]);
  assert.equal(m.roundTrips.length, 0);
  near(m.unmatchedSellQty, 2);
});

test('fills are matched in timestamp order regardless of input order', () => {
  const late = fill({ id: 'z', side: 'sell', baseQty: 1, priceUsd: 130, tsMs: 3 });
  const early = fill({ id: 'a', side: 'buy', baseQty: 1, priceUsd: 100, tsMs: 1 });
  const m = matchFifo([late, early]);
  assert.equal(m.roundTrips.length, 1);
  near(m.realizedNetUsd, 30);
});

test('win rate counts net-positive round trips only', () => {
  const fills = [
    fill({ id: 'a', side: 'buy', baseQty: 1, priceUsd: 100, tsMs: 1 }),
    fill({ id: 'b', side: 'sell', baseQty: 1, priceUsd: 110, tsMs: 2 }),
    fill({ id: 'c', side: 'buy', baseQty: 1, priceUsd: 100, tsMs: 3 }),
    fill({ id: 'd', side: 'sell', baseQty: 1, priceUsd: 90, tsMs: 4 }),
  ];
  assert.equal(snapshot({ fills, markPriceUsd: 90 }).winRate, 0.5);
});

test('a fee larger than the move turns a gross win into a net loss', () => {
  const fills = [
    fill({ id: 'a', side: 'buy', baseQty: 1, priceUsd: 100, feeUsd: 3, tsMs: 1 }),
    fill({ id: 'b', side: 'sell', baseQty: 1, priceUsd: 102, feeUsd: 3, tsMs: 2 }),
  ];
  const s = snapshot({ fills, markPriceUsd: 102 });
  near(s.realizedGrossUsd, 2);
  near(s.realizedNetUsd, -4);
  assert.equal(s.winRate, 0);
});

test('drawdown is measured peak to trough', () => {
  const points = [
    { tsMs: 1, equityUsd: 100 },
    { tsMs: 2, equityUsd: 130 },
    { tsMs: 3, equityUsd: 90 },
    { tsMs: 4, equityUsd: 120 },
  ];
  const dd = maxDrawdown(points);
  near(dd.drawdownUsd, 40);
  near(dd.drawdownPct, (40 / 130) * 100);
});

test('equity curve folds carry costs in at their own timestamps', () => {
  const roundTrips = [{ closeTsMs: 10, netUsd: 5 }];
  const points = equityCurve({
    roundTrips,
    carryEntries: [{ tsMs: 20, costUsd: 2 }],
    startEquityUsd: 100,
  });
  assert.equal(points.at(-1).equityUsd, 103);
});

test('CSV export has a header and one row per fill', () => {
  const csv = fillsToCsv([
    fill({ id: 'a', side: 'buy', baseQty: 2, priceUsd: 100, feeUsd: 1, tsMs: 0, level: 100 }),
  ]);
  const lines = csv.split('\n');
  assert.equal(lines.length, 2);
  assert.ok(lines[0].startsWith('id,gridId,tsIso'));
  assert.ok(lines[1].includes('200.000000')); // notional
});
