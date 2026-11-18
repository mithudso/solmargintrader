/** Chrome owns this process. Its standard output carries native-message frames only. */
import { randomUUID } from 'node:crypto';
import { constants as fsFlags } from 'node:fs';
import { chmod, lstat, mkdir, open, rmdir, unlink } from 'node:fs/promises';
import net from 'node:net';
import { dirname } from 'node:path';
import {
  encodeZecFrame, isPrivateZecPath, isZecOrigin, isZecRequest, isZecResult, readZecFrames,
  MAX_ZEC_REPLY_BYTES, MAX_ZEC_REQUEST_BYTES, validateZecSocketPath, ZEC_CHROME_UNAVAILABLE,
  ZEC_REQUEST_TIMEOUT_MS,
} from './zec-transport.js';

const MAX_CONNECTIONS = 16;
const REPLY_TIMEOUT_MS = ZEC_REQUEST_TIMEOUT_MS - 1000;
const INVALID_REQUEST = { ok: false, error: 'Invalid Zec advisory request.', status: 400 };

async function verifyEndpointDirectory(endpoint) {
  const directory = dirname(endpoint);
  await mkdir(directory, { mode: 0o700, recursive: true });
  if (!isPrivateZecPath(await lstat(directory), 'isDirectory')) {
    throw new Error('Zec endpoint directory belongs to another user or is accessible to others.');
  }
}

async function claimEndpoint(endpoint) {
  const claim = `${endpoint}.binding`;
  if (process.platform !== 'darwin') {
    // Portable fail-closed fallback. If this host was killed without cleanup,
    // remove the old claim only after confirming no host process is running.
    await mkdir(claim, { mode: 0o700 });
    return () => rmdir(claim);
  }

  // Darwin's O_EXLOCK from sys/fcntl.h. Keep the descriptor open through
  // socket cleanup. The kernel releases the claim even if Chrome kills us.
  const exclusive = 0x20;
  const flags = fsFlags.O_CREAT | fsFlags.O_RDWR | fsFlags.O_NOFOLLOW | fsFlags.O_NONBLOCK | exclusive;
  const lock = await open(claim, flags, 0o600);
  try {
    if (!isPrivateZecPath(await lock.stat(), 'isFile')) throw new Error('Zec endpoint claim is not private.');
  } catch (error) {
    await lock.close();
    throw error;
  }
  return () => lock.close();
}

async function removeDeadSocket(endpoint) {
  const socket = await lstat(endpoint).catch((error) => {
    if (error.code === 'ENOENT') return null;
    throw error;
  });
  if (!socket) return;
  if (!isPrivateZecPath(socket, 'isSocket')) throw new Error('Zec endpoint already exists with unexpected ownership or type.');

  const outcome = await new Promise((resolve) => {
    const probe = net.createConnection(endpoint);
    const complete = (status) => { probe.destroy(); resolve(status); };
    probe.setTimeout(1000, () => complete('timeout'));
    probe.once('connect', () => complete('active'));
    probe.once('error', (error) => complete(error.code));
  });
  if (outcome === 'ENOENT') return;
  if (outcome !== 'ECONNREFUSED') throw new Error('Zec endpoint already belongs to a running host.');
  await unlink(endpoint);
}

async function runHost(endpoint) {
  await verifyEndpointDirectory(endpoint);
  // Serialize stale-socket checks and binding. Holding the claim until shutdown
  // also prevents an old server's automatic socket cleanup from unlinking a new one.
  const releaseClaim = await claimEndpoint(endpoint);
  const pending = new Map();
  const clients = new Set();
  let running = true;

  const server = net.createServer((socket) => {
    clients.add(socket);
    let id;
    let sent = false;
    const finish = (result) => {
      if (sent) return;
      sent = true;
      if (id) pending.delete(id);
      clearTimeout(timer);
      let reply;
      try { reply = encodeZecFrame(result, MAX_ZEC_REPLY_BYTES); }
      catch { reply = encodeZecFrame(ZEC_CHROME_UNAVAILABLE, MAX_ZEC_REPLY_BYTES); }
      socket.end(reply);
    };
    const timer = setTimeout(() => finish(ZEC_CHROME_UNAVAILABLE), REPLY_TIMEOUT_MS);

    const reader = readZecFrames(MAX_ZEC_REQUEST_BYTES, (request) => {
      if (sent) return;
      if (id || !running || !isZecRequest(request)) return finish(INVALID_REQUEST);
      id = randomUUID();
      pending.set(id, finish);
      process.stdout.write(encodeZecFrame({ id, ...request }, MAX_ZEC_REPLY_BYTES));
    });
    socket.on('data', (chunk) => {
      try { reader(chunk); } catch { finish(INVALID_REQUEST); }
    });
    socket.once('error', () => socket.destroy());
    socket.once('close', () => {
      clearTimeout(timer);
      if (id) pending.delete(id);
      clients.delete(socket);
    });
  });
  server.maxConnections = MAX_CONNECTIONS;

  async function stop(exitCode = 0) {
    if (!running) return;
    running = false;
    process.exitCode = exitCode;
    process.stdin.pause();
    for (const client of clients) client.destroy();
    if (server.listening) await new Promise((resolve) => server.close(resolve));
    await releaseClaim();
  }

  try {
    await removeDeadSocket(endpoint);
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen(endpoint, () => {
        server.off('error', reject);
        resolve();
      });
    });
    await chmod(endpoint, 0o600);
  } catch (error) {
    await stop(1);
    throw error;
  }

  function shutDown(code) {
    stop(code).catch(() => {
      process.exitCode = 1;
      process.stderr.write('Zec host could not remove its local endpoint claim.\n');
    });
  }

  const reader = readZecFrames(MAX_ZEC_REPLY_BYTES, ({ id, result }) => {
    // A late or unknown response cannot answer another client's request.
    pending.get(id)?.(isZecResult(result) ? result : ZEC_CHROME_UNAVAILABLE);
  });
  process.stdin.on('data', (chunk) => {
    try { reader(chunk); } catch { shutDown(1); }
  });
  server.once('error', () => shutDown(1));
  process.stdin.once('end', () => shutDown(0));
  process.stdin.once('error', () => shutDown(1));
  process.stdout.once('error', () => shutDown(1));
  process.once('SIGINT', () => shutDown(0));
  process.once('SIGTERM', () => shutDown(0));
  process.stdout.write(encodeZecFrame({ ready: true }, MAX_ZEC_REPLY_BYTES));
}

async function main() {
  // Chrome appends the caller origin as the first native launch argument.
  const [endpoint, allowedOrigin, launchOrigin] = process.argv.slice(2);
  if (!isZecOrigin(allowedOrigin) || !launchOrigin || launchOrigin.replace(/\/?$/, '/') !== allowedOrigin) {
    throw new Error('Unrecognized Chrome extension origin.');
  }
  await runHost(validateZecSocketPath(endpoint));
}

main().catch((error) => {
  process.stderr.write(['EEXIST', 'EADDRINUSE', 'EAGAIN', 'EWOULDBLOCK'].includes(error.code)
    ? 'Zec endpoint is already claimed by another Chrome host.\n'
    : 'Zec native host could not start. Check the registered origin and private endpoint.\n');
  process.exitCode = 1;
});
