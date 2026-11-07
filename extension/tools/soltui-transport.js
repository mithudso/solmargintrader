/**
 * Node transport to the soltui native messaging host.
 *
 * The extension's CLI (tools/cli.js) and HTTP API (tools/api-server.js) reach
 * soltui the same way the browser does: by running the native host and speaking
 * Chrome's framing, a 4-byte little-endian length then UTF-8 JSON, on its
 * stdio. Both then get the very envelope soltui produced, through the same
 * src/core/soltui.js, so a call returns the same bytes on every surface.
 *
 * One host process per request, ended when the reply arrives. That mirrors the
 * service-worker transport and leaves nothing running between calls.
 *
 * Which program runs:
 *   SOLTUI_NATIVE_HOST   path to the host wrapper (the file the browser's host
 *                        manifest points at); run with no arguments
 *   otherwise            `python -m soltui.native_host` from the repository
 *                        root (SOLTUI_REPO overrides it), with SOLTUI_PYTHON
 *                        (default ~/.venvs/soltui/bin/python)
 *
 * Kept out of src/ for the same reason as deps.js: it imports node:child_process.
 */

import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SoltuiTransportError, SOLTUI_ERROR } from '../src/core/soltui.js';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
// Chrome refuses a host message over 1 MiB; a reply larger than this from a
// misbehaving host is refused here rather than buffered without bound.
const MAX_FRAME_BYTES = 64 * 1024 * 1024;

export const repoRoot = (env = process.env) => env.SOLTUI_REPO || REPO_ROOT;
export const soltuiPython = (env = process.env) =>
  env.SOLTUI_PYTHON || path.join(os.homedir(), '.venvs', 'soltui', 'bin', 'python');

export function defaultHostCommand(env = process.env) {
  if (env.SOLTUI_NATIVE_HOST) return { command: env.SOLTUI_NATIVE_HOST, args: [], cwd: repoRoot(env) };
  return { command: soltuiPython(env), args: ['-m', 'soltui.native_host'], cwd: repoRoot(env) };
}

// The host needs HOME and PATH to find its state and its tools. It does not
// need SMT_API_TOKEN, SMT_PASSPHRASE or anything else in this process's
// environment, so those are not handed on.
const HOST_ENV = /^(HOME|PATH|USER|LOGNAME|SHELL|TMPDIR|LANG|LC_[A-Z]+|SOLTUI_[A-Z_]+|VIRTUAL_ENV)$/;
export const hostEnv = (env) => Object.fromEntries(Object.entries(env).filter(([key]) => HOST_ENV.test(key)));

export const encodeFrame = (message) => {
  const body = Buffer.from(JSON.stringify(message), 'utf8');
  const head = Buffer.alloc(4);
  head.writeUInt32LE(body.length, 0);
  return Buffer.concat([head, body]);
};

/** Pull one complete frame off the front of `buffer`, or null when it is still partial. */
export function decodeFrame(buffer) {
  if (buffer.length < 4) return null;
  const length = buffer.readUInt32LE(0);
  if (length > MAX_FRAME_BYTES) throw new SoltuiTransportError(SOLTUI_ERROR.FAILED, 'soltui host sent an oversized frame');
  if (buffer.length < 4 + length) return null;
  return { message: JSON.parse(buffer.subarray(4, 4 + length).toString('utf8')), rest: buffer.subarray(4 + length) };
}

/**
 * @param {object} [opts]
 * @param {function(): {command: string, args: string[], cwd?: string}} [opts.resolveHost]
 * @param {object} [opts.env]
 */
export function createNodeSoltuiTransport({ resolveHost = defaultHostCommand, env = process.env } = {}) {
  return {
    request(request, { timeoutMs }) {
      return new Promise((resolve, reject) => {
        const id = randomUUID();
        const host = resolveHost(env);
        let child;
        let timer;
        let done = false;
        let buffer = Buffer.alloc(0);

        const finish = (fn, value) => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          try { child?.stdin.end(); } catch { /* closed */ }
          try { child?.kill(); } catch { /* gone */ }
          fn(value);
        };
        const fail = (code, message) => finish(reject, new SoltuiTransportError(code, message));

        try {
          child = spawn(host.command, host.args, { cwd: host.cwd, env: hostEnv(env), stdio: ['pipe', 'pipe', 'ignore'] });
        } catch {
          fail(SOLTUI_ERROR.FAILED, 'soltui native host could not be started; set SOLTUI_NATIVE_HOST or install soltui');
          return;
        }
        child.on('error', () => fail(SOLTUI_ERROR.FAILED,
          'soltui native host is not available; run `python -m soltui.native_host_install install` or set SOLTUI_NATIVE_HOST'));
        child.stdin.on('error', () => {});
        child.stdout.on('data', (chunk) => {
          buffer = Buffer.concat([buffer, chunk]);
          try {
            for (let frame = decodeFrame(buffer); frame; frame = decodeFrame(buffer)) {
              buffer = frame.rest;
              if (frame.message?.id === id) { finish(resolve, frame.message.response); return; }
            }
          } catch (err) {
            fail(SOLTUI_ERROR.FAILED, err instanceof SoltuiTransportError ? err.message : 'soltui host sent an unreadable frame');
          }
        });
        child.on('close', () => fail(SOLTUI_ERROR.FAILED, 'soltui native host exited without answering'));
        timer = setTimeout(
          () => fail(SOLTUI_ERROR.TIMEOUT, `soltui ${request.op === 'call' ? request.command : request.op} timed out after ${Math.round(timeoutMs / 1000)}s`),
          timeoutMs,
        );
        child.stdin.write(encodeFrame({ id, ...request }));
      });
    },
  };
}
