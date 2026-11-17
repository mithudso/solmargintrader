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
import { timingSafeEqual } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { runCommand, describeCommands, COMMANDS, CommandError } from '../src/core/commands.js';
import { createNodeDeps } from './deps.js';
import { toolArgs, toolFailure } from './args.js';

const MAX_BODY_BYTES = 256 * 1024;

const USAGE = 'Usage: node tools/api-server.js [--port PORT] [--host HOST] [--ephemeral] [--store-path PATH] [--config-path PATH] [--passphrase VALUE]\nRequires SMT_API_TOKEN in the service environment.\nExample: node tools/api-server.js --port 8787';

export function tokenMatches(provided, token) {
  if (typeof token !== 'string' || !token.trim() || typeof provided !== 'string' || !provided) return false;
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
    let refused = false;
    const chunks = [];
    req.on('data', (chunk) => {
      if (refused) return;
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        refused = true;
        chunks.length = 0;
        reject(new CommandError('request body too large', 413));
        req.resume();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (refused) return;
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
      } catch {
        reject(new CommandError('body is not valid JSON', 400));
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
      try {
        out[key] = JSON.parse(raw);
      } catch {
        throw new CommandError(`"${key}" must contain valid JSON`, 400);
      }
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
  if (typeof token !== 'string' || !token.trim()) throw new TypeError('API bearer token must be a nonempty string');
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
      deps.log?.({ level: 'warn', msg: 'API browser request refused' });
      send(res, 403, {
        ok: false,
        error: 'browser-originated requests are refused; use a CLI or server-side client',
      });
      return;
    }

    const auth = req.headers.authorization ?? '';
    const bearer = auth.startsWith('Bearer ') ? auth.slice(7) : '';
    if (!tokenMatches(bearer, token)) {
      deps.log?.({ level: 'warn', msg: 'API authentication refused' });
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
      deps.log?.({ level: 'warn', msg: 'API request rejected', status: err.status ?? 400 });
      send(res, err.status ?? 400, { ok: false, error: err.message });
      return;
    }
    // Upstream exception messages may contain credentials or response bodies.
      deps.log?.({ level: 'error', msg: 'API request failed', status: 500 });
      send(res, 500, { ok: false, error: 'internal command failure' });
    }
  };
}

/** Build a server without listening — used by tests and by main(). */
export function createApiServer({ deps, token }) {
  return createServer(createRequestHandler({ deps, token }));
}

const API_MESSAGES = new Set(['API browser request refused', 'API authentication refused',
  'API request rejected', 'API request failed']);

function logApiEvent(event) {
  // Never serialize upstream errors, request bodies/URLs, headers or credentials.
  const diagnostic = { type: 'api', level: event.level === 'error' ? 'error' : 'warn',
    msg: API_MESSAGES.has(event.msg) ? event.msg : 'command diagnostic' };
  if (Number.isInteger(event.status) && event.status >= 100 && event.status <= 599) diagnostic.status = event.status;
  process.stderr.write(`${JSON.stringify(diagnostic)}\n`);
}

async function main() {
  const args = toolArgs(process.argv.slice(2), { port: undefined, host: undefined, ephemeral: false,
    'store-path': undefined, 'config-path': undefined, passphrase: undefined }, { booleans: ['ephemeral'], usage: USAGE });
  if (args.help) { console.log(USAGE); return; }
  const port = Number(args.port ?? process.env.SMT_API_PORT ?? 8787);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw Object.assign(new Error(`port must be an integer from 1 to 65535\n${USAGE}`), { exitCode: 2 });
  const host = typeof args.host === 'string' ? args.host : '127.0.0.1';
  const token = process.env.SMT_API_TOKEN;
  if (typeof token !== 'string' || !token.trim()) {
    throw Object.assign(new Error('SMT_API_TOKEN must be set in the service environment before starting the API; credentials are never printed'), { exitCode: 3 });
  }

  const deps = await createNodeDeps({
    ephemeral: args.ephemeral === true,
    quiet: true,
    storePath: typeof args['store-path'] === 'string' ? args['store-path'] : undefined,
    configPath: typeof args['config-path'] === 'string' ? args['config-path'] : undefined,
    passphrase: typeof args.passphrase === 'string' ? args.passphrase : process.env.SMT_PASSPHRASE,
  });
  deps.log = logApiEvent;

  const server = createApiServer({ deps, token });

  server.listen(port, host, () => {
    console.log(`solmargintrader API on http://${host}:${port}`);
    console.log(`commands: ${Object.keys(COMMANDS).length}  state: ${deps.paths.store}`);
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
function ranDirectly() {
  if (!process.argv[1]) return false;
  try {
    // Node resolves entrypoint symlinks; macOS /var is itself a symlink. Both
    // sides must use filesystem paths before comparing the physical file.
    return realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1]);
  } catch { return false; } // eval/import callers need not have a file entrypoint.
}
if (ranDirectly()) {
  await main().catch(toolFailure);
}
