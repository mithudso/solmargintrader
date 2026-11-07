// The browser e2e (tools/e2e.mjs) cannot run under `node --test`: it needs Chrome for
// Testing. What can be tested without a browser is the part that makes it safe.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { COMMAND_NAMES } from '../src/core/commands.js';
import {
  ALLOWED_MESSAGES,
  FORBIDDEN_MESSAGES,
  assertAllowedMessage,
  assertDisarmed,
  assertSoltuiCallAllowed,
} from '../e2e/lib/guard.mjs';
import { parseFrames } from '../e2e/lib/cdp.mjs';

test('e2e allowlist and forbidden list name only real registry commands, with no overlap', () => {
  for (const name of [...ALLOWED_MESSAGES, ...FORBIDDEN_MESSAGES]) {
    assert.ok(COMMAND_NAMES.includes(name), `${name} is not a registry command`);
  }
  assert.deepEqual(ALLOWED_MESSAGES.filter((n) => FORBIDDEN_MESSAGES.includes(n)), []);
});

test('e2e harness refuses every command that could arm, sign, reconfigure or cancel', () => {
  for (const name of FORBIDDEN_MESSAGES) assert.throws(() => assertAllowedMessage(name), /refuses to send/);
  assert.throws(() => assertAllowedMessage('arm'), /refuses to send/);
  assert.throws(() => assertAllowedMessage(undefined), /refuses to send/);
});

test('every registry command is either allowed or forbidden to the e2e harness, so a new command needs a decision', () => {
  const classified = new Set([...ALLOWED_MESSAGES, ...FORBIDDEN_MESSAGES]);
  const unclassified = COMMAND_NAMES.filter((n) => !classified.has(n));
  assert.deepEqual(unclassified, [], 'classify new commands in e2e/lib/guard.mjs');
});

test('assertDisarmed fails closed on anything but an explicit armed:false', () => {
  assertDisarmed({ armed: false }, 'here');
  for (const bad of [{ armed: true }, {}, null, undefined, { armed: 'false' }]) {
    assert.throws(() => assertDisarmed(bad, 'here'), /armed/);
  }
});

test('parseFrames splits NUL-delimited JSON, keeps a partial tail and counts bad frames', () => {
  const a = parseFrames('{"id":1}\0{"id":2}\0{"id":');
  assert.deepEqual(a.frames, [{ id: 1 }, { id: 2 }]);
  assert.equal(a.rest, '{"id":');
  assert.equal(a.malformed, 0);

  const b = parseFrames(`${a.rest}3}\0not json\0{"id":4}\0`);
  assert.deepEqual(b.frames, [{ id: 3 }, { id: 4 }]);
  assert.equal(b.rest, '');
  assert.equal(b.malformed, 1);
});

test('the harness may call a soltui command only if soltui lists it read-only and without confirm', () => {
  const listing = [
    { name: 'a.read', read_only: true, requires_confirm: false },
    { name: 'b.write', read_only: false, requires_confirm: false },
    { name: 'c.resume', read_only: true, requires_confirm: true },
  ];
  assert.equal(assertSoltuiCallAllowed('a.read', {}, listing).name, 'a.read');
  assert.throws(() => assertSoltuiCallAllowed('b.write', {}, listing), /not a read-only/);
  assert.throws(() => assertSoltuiCallAllowed('c.resume', {}, listing), /not a read-only/);
  assert.throws(() => assertSoltuiCallAllowed('d.unlisted', {}, listing), /does not list/);
  assert.throws(() => assertSoltuiCallAllowed('a.read', { confirm: true }, listing), /never sends confirm/);
  assert.throws(() => assertSoltuiCallAllowed('a.read', {}, undefined), /does not list/);
});
