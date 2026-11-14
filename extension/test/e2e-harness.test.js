// The browser e2e (tools/e2e.mjs) cannot run under `node --test`: it needs Chrome for
// Testing. What can be tested without a browser is the part that makes it safe.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { COMMAND_NAMES } from '../src/core/commands.js';
import {
  ALLOWED_MESSAGES,
  FORBIDDEN_MESSAGES,
  assertAllowedMessage,
  assertDisarmed,
  assertSoltuiCallAllowed,
} from '../e2e/lib/guard.mjs';
import { launch, parseFrames } from '../e2e/lib/cdp.mjs';
import { installHost } from '../e2e/lib/soltui-host.mjs';

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

test('a failed final CDP startup query closes its child and removes its temporary profile', async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'smt-cdp-startup-'));
  const marker = path.join(directory, 'started.json');
  const program = path.join(directory, 'chrome.mjs');
  const chrome = path.join(directory, 'chrome.sh');
  const quote = (value) => `'${String(value).replace(/'/g, `'\\''`)}'`;
  const alive = (pid) => {
    try { process.kill(pid, 0); return true; } catch (error) {
      if (error.code === 'ESRCH') return false;
      throw error;
    }
  };
  t.after(() => {
    if (fs.existsSync(marker)) {
      const { pid, profile } = JSON.parse(fs.readFileSync(marker, 'utf8'));
      if (alive(pid)) process.kill(pid, 'SIGKILL');
      fs.rmSync(profile, { recursive: true, force: true });
    }
    fs.rmSync(directory, { recursive: true, force: true });
  });
  // This child implements only the startup pipe protocol. It never runs Chrome,
  // reads accounts, opens sockets, or executes extension code.
  fs.writeFileSync(program, `import fs from 'node:fs';
    const profile = process.argv.find(arg => arg.startsWith('--user-data-dir=')).slice(16);
    fs.writeFileSync(${JSON.stringify(marker)}, JSON.stringify({pid:process.pid,profile}));
    let buffer = '', versionCalls = 0;
    const input = fs.createReadStream(null, {fd:3,autoClose:false});
    input.setEncoding('utf8');
    input.on('data', chunk => {
      buffer += chunk;
      for (let end = buffer.indexOf('\\0'); end >= 0; end = buffer.indexOf('\\0')) {
        const request = JSON.parse(buffer.slice(0,end)); buffer = buffer.slice(end+1);
        const reply = request.method === 'Extensions.loadUnpacked'
          ? {id:request.id,result:{id:'synthetic-extension'}}
          : ++versionCalls === 1
            ? {id:request.id,result:{product:'Synthetic/1'}}
            : {id:request.id,error:{message:'synthetic final version failure'}};
        fs.writeSync(4, JSON.stringify(reply)+'\\0');
      }
    });\n`);
  fs.writeFileSync(chrome, `#!/bin/sh\nexec ${quote(process.execPath)} ${quote(program)} "$@"\n`, { mode: 0o700 });

  await assert.rejects(launch({ chrome, extension: directory }), /synthetic final version failure/);
  const { pid, profile } = JSON.parse(fs.readFileSync(marker, 'utf8'));
  assert.equal(alive(pid), false, 'startup rejection must wait for the child to exit');
  assert.equal(fs.existsSync(profile), false, 'startup rejection must remove its profile');
});

test('forcing a real host refuses before installation when the isolated repository has no host', async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'smt-real-host-missing-'));
  const previous = process.env.SOLTUI_REPO;
  process.env.SOLTUI_REPO = directory;
  t.after(() => {
    if (previous === undefined) delete process.env.SOLTUI_REPO;
    else process.env.SOLTUI_REPO = previous;
    fs.rmSync(directory, { recursive: true, force: true });
  });
  const profile = path.join(directory, 'profile');
  await assert.rejects(
    installHost({ profile, extensionId: 'synthetic-extension', mode: 'real' }),
    /native host did not answer a ping/,
  );
  assert.equal(fs.existsSync(profile), false, 'failed preflight must not write a host installation');
});
