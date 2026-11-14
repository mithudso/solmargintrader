import test from 'node:test';
import assert from 'node:assert/strict';
import { readBase, readSolana, readHoldings } from '../src/market/holdings.js';
import { BASE, SOLANA } from '../src/market/tokens.js';
const reply = value => new Response(JSON.stringify(value));
const owner = '11111111111111111111111111111111';
test('CDO-771a5f0380 missing Base balance is explicitly incomplete', async () => {
  const result = await readBase({ fetch: async (_url, init) => reply(JSON.parse(init.body).map(r =>
    r.id === 2 ? { id: r.id, error: { code: -1 } } : { id: r.id, result: r.method === 'eth_chainId' ? BASE.chainIdHex : '0x' + '0'.repeat(64) })) }, '0x' + '1'.repeat(40));
  assert.equal(result.usdComplete, false);
  assert.ok(result.errors.length > 0);
});
test('CDO-81bf59cb8a malformed Solana amounts cannot become complete zero balances', async () => {
  for (const bad of [{ uiAmountString: null, uiAmount: null, tokens: [] }, { uiAmountString: 'Infinity', tokens: {} },
    { uiAmountString: '0', tokens: { [SOLANA.wsol]: [{ uiAmountString: 'Infinity' }] } }]) {
    const result = await readSolana({ fetch: async (url, init) => {
      if (url.includes('/holdings/')) return reply(bad);
      if (!init.body) return reply({ [SOLANA.wsol]: { usdPrice: 100 } });
      return reply({ id: 1, result: JSON.parse(init.body).method === 'getBalance' ? { value: null } : { value: [] } });
    } }, owner);
    assert.equal(result.usdComplete, false);
    assert.ok(Number.isFinite(result.totalUsd));
  }
});
test('CDO-eec14113c2 aggregate preserves a healthy chain when the other fails', async () => {
  const result = await readHoldings({ fetch: async (url, init) => {
    if (url.includes('/holdings/')) return reply({ uiAmountString: '1', tokens: {} });
    if (!init.body) return reply({ [SOLANA.wsol]: { usdPrice: 100 } });
    const body = JSON.parse(init.body);
    assert.ok(Array.isArray(body));
    return reply(body.map(r => ({ id: r.id, result: r.method === 'eth_chainId' ? '0x1' : '0x0' })));
  } }, { baseAddress: '0x' + '1'.repeat(40), solanaAddress: owner });
  assert.equal(result.totalUsd, 100);
  assert.equal(result.complete, false);
  assert.ok(result.errors.length);
  assert.equal(result.chains.find(c => c.chain === 'solana').totalUsd, 100);
});
