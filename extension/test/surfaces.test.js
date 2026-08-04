import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { readFile, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { once } from 'node:events';

import { COMMANDS, COMMAND_NAMES, describeCommands, runCommand, CommandError } from '../src/core/commands.js';
import { createApiServer } from '../tools/api-server.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const CLI = join(ROOT, 'tools', 'cli.js');
const TOKEN = 'test-token-parity';

/**
 * The point of these tests: the extension, the CLI and the HTTP API must expose
 * the SAME set of actions. Three hand-maintained surfaces drift; a registry
 * plus this file does not.
 */

function run(args, opts = {}) {
  return new Promise((resolve) => {
    execFile(
      process.execPath,
      [CLI, ...args],
      { cwd: ROOT, timeout: 20_000, ...opts },
      (err, stdout, stderr) => resolve({ code: err?.code ?? 0, stdout, stderr }),
    );
  });
}

/** Deps with a stubbed venue: no network, no disk, no side effects. */
function testDeps() {
  const configStore = new ConfigStore(null);
  return {
    store: new MemoryStore(),
    configStore,
    async buildVenue() {
      return {
        id: 'stub',
        kind: 'spot',
        capabilities: { canPlaceLive: false, supportsLeverage: false },
        async getPrice() {
          return 100;
        },
        async getDecimals() {
          return { base: 9, quote: 6 };
        },
        async getOpenOrders() {
          return [];
        },
        async getFills() {
          return [];
        },
        async getCarryCosts() {
          return [];
        },
        async placeOrder({ intent }) {
          return { venueOrderId: `stub-${intent.intentKey}`, simulated: true };
        },
        async cancelOrder() {
          return { cancelled: true };
        },
      };
    },
    clock: () => 1_700_000_000_000,
    log: () => {},
  };
}

async function withServer(fn) {
  const server = createApiServer({ deps: testDeps(), token: TOKEN });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  try {
    return await fn(`http://127.0.0.1:${port}`);
  } finally {
    server.close();
    await once(server, 'close');
  }
}

const authed = (extra = {}) => ({ Authorization: `Bearer ${TOKEN}`, ...extra });

/* --------------------------------------------------------------- registry -- */

test('every command is well formed', () => {
  assert.ok(COMMAND_NAMES.length >= 20, `expected a substantial registry, got ${COMMAND_NAMES.length}`);
  for (const name of COMMAND_NAMES) {
    const c = COMMANDS[name];
    assert.equal(typeof c.handler, 'function', `${name}.handler`);
    assert.equal(typeof c.describe, 'string', `${name}.describe`);
    assert.ok(c.describe.length > 10, `${name}.describe should be a real sentence`);
    assert.ok(Array.isArray(c.params), `${name}.params`);
    for (const p of c.params) {
      assert.ok(p.name, `${name} has a param with no name`);
      assert.ok(['string', 'number', 'bool', 'json'].includes(p.type), `${name}.${p.name} type "${p.type}"`);
    }
    // Params must be uniquely named or argument coercion is ambiguous.
    const names = c.params.map((p) => p.name);
    assert.equal(new Set(names).size, names.length, `${name} has duplicate param names`);
  }
});

test('command names are safe for a URL path segment', () => {
  for (const name of COMMAND_NAMES) {
    assert.match(name, /^[A-Za-z][A-Za-z0-9]*$/, `"${name}" must match the API route pattern`);
  }
});

test('destructive commands require an explicit confirmation argument', () => {
  for (const name of COMMAND_NAMES) {
    if (!COMMANDS[name].destructive) continue;
    const confirm = COMMANDS[name].params.find((p) => p.name === 'confirm');
    assert.ok(confirm?.required, `${name} is destructive and must require --confirm`);
  }
});

test('read-only commands are not marked destructive', () => {
  for (const name of COMMAND_NAMES) {
    if (COMMANDS[name].readOnly) assert.ok(!COMMANDS[name].destructive, name);
  }
});

/* ------------------------------------------------------------- dispatcher -- */

test('an unknown command names the valid ones', async () => {
  await assert.rejects(
    () => runCommand({ name: 'nope', args: {}, deps: testDeps() }),
    (err) => err instanceof CommandError && err.status === 404 && /Known:/.test(err.message),
  );
});

test('an unknown argument is rejected, not ignored', async () => {
  await assert.rejects(
    () => runCommand({ name: 'status', args: { notAThing: 1 }, deps: testDeps() }),
    (err) => err instanceof CommandError && /unknown argument/.test(err.message),
  );
});

test('a missing required argument is rejected', async () => {
  await assert.rejects(
    () => runCommand({ name: 'setApiKey', args: {}, deps: testDeps() }),
    (err) => err instanceof CommandError && /requires --apiKey/.test(err.message),
  );
});

test('setApiKey never echoes the key back', async () => {
  const result = await runCommand({
    name: 'setApiKey',
    args: { apiKey: 'super-secret-value' },
    deps: testDeps(),
  });
  const serialised = JSON.stringify(result);
  assert.ok(!serialised.includes('super-secret-value'), 'the key must not appear in the response');
  assert.equal(result.keyLength, 'super-secret-value'.length);
});

test('reset refuses without confirmation and works with it', async () => {
  const deps = testDeps();
  await deps.store.putFill({ id: 'f', gridId: 'g', side: 'buy', baseQty: 1, priceUsd: 1, tsMs: 1 });

  await assert.rejects(() => runCommand({ name: 'reset', args: {}, deps }), CommandError);
  assert.equal((await deps.store.allFills()).length, 1, 'nothing may be erased without confirm');

  const result = await runCommand({ name: 'reset', args: { confirm: true }, deps });
  assert.equal(result.cleared.fills, 1);
  assert.equal((await deps.store.allFills()).length, 0);
  assert.match(result.note, /NOT cancelled/);
});

test('arming a live mode requires confirmLive', async () => {
  const deps = testDeps();
  await deps.configStore.setConfig({ mode: 'full-auto' });
  await assert.rejects(
    () => runCommand({ name: 'arm', args: {}, deps }),
    (err) => err instanceof CommandError && err.status === 412,
  );
  const ok = await runCommand({ name: 'arm', args: { confirmLive: true }, deps });
  assert.equal(ok.runtime.armed, true);
});

test('arming is refused while the kill switch is latched', async () => {
  const deps = testDeps();
  await runCommand({ name: 'kill', args: {}, deps });
  await assert.rejects(
    () => runCommand({ name: 'arm', args: {}, deps }),
    (err) => err instanceof CommandError && err.status === 409,
  );
  await runCommand({ name: 'clearKill', args: {}, deps });
  assert.equal((await runCommand({ name: 'arm', args: {}, deps })).runtime.armed, true);
});

/* -------------------------------------------------------------------- CLI -- */

test('CLI help lists every command', async () => {
  const { code, stdout } = await run([]);
  assert.equal(code, 0);
  for (const name of COMMAND_NAMES) {
    assert.ok(stdout.includes(name), `CLI help is missing "${name}"`);
  }
});

test('CLI exposes per-command help for every command', async () => {
  const results = await Promise.all(COMMAND_NAMES.map((name) => run([name, '--help'])));
  results.forEach((r, i) => {
    const name = COMMAND_NAMES[i];
    assert.equal(r.code, 0, `${name} --help exited ${r.code}: ${r.stderr}`);
    assert.ok(r.stdout.includes(name), `${name} --help should name the command`);
    for (const p of COMMANDS[name].params) {
      assert.ok(r.stdout.includes(`--${p.name}`), `${name} --help omits --${p.name}`);
    }
  });
});

test('CLI rejects an unknown command and an unknown flag', async () => {
  const bad = await run(['definitelyNotACommand']);
  assert.equal(bad.code, 2);
  const badFlag = await run(['status', '--nonsense', '1']);
  assert.equal(badFlag.code, 2);
  assert.match(badFlag.stderr, /no argument --nonsense/);
});

test('CLI coerces numbers and rejects non-numeric input', async () => {
  const bad = await run(['plan', '--price', 'abc', '--ephemeral']);
  assert.equal(bad.code, 1);
  assert.match(bad.stderr, /must be a number/);
});

/* -------------------------------------------------------------- HTTP API -- */

test('health needs no auth; everything else does', async () => {
  await withServer(async (base) => {
    const health = await fetch(`${base}/v1/health`);
    assert.equal(health.status, 200);
    assert.equal((await health.json()).ok, true);

    const unauth = await fetch(`${base}/v1/status`);
    assert.equal(unauth.status, 401);

    const wrong = await fetch(`${base}/v1/status`, { headers: { Authorization: 'Bearer nope' } });
    assert.equal(wrong.status, 401);
  });
});

test('browser-originated requests are refused even with a valid token', async () => {
  await withServer(async (base) => {
    for (const header of [{ Origin: 'https://evil.example' }, { 'Sec-Fetch-Site': 'cross-site' }]) {
      const res = await fetch(`${base}/v1/status`, { headers: authed(header) });
      assert.equal(res.status, 403, `expected 403 for ${JSON.stringify(header)}`);
    }
  });
});

test('every command is routable over the API', async () => {
  await withServer(async (base) => {
    for (const name of COMMAND_NAMES) {
      // A deliberately invalid argument proves the route resolved to the command
      // WITHOUT running its handler — so this probes all 20+ commands with zero
      // side effects and no network calls.
      const res = await fetch(`${base}/v1/${name}`, {
        method: 'POST',
        headers: authed({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ __probe__: true }),
      });
      const body = await res.json();
      assert.equal(res.status, 400, `${name} should reject the probe argument, got ${res.status}`);
      // Either validation error proves the route resolved to this command
      // without executing it: required-arg checks run before unknown-arg checks.
      assert.match(body.error, /unknown argument|requires --/, `${name}: ${body.error}`);
    }
  });
});

test('GET is allowed only for read-only commands', async () => {
  await withServer(async (base) => {
    for (const name of COMMAND_NAMES) {
      const res = await fetch(`${base}/v1/${name}?__probe__=1`, { headers: authed() });
      if (COMMANDS[name].readOnly) {
        assert.equal(res.status, 400, `${name} is read-only so GET should reach validation`);
      } else {
        assert.equal(res.status, 405, `${name} writes state so GET must be refused`);
      }
    }
  });
});

test('discovery describes every command and its arguments', async () => {
  await withServer(async (base) => {
    const res = await fetch(`${base}/v1/commands`, { headers: authed() });
    assert.equal(res.status, 200);
    const { commands } = await res.json();
    assert.deepEqual(
      commands.map((c) => c.name).sort(),
      [...COMMAND_NAMES].sort(),
      'discovery must list exactly the registry',
    );
    assert.deepEqual(commands, describeCommands());
  });
});

test('unknown routes and methods are refused', async () => {
  await withServer(async (base) => {
    assert.equal((await fetch(`${base}/v1/nope`, { headers: authed() })).status, 404);
    assert.equal((await fetch(`${base}/nope`, { headers: authed() })).status, 404);
    assert.equal(
      (await fetch(`${base}/v1/status`, { method: 'DELETE', headers: authed() })).status,
      405,
    );
  });
});

test('a malformed body is rejected with a clear message', async () => {
  await withServer(async (base) => {
    const res = await fetch(`${base}/v1/plan`, {
      method: 'POST',
      headers: authed({ 'Content-Type': 'application/json' }),
      body: 'not json',
    });
    assert.equal(res.status, 400);
    assert.match((await res.json()).error, /not valid JSON/);

    const arrayBody = await fetch(`${base}/v1/plan`, {
      method: 'POST',
      headers: authed({ 'Content-Type': 'application/json' }),
      body: '[1,2,3]',
    });
    assert.equal(arrayBody.status, 400);
  });
});

test('a read-only command returns real data over the API', async () => {
  await withServer(async (base) => {
    const res = await fetch(`${base}/v1/levels`, { headers: authed() });
    assert.equal(res.status, 200);
    const { ok, result } = await res.json();
    assert.equal(ok, true);
    assert.ok(Array.isArray(result.levels) && result.levels.length >= 2);
    assert.ok(result.rungWidthBps > 0);
    // Every rung must capture a positive spread — the economic contract.
    assert.ok(result.expectedRoundTripUsd.every((r) => r.grossUsd > 0));
  });
});

/* -------------------------------------------------- extension UI parity -- */

test('every message the bundled UI sends maps to a real command', async () => {
  const uiDir = join(ROOT, 'src', 'ui');
  const files = (await readdir(uiDir)).filter((f) => f.endsWith('.js'));
  assert.ok(files.length > 0, 'expected UI scripts to scan');

  const aliases = { tickNow: 'tick' };
  const seen = new Set();

  for (const file of files) {
    const source = await readFile(join(uiDir, file), 'utf8');
    for (const match of source.matchAll(/type:\s*'([A-Za-z][A-Za-z0-9]*)'/g)) {
      const raw = match[1];
      const resolved = aliases[raw] ?? raw;
      seen.add(raw);
      assert.ok(
        COMMANDS[resolved],
        `${file} sends {type:'${raw}'} which is not a command (nor an alias of one)`,
      );
    }
  }

  // Sanity: the scan actually found the messages rather than silently matching none.
  assert.ok(seen.has('status'), 'expected the UI to request status');
  assert.ok(seen.size >= 5, `expected several UI messages, found ${seen.size}`);
});

// ---------------------------------------------- auto re-centring, via commands
//
// Every other re-centring test builds config in-process with
// `configStore.setConfig({...})`, which bypasses the command layer entirely. A
// green suite is fully consistent with a flag no surface can actually set, so
// these go through `runCommand`.

test('autoRecentre is settable by name from every surface, not just via --patch', async () => {
  const setConfig = COMMANDS.setConfig;
  for (const field of ['autoRecentre', 'recentreSpanPct', 'recentreDriftBps']) {
    assert.ok(
      setConfig.params.some((p) => p.name === field),
      `${field} needs a named param or the CLI and HTTP surfaces cannot reach it`,
    );
  }

  const deps = testDeps();
  const { config } = await runCommand({
    name: 'setConfig',
    args: { autoRecentre: true, recentreSpanPct: 0.2, recentreDriftBps: 50 },
    deps,
  });
  assert.equal(config.autoRecentre, true);
  assert.equal(config.recentreSpanPct, 0.2);
  assert.equal(config.recentreDriftBps, 50);
});

test('a span that would break recentredBounds is refused at set time', async () => {
  // ConfigStore.setConfig is a blind merge, so without this the bad value is not
  // caught until recentredBounds() throws inside every tick — fail-closed, but it
  // bricks the grid silently instead of rejecting the input.
  for (const bad of [0, 1, 1.5, -0.1]) {
    await assert.rejects(
      () => runCommand({ name: 'setConfig', args: { recentreSpanPct: bad }, deps: testDeps() }),
      CommandError,
      `recentreSpanPct ${bad} must be refused`,
    );
  }
  for (const bad of [-1, Infinity, NaN]) {
    await assert.rejects(
      () => runCommand({ name: 'setConfig', args: { recentreDriftBps: bad }, deps: testDeps() }),
      CommandError,
      `recentreDriftBps ${bad} must be refused`,
    );
  }
  // The --patch escape hatch is validated on the same path, not around it.
  await assert.rejects(
    () => runCommand({ name: 'setConfig', args: { patch: { recentreSpanPct: 9 } }, deps: testDeps() }),
    CommandError,
  );
});

test('plan explains a previewed re-centre instead of silently showing moved levels', async () => {
  const deps = testDeps();
  await deps.configStore.setConfig({
    gridId: 'g1', lower: 500, upper: 900, rungs: 5, notionalPerRungUsd: 25, autoRecentre: true,
  });
  // The stub venue prices at $100, well below the 500-900 ladder.
  const result = await runCommand({ name: 'plan', args: {}, deps });
  assert.ok(result.recentre, 'plan must report the re-centre decision');
  assert.equal(result.recentre.applied, true);
  assert.deepEqual(result.recentre.from, { lower: 500, upper: 900 });
  assert.deepEqual(result.recentre.to, { lower: 85, upper: 115 });
  // readOnly: previewing must not have moved the stored config.
  const config = await deps.configStore.getConfig();
  assert.deepEqual([config.lower, config.upper], [500, 900]);
});
