import test from 'node:test';
import assert from 'node:assert/strict';
import { ingestFills, tick } from '../src/core/engine.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';

test('fill timing must be known before historical execution enters daily P&L', async () => {
  for (const updatedAtMs of [undefined, null, NaN, Infinity, -1]) {
    const store = new MemoryStore();
    const venue = { getFills: async () => [{ venueOrderId: 'f', side: 'buy', executedPriceUsd: 100,
      filledBaseQty: 1, feeUsd: 0, updatedAtMs }] };
    const result = await ingestFills({ venue, store, config: { gridId: 'g' } });
    assert.equal(result.blocked, true, String(updatedAtMs));
    assert.equal((await store.allFills()).length, 0);
  }
});

test('unknown persisted costs or timestamps hold admission instead of disabling daily loss rail', async () => {
  for (const kind of ['fee', 'carry', 'legacy-time']) {
    const store = new MemoryStore();
    const configStore = new ConfigStore(null);
    await configStore.setConfig({ lower: 100, upper: 200, rungs: 5, spacing: 'arith' });
    await configStore.setRuntime({ armed: true });
    if (kind === 'carry') await store.putCarry({ id: 'c', costUsd: NaN, tsMs: 1 });
    else await store.putFill({ id: 'f', side: 'buy', baseQty: 0.1, priceUsd: 100, feeUsd: 0,
      feeUnknown: kind === 'fee', tsMs: kind === 'legacy-time' ? undefined : 1 });
    let placed = 0;
    const venue = { kind: 'spot', getPrice: async () => 150, getFills: async () => [], getOpenOrders: async () => [],
      placeOrder: async () => { placed++; return { venueOrderId: 'new' }; } };
    const result = await tick({ store, configStore, venue });
    assert.equal(placed, 0, kind);
    assert.ok(result.skipped.some((row) => row.reason === 'accounting-evidence-needs-review'), kind);
  }
});
