#!/usr/bin/env node
/**
 * HTTP API surface.
 *
 * Routes are generated from the registry in src/core/commands.js — the same
 * registry the CLI and the extension use — so no endpoint can drift from the
 * extension's behaviour.
 *
 *   GET  /v1/health              liveness, no auth
 *   GET  /v1/commands            discovery: every command, its args and types
 *   GET  /v1/<command>?a=1       read-only commands, args from the query string
 *   POST /v1/<command>           any command, args from a JSON body
 *
 * Security posture — this endpoint can move real money, so:
 *
 *   - binds 127.0.0.1 by default; --host must be passed explicitly to widen it
 *   - every command route requires `Authorization: Bearer <token>`
 *   - a request carrying an Origin or Sec-Fetch-Site header is refused. A web
 *     page CAN post to localhost, so a token alone is not enough: without this,
 *     any site you visit could drive your grid. No CORS headers are ever sent,
 *     which is deliberate — browsers are not a supported client
 *   - the token is compared with a timing-safe equality check
 *   - GET is restricted to read-only commands, so nothing that places an order
 *     is reachable from a URL alone
 *
 *   node tools/api-server.js --port 8787
 *   SMT_API_TOKEN=secret node tools/api-server.js
 */

import { createServer } from 'node:http';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { runCommand, describeCommands, COMMANDS, CommandError } from '../src/core/commands.js';
import { createNodeDeps } from './deps.js';

const MAX_BODY_BYTES = 256 * 1024;

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) continue;
    const key = argv[i].slice(2);
    const next = argv[i + 1];
    out[key] = next && !next.startsWith('--') ? next : true;
  }
  return out;
}

export function tokenMatches(provided, token) {
  const a = Buffer.from(provided ?? '');
  const b = Buffer.from(token);
  // Compare lengths separately: timingSafeEqual throws on a length mismatch.
  return a.length === b.length && timingSafeEqual(a, b);
}

function send(res, status, payload) {
  const body = JSON.stringify(payload, null, 2);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
    // No CORS headers by design; browsers are not a supported client.
    'x-content-type-options': 'nosniff',
    'cache-control': 'no-store',
  });
  res.end(body);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new CommandError('request body too large', 413));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8').trim();
      if (!raw) {
        resolve({});
        return;
      }
      try {
        const parsed = JSON.parse(raw);
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
          reject(new CommandError('body must be a JSON object', 400));
          return;
        }
        resolve(parsed);
      } catch (err) {
        reject(new CommandError(`body is not valid JSON: ${err.message}`, 400));
      }
    });
    req.on('error', reject);
  });
}

/** Query strings are all strings; coerce to the types the registry declares. */
function coerceQuery(name, query) {
  const params = COMMANDS[name].params;
  const out = {};
  for (const [key, raw] of query.entries()) {
    const param = params.find((p) => p.name === key);
    if (!param) throw new CommandError(`command "${name}" has no argument "${key}"`, 400);
    if (param.type === 'number') {
      const n = Number(raw);
      if (!Number.isFinite(n)) throw new CommandError(`"${key}" must be a number`, 400);
      out[key] = n;
    } else if (param.type === 'bool') {
      out[key] = raw === 'true' || raw === '1' || raw === 'yes';
    } else if (param.type === 'json') {
      out[key] = JSON.parse(raw);
    } else {
      out[key] = raw;
    }
  }
  return out;
}

/**
 * The request handler, separated from startup so tests can drive it on an
 * ephemeral port without the module launching a listener on import.
 */
export function createRequestHandler({ deps, token }) {
  return async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host ?? 'localhost'}`);
    const path = url.pathname.replace(/\/+$/, '');

    if (path === '/v1/health') {
      send(res, 200, { ok: true, service: 'solmargintrader', commands: Object.keys(COMMANDS).length });
      return;
    }

    // A browser-initiated request is refused outright: a page you visit must not
    // be able to drive the grid, token or no token.
    if (req.headers.origin || req.headers['sec-fetch-site']) {
      send(res, 403, {
        ok: false,
        error: 'browser-originated requests are refused; use a CLI or server-side client',
      });
      return;
    }

    const auth = req.headers.authorization ?? '';
    const bearer = auth.startsWith('Bearer ') ? auth.slice(7) : '';
    if (!tokenMatches(bearer, token)) {
      send(res, 401, { ok: false, error: 'missing or invalid bearer token' });
      return;
    }

    if (path === '/v1/commands') {
      send(res, 200, { ok: true, commands: describeCommands() });
      return;
    }

    const match = /^\/v1\/([A-Za-z][A-Za-z0-9]*)$/.exec(path);
    if (!match) {
      send(res, 404, { ok: false, error: `no route for ${path}`, hint: 'GET /v1/commands' });
      return;
    }

    const name = match[1];
    const command = COMMANDS[name];
    if (!command) {
      send(res, 404, { ok: false, error: `unknown command "${name}"`, hint: 'GET /v1/commands' });
      return;
    }

    let commandArgs;
    if (req.method === 'GET') {
      if (!command.readOnly) {
        send(res, 405, {
          ok: false,
          error: `"${name}" changes state — use POST`,
        });
        return;
      }
      commandArgs = coerceQuery(name, url.searchParams);
    } else if (req.method === 'POST') {
      commandArgs = await readJsonBody(req);
    } else {
      send(res, 405, { ok: false, error: `${req.method} not allowed` });
      return;
    }

    const result = await runCommand({ name, args: commandArgs, deps });
    send(res, 200, { ok: true, command: name, result });
  } catch (err) {
    if (err instanceof CommandError) {
      send(res, err.status ?? 400, { ok: false, error: err.message });
      return;
    }
    // Message only, never a stack: paths and internals do not belong in a
    // response body.
      send(res, 500, { ok: false, error: String(err?.message ?? err) });
    }
  };
}

/** Build a server without listening — used by tests and by main(). */
export function createApiServer({ deps, token }) {
  return createServer(createRequestHandler({ deps, token }));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const port = Number(args.port ?? process.env.SMT_API_PORT ?? 8787);
  const host = typeof args.host === 'string' ? args.host : '127.0.0.1';
  const token = process.env.SMT_API_TOKEN || randomBytes(24).toString('base64url');

  const deps = await createNodeDeps({
    ephemeral: args.ephemeral === true,
    quiet: true,
    storePath: typeof args['store-path'] === 'string' ? args['store-path'] : undefined,
    configPath: typeof args['config-path'] === 'string' ? args['config-path'] : undefined,
    passphrase: typeof args.passphrase === 'string' ? args.passphrase : process.env.SMT_PASSPHRASE,
  });

  const server = createApiServer({ deps, token });

  server.listen(port, host, () => {
    console.log(`solmargintrader API on http://${host}:${port}`);
    console.log(`commands: ${Object.keys(COMMANDS).length}  state: ${deps.paths.store}`);
    if (!process.env.SMT_API_TOKEN) {
      console.log(`\ngenerated token (set SMT_API_TOKEN to pin it):\n  ${token}\n`);
    }
    console.log(
      `example:\n  curl -s -H "Authorization: Bearer $SMT_API_TOKEN" http://${host}:${port}/v1/status`,
    );
    if (host !== '127.0.0.1' && host !== 'localhost') {
      console.warn(
        `\nWARNING: bound to ${host}, not loopback. This API can place real orders — do not expose it to a network you do not control.`,
      );
    }
  });

  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => server.close(() => process.exit(0)));
  }
}

// Only start a listener when run directly; importing this module must not bind
// a port, or the test suite would fight the running server for it.
if (process.argv[1] && import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
