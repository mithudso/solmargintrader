import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MIN_PASSPHRASE_LENGTH,
  validateSessionKeyInputs,
  buildCreateSessionKeyMessage,
  describeCreateResult,
} from '../src/ui/session-key-form.js';
import { COMMANDS } from '../src/core/commands.js';

const good = { passphrase: 'correct horse battery', confirmPassphrase: 'correct horse battery', acknowledged: true };

test('valid inputs pass', () => {
  assert.equal(validateSessionKeyInputs(good), null);
});

test('a mistyped confirmation is refused', () => {
  const err = validateSessionKeyInputs({ ...good, confirmPassphrase: 'correct horse batterz' });
  assert.match(err, /do not match/);
  assert.ok(!err.includes(good.passphrase), 'errors must not echo the passphrase');
});

test('the acknowledgement is required', () => {
  assert.match(validateSessionKeyInputs({ ...good, acknowledged: false }), /replaces any existing/);
});

test('the client minimum equals the command minimum', async () => {
  const short = 'x'.repeat(MIN_PASSPHRASE_LENGTH - 1);
  const ok = 'x'.repeat(MIN_PASSPHRASE_LENGTH);
  assert.ok(validateSessionKeyInputs({ passphrase: short, confirmPassphrase: short, acknowledged: true }));
  assert.equal(validateSessionKeyInputs({ passphrase: ok, confirmPassphrase: ok, acknowledged: true }), null);
  // The command refuses the short one before touching deps.
  await assert.rejects(COMMANDS.createSessionKey.handler({ deps: {}, args: { passphrase: short } }), /at least 12/);
});

test('the message is exactly the registered command', () => {
  const msg = buildCreateSessionKeyMessage('pw');
  assert.deepEqual(msg, { type: 'createSessionKey', passphrase: 'pw' });
  assert.ok(COMMANDS[msg.type]);
});

test('the result text shows the public key and never the vault', () => {
  const r = describeCreateResult({ ok: true, pubkeyBs58: 'PUBKEY', vault: { ct: 'SECRETISH' } });
  assert.equal(r.ok, true);
  assert.match(r.text, /PUBKEY/);
  assert.ok(!r.text.includes('SECRETISH'));
  assert.equal(describeCreateResult({ ok: false, error: 'boom' }).ok, false);
  assert.equal(describeCreateResult(undefined).ok, false);
});
