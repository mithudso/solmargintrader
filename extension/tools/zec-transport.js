/** Private, per-user IPC for the three Zec advisory commands. */
import { lstat } from 'node:fs/promises';
import net from 'node:net';
import { endianness } from 'node:os';
import path from 'node:path';

export const ZEC_NATIVE_HOST = 'com.mitchhudson.solmargintrader_zec';
export const ZEC_NATIVE_COMMANDS = Object.freeze(['zecSnapshot', 'zecAdvisories', 'zecAdvice']);
export const MAX_ZEC_REQUEST_BYTES = 16 * 1024;
export const MAX_ZEC_REPLY_BYTES = 256 * 1024;
export const ZEC_REQUEST_TIMEOUT_MS = 12_000;
export const ZEC_CHROME_UNAVAILABLE = Object.freeze({
  ok: false,
  error: 'Zec bridge is unavailable. Connect it in the Chrome extension.',
  status: 503,
});
const CHROME_ORIGIN = /^chrome-extension:\/\/[a-p]{32}\/$/;
const nativeLittleEndian = endianness() === 'LE';

export const isZecOrigin = (value) => typeof value === 'string' && CHROME_ORIGIN.test(value);

export function zecSocketPath(env = process.env) {
  // Finder-launched Chrome and the CLI may have different TMPDIR values.
  return validateZecSocketPath(env.SOLMARGIN_ZEC_SOCKET || `/tmp/smt-zec-${process.getuid()}/chrome.sock`);
}

export function validateZecSocketPath(value) {
  // macOS sockaddr_un.sun_path is 104 bytes including the NUL terminator.
  if (typeof value !== 'string' || !path.isAbsolute(value) || path.normalize(value) !== value
      || !path.basename(value) || path.dirname(value) === '/' || /[\0\r\n]/.test(value)
      || Buffer.byteLength(value) >= 104) {
    throw new Error('Zec socket must be an absolute path shorter than 104 bytes inside a private directory.');
  }
  return value;
}

export function isPrivateZecPath(stat, type) {
  return stat[type]() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0;
}

export function isZecRequest(message) {
  return ZEC_NATIVE_COMMANDS.includes(message?.name) && message.params !== null
    && typeof message.params === 'object' && !Array.isArray(message.params)
    && Object.keys(message).every((key) => key === 'name' || key === 'params');
}

export function isZecResult(result) {
  if (result?.ok === true) return Object.hasOwn(result, 'result');
  return result?.ok === false && typeof result.error === 'string' && result.error.length <= 500
    && (result.status === undefined || (Number.isInteger(result.status) && result.status >= 400 && result.status <= 599));
}

export function encodeZecFrame(message, limit) {
  const body = Buffer.from(JSON.stringify(message), 'utf8');
  if (body.length === 0 || body.length > limit) throw new Error('Zec bridge frame exceeds its size limit.');
  const header = Buffer.alloc(4);
  if (nativeLittleEndian) header.writeUInt32LE(body.length);
  else header.writeUInt32BE(body.length);
  return Buffer.concat([header, body]);
}

export function readZecFrames(limit, onMessage) {
  let buffer = Buffer.alloc(0);
  return (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    while (buffer.length >= 4) {
      const size = nativeLittleEndian ? buffer.readUInt32LE() : buffer.readUInt32BE();
      if (size === 0 || size > limit) throw new Error('Zec bridge frame has an invalid size.');
      if (buffer.length < size + 4) return;
      const message = JSON.parse(buffer.subarray(4, 4 + size).toString('utf8'));
      buffer = buffer.subarray(4 + size);
      onMessage(message);
    }
  };
}

export async function requestZecChrome(name, params = {}, { env = process.env } = {}) {
  const request = { name, params };
  if (!isZecRequest(request)) return { ok: false, error: 'Unsupported Zec advisory request.', status: 400 };

  let frame;
  try {
    frame = encodeZecFrame(request, MAX_ZEC_REQUEST_BYTES);
  } catch {
    return { ok: false, error: 'Zec advisory request cannot be encoded or exceeds the size limit.', status: 400 };
  }

  let endpoint;
  try {
    endpoint = zecSocketPath(env);
    const [directory, socket] = await Promise.all([lstat(path.dirname(endpoint)), lstat(endpoint)]);
    if (!isPrivateZecPath(directory, 'isDirectory') || !isPrivateZecPath(socket, 'isSocket')) {
      return ZEC_CHROME_UNAVAILABLE;
    }
  } catch {
    return ZEC_CHROME_UNAVAILABLE;
  }

  return new Promise((resolve) => {
    const socket = net.createConnection(endpoint);
    const finish = (result) => {
      clearTimeout(timer);
      socket.destroy();
      resolve(result);
    };
    const failed = () => finish(ZEC_CHROME_UNAVAILABLE);
    const reader = readZecFrames(MAX_ZEC_REPLY_BYTES, (reply) => finish(isZecResult(reply) ? reply : ZEC_CHROME_UNAVAILABLE));
    const timer = setTimeout(failed, ZEC_REQUEST_TIMEOUT_MS);
    socket.once('connect', () => socket.write(frame));
    socket.once('error', failed);
    socket.once('close', failed);
    socket.on('data', (chunk) => {
      try { reader(chunk); } catch { failed(); }
    });
  });
}
