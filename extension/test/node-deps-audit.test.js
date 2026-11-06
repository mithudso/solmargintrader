import test from 'node:test';
import assert from 'node:assert/strict';
import { createNodeDeps } from '../tools/deps.js';
import { runCommand } from '../src/core/commands.js';

test('fresh per-tick configuration does not discard the process dry-run order book', async () => {
  const deps = await createNodeDeps({ ephemeral: true, quiet: true });
  await deps.configStore.setConfig({ lower: 100, upper: 200, rungs: 5, spacing: 'arith' });
  const config = await deps.configStore.getConfig();
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    [config.baseMint]: { usdPrice: 150, decimals: 9 },
    [config.quoteMint]: { usdPrice: 1, decimals: 6 },
  }));
  try {
    await runCommand({ name: 'arm', args: {}, deps });
    const { ticks } = await runCommand({ name: 'tick', args: { count: 3 }, deps });
    assert.equal(ticks[0].placed.length, 2);
    assert.ok(ticks.every((result) => result.unknownIntents.length === 0));
    assert.ok(ticks.every((result) => result.errors.length === 0));
  } finally {
    globalThis.fetch = oldFetch;
  }
});
