import test from 'node:test';
import assert from 'node:assert/strict';
import { readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';

import { DryRunVenue, buildVenue, MODE } from '../src/venues/index.js';
import * as venues from '../src/venues/index.js';
import { ingestFills } from '../src/core/engine.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { snapshot } from '../src/core/pnl.js';

const inner = { id: 'stub', kind: 'spot', capabilities: { canPlaceLive: false }, getCarryCosts: async () => [] };
const CONFIG = { gridId: 'g' };

const buyIntent = { intentKey: 'g:buy:100', side: 'buy', level: 100, baseQty: 0.12 };
const sellIntent = { intentKey: 'g:sell:110', side: 'sell', level: 110, baseQty: 0.12 };

// ------------------------------------------------------------ TASK-387 -----

test('a simulated fill carries its quantity and a fee of notional * feeBps', async () => {
  const venue = new DryRunVenue({ inner, feeBps: 10 });
  await venue.placeOrder({ intent: buyIntent, slippageBps: 50 });
  const [fill] = venue.markPrice(99);

  // Buys pay up by the full slippage allowance, and the fee is charged on what
  // was actually paid, not on the trigger price.
  const executed = 100 * 1.005;
  assert.equal(fill.filledBaseQty, 0.12);
  assert.ok(Math.abs(fill.feeUsd - (0.12 * executed * 10) / 10_000) < 1e-12);
});

test('feeBps is honoured, including a deliberate zero', async () => {
  const zero = new DryRunVenue({ inner, feeBps: 0 });
  await zero.placeOrder({ intent: buyIntent, slippageBps: 0 });
  assert.equal(zero.markPrice(99)[0].feeUsd, 0, 'zero is a stated fee, not an unknown one');

  const wide = new DryRunVenue({ inner, feeBps: 100 });
  await wide.placeOrder({ intent: buyIntent, slippageBps: 0 });
  assert.ok(Math.abs(wide.markPrice(99)[0].feeUsd - 0.12) < 1e-12);
});

test('a fill with no usable quantity does not invent a fee', async () => {
  const venue = new DryRunVenue({ inner });
  await venue.placeOrder({ intent: { ...buyIntent, baseQty: undefined }, slippageBps: 0 });
  const [fill] = venue.markPrice(99);
  assert.equal(fill.feeUsd, undefined);
  assert.equal(fill.filledBaseQty, undefined);
});

test('ingested dry-run fills are not feeUnknown and realized P&L nets the fee', async () => {
  const venue = new DryRunVenue({ inner, feeBps: 10, clock: () => 1 });
  const store = new MemoryStore();

  await venue.placeOrder({ intent: buyIntent, slippageBps: 0 });
  venue.markPrice(100);
  await venue.placeOrder({ intent: sellIntent, slippageBps: 0 });
  venue.markPrice(110);

  const { added, feeUnknown } = await ingestFills({ venue, store, config: CONFIG });
  assert.equal(added.length, 2);
  assert.deepEqual(feeUnknown, []);
  assert.ok(added.every((f) => f.feeUnknown === false && f.feeUsd > 0));

  const snap = snapshot({ fills: await store.allFills(), markPriceUsd: 110 });
  const expectedFees = (0.12 * 100 * 10) / 10_000 + (0.12 * 110 * 10) / 10_000;
  const gross = 0.12 * (110 - 100);
  assert.ok(Math.abs(snap.realizedGrossUsd - gross) < 1e-9);
  assert.ok(Math.abs(snap.realizedFeeUsd - expectedFees) < 1e-9);
  assert.ok(Math.abs(snap.realizedNetUsd - (gross - expectedFees)) < 1e-9);
});

// ------------------------------------------------------------ TASK-402 -----

test('buildVenue offers only the wired venues and refuses unknown names', () => {
  for (const venue of ['kraken', 'jupiter_live', 'bogus']) {
    assert.throws(
      () => buildVenue({ config: { venue, mode: MODE.DRY_RUN } }),
      /unknown venue/,
      `${venue} must fail closed, not silently become the Trigger venue`,
    );
    assert.throws(() => buildVenue({ config: { venue, mode: MODE.FULL_AUTO } }), /unknown venue/);
  }
  assert.equal(buildVenue({ config: { venue: 'trigger', mode: MODE.DRY_RUN } }).kind, 'spot');
  assert.equal(buildVenue({ config: { mode: MODE.DRY_RUN } }).kind, 'spot', 'venue defaults to trigger');
  assert.equal(buildVenue({ config: { venue: 'perps', mode: MODE.DRY_RUN } }).kind, 'perps');
});

test('the unwired Kraken and Jupiter-live adapters are gone', async () => {
  assert.equal(venues.KrakenVenue, undefined);
  assert.equal(venues.JupiterLiveVenue, undefined);
  const here = dirname(fileURLToPath(import.meta.url));
  const files = await readdir(join(here, '..', 'src', 'venues'));
  assert.ok(!files.includes('krakenVenue.js'));
  assert.ok(!files.includes('jupiterLiveVenue.js'));
});
