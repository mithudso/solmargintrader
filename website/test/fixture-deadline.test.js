import assert from 'node:assert/strict';
import test from 'node:test';
import { waitForFixture } from './helpers/deadline.mjs';

test('fixture request waits fail with an actionable deadline and clear successful timers', async () => {
  await assert.rejects(waitForFixture(new Promise(() => {}), 'GET /fixture', 5), /fixture request timed out: GET \/fixture/);
  assert.equal(await waitForFixture(Promise.resolve('started'), 'successful request', 5), 'started');
});
