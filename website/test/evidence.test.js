import test from 'node:test';
import assert from 'node:assert/strict';
import { freshStrategy } from '../public/evidence.js';

test('oracle leader disappears at its exact expiry, including offline cached responses', () => {
  const topStrategy = { id: 'rsi', direction: 'up', expiresAt: 120 };
  assert.equal(freshStrategy({ status: 'available', topStrategy }, 119), topStrategy);
  assert.equal(freshStrategy({ status: 'available', topStrategy }, 120), null);
  assert.equal(freshStrategy({ status: 'unavailable', topStrategy }, 119), null);
  for (const expiresAt of [undefined, null, '120', NaN, Infinity]) assert.equal(freshStrategy({ status: 'available', topStrategy: { ...topStrategy, expiresAt } }, 119), null);
});
