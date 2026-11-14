import test from 'node:test';
import assert from 'node:assert/strict';
import { validPolicyScope, tradeWithinPolicyScope } from '../src/policy-scope.js';

const legacy = () => ({ venues: ['coinbase', 'jupiter'], assets: ['SOL'], maxTradeUsd: 100, maxTotalUsd: 500, expiresAt: 2_000_000_000 });
const v2 = changes => ({ version: 2, ...legacy(), products: ['spot', 'perpetual'], maxLeverage: 3, ...changes });
const spot = { venue: 'jupiter', asset: 'SOL', product: 'spot', leverage: 1 };
const perp = { ...spot, product: 'perpetual', leverage: 3 };

test('legacy five-field scope grants spot at one times only, including normalized defaults', () => {
  assert.equal(validPolicyScope(legacy()), true);
  assert.equal(tradeWithinPolicyScope(legacy(), spot), true);
  assert.equal(tradeWithinPolicyScope(legacy(), { venue: 'coinbase', asset: 'SOL' }), true);
  for (const changed of [{ product: 'perpetual', leverage: 1 }, { product: 'perpetual', leverage: 5 }, { leverage: 2 }, { product: null }, { leverage: null }]) {
    assert.equal(tradeWithinPolicyScope(legacy(), { ...spot, ...changed }), false, JSON.stringify(changed));
  }
  assert.equal(validPolicyScope({ ...legacy(), version: 1 }), false);
  assert.equal(validPolicyScope({ ...legacy(), products: ['perpetual'] }), false);
});

test('version two requires explicit product membership and bounds position leverage', () => {
  assert.equal(validPolicyScope(v2()), true);
  assert.equal(tradeWithinPolicyScope(v2(), perp), true);
  assert.equal(tradeWithinPolicyScope(v2(), { ...perp, leverage: 1 }), true);
  assert.equal(tradeWithinPolicyScope(v2(), { ...perp, leverage: 4 }), false);
  assert.equal(tradeWithinPolicyScope(v2({ products: ['spot'], maxLeverage: 5 }), perp), false);
  assert.equal(tradeWithinPolicyScope(v2({ products: ['perpetual'] }), spot), false);
  assert.equal(tradeWithinPolicyScope(v2(), { ...spot, leverage: 2 }), false);
  assert.equal(tradeWithinPolicyScope(v2(), { ...perp, asset: 'BTC' }), false);
  assert.equal(tradeWithinPolicyScope(v2({ venues: ['coinbase'] }), perp), false);
});

test('unknown fields, versions, duplicate collections and malformed leverage fail closed', () => {
  for (const changed of [
    { version: 1 }, { version: 3 }, { version: '2' }, { version: null },
    { products: [] }, { products: ['spot', 'spot'] }, { products: ['futures'] }, { products: 'spot' },
    { venues: [] }, { venues: ['jupiter', 'jupiter'] }, { venues: ['unknown'] },
    { assets: ['SOL', 'SOL'] }, { assets: ['unknown'] }, { signer: 'another-wallet' },
    ...[0, 6, -1, 1.5, '3', true, null, NaN].map(maxLeverage => ({ maxLeverage })),
  ]) assert.equal(validPolicyScope(v2(changed)), false, JSON.stringify(changed));
  const missing = v2(); delete missing.maxLeverage; assert.equal(validPolicyScope(missing), false);
  for (const leverage of [null, NaN, 1.5, '3', true, 0, 6]) assert.equal(tradeWithinPolicyScope(v2(), { ...perp, leverage }), false);
  assert.equal(tradeWithinPolicyScope(v2(), { ...perp, product: 'unknown' }), false);
});
