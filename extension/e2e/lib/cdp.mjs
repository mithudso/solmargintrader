/**
 * Minimal Chrome DevTools Protocol client over the DevTools pipe.
 *
 * Why the pipe and not a WebSocket: `Extensions.loadUnpacked` is only exposed on
 * `--remote-debugging-pipe` (with `--enable-unsafe-extension-debugging`), and the
 * branded Chrome channel ignores `--load-extension`. So this needs Chrome for
 * Testing or Chromium, and it needs no port, no HTTP discovery and no package.
 *
 * Wire format: JSON messages, each terminated by a NUL byte, on file descriptor 3
 * (to the browser) and 4 (from the browser).
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Split a NUL-delimited stream into complete frames.
 * Pure, so the framing is unit-tested without a browser.
 * @returns {{frames: object[], rest: string, malformed: number}}
 */
export function parseFrames(buffer) {
  const frames = [];
  let malformed = 0;
  let rest = buffer;
  for (let i = rest.indexOf('\0'); i >= 0; i = rest.indexOf('\0')) {
    const raw = rest.slice(0, i);
    rest = rest.slice(i + 1);
    if (!raw) continue;
    try {
      frames.push(JSON.parse(raw));
    } catch {
      // A bad frame must not poison the frames after it, but it must be visible.
      malformed += 1;
    }
  }
  return { frames, rest, malformed };
}

/** Newest Chrome for Testing under the @puppeteer/browsers cache, or null. */
export function findChromeForTesting(home = os.homedir()) {
  const base = path.join(home, '.cache/puppeteer/chrome');
  if (!fs.existsSync(base)) return null;
  const rel = [
    'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-linux64/chrome',
  ];
  const builds = fs
    .readdirSync(base)
    .map((dir) => ({
      version: /-(\d+(?:\.\d+)*)$/.exec(dir)?.[1],
      bin: rel.map((r) => path.join(base, dir, r)).find((p) => fs.existsSync(p)),
    }))
    .filter((b) => b.version && b.bin)
    .sort((a, b) => b.version.localeCompare(a.version, undefined, { numeric: true }));
  return builds[0]?.bin ?? null;
}

const CALL_TIMEOUT_MS = 15_000;
const EXIT_GRACE_MS = 2_000;

/**
 * Launch Chrome, load one unpacked extension, and return a session handle.
 * @param {{chrome: string, extension: string, noSandbox?: boolean, headless?: boolean}} opts
 */
export async function launch({ chrome, extension, noSandbox = false, headless = true }) {
  if (!chrome || !fs.existsSync(chrome)) throw new Error('no Chrome for Testing binary (set CHROME)');
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'smt-e2e-'));
  const proc = spawn(
    chrome,
    [
      `--user-data-dir=${profile}`,
      '--remote-debugging-pipe',
      '--enable-unsafe-extension-debugging',
      ...(headless ? ['--headless=new'] : []),
      ...(noSandbox ? ['--no-sandbox'] : []),
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-background-networking',
      '--disable-component-update',
      'about:blank',
    ],
    { stdio: ['ignore', 'ignore', 'ignore', 'pipe', 'pipe'] },
  );
  const [toChrome, fromChrome] = [proc.stdio[3], proc.stdio[4]];

  let exited = false;
  const exit = new Promise((r) => proc.once('exit', () => ((exited = true), r())));
  let seq = 0;
  let dead = null;
  const pending = new Map();
  const listeners = new Set();

  const failAll = (why) => {
    dead ??= why;
    for (const p of pending.values()) {
      clearTimeout(p.timer);
      p.reject(new Error(`${p.method}: ${why}`));
    }
    pending.clear();
  };

  let buf = '';
  fromChrome.setEncoding('utf8');
  fromChrome.on('data', (chunk) => {
    const parsed = parseFrames(buf + chunk);
    buf = parsed.rest;
    for (const m of parsed.frames) {
      if (m.id !== undefined && pending.has(m.id)) {
        const p = pending.get(m.id);
        pending.delete(m.id);
        clearTimeout(p.timer);
        if (m.error) p.reject(new Error(`${p.method}: ${m.error.message}`));
        else p.resolve(m.result);
      } else if (m.method) {
        for (const fn of listeners) fn(m);
      }
    }
  });
  proc.on('exit', () => failAll('Chrome exited'));
  proc.on('error', (e) => failAll(`Chrome could not start: ${e.message}`));
  for (const s of [toChrome, fromChrome]) s.on('error', () => failAll('DevTools pipe closed'));

  const call = (method, params = {}, sessionId, timeoutMs = CALL_TIMEOUT_MS) => {
    if (dead) return Promise.reject(new Error(`${method}: ${dead}`));
    const id = ++seq;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`${method}: timed out after ${timeoutMs} ms`));
      }, timeoutMs);
      pending.set(id, { resolve, reject, method, timer });
      try {
        toChrome.write(`${JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) })}\0`);
      } catch (e) {
        pending.delete(id);
        clearTimeout(timer);
        reject(e);
      }
    });
  };

  const close = async () => {
    failAll('closed');
    if (!exited) {
      proc.kill('SIGTERM');
      const stopped = await Promise.race([exit.then(() => true), sleep(EXIT_GRACE_MS).then(() => false)]);
      if (!stopped) {
        proc.kill('SIGKILL');
        await Promise.race([exit, sleep(EXIT_GRACE_MS)]);
      }
    }
    fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  };

  let extensionId;
  try {
    await call('Browser.getVersion');
    ({ id: extensionId } = await call('Extensions.loadUnpacked', { path: path.resolve(extension) }));
  } catch (e) {
    await close();
    throw e;
  }

  const version = (await call('Browser.getVersion')).product;
  const on = (fn) => (listeners.add(fn), () => listeners.delete(fn));
  const targets = async () => (await call('Target.getTargets')).targetInfos;

  /** Attach to a target and return its flat session id. */
  const attach = async (targetId) => {
    const { sessionId } = await call('Target.attachToTarget', { targetId, flatten: true });
    return sessionId;
  };

  /** Run an expression in a session and return its JSON-serialisable value. */
  const evaluate = async (sessionId, expression) => {
    const r = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
    if (r.exceptionDetails) {
      throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    }
    return r.result.value;
  };

  const waitFor = async (fn, ms = 10_000, stepMs = 150) => {
    const end = Date.now() + ms;
    for (;;) {
      const v = await fn();
      if (v) return v;
      if (Date.now() >= end) return null;
      await sleep(stepMs);
    }
  };

  return { call, on, targets, attach, evaluate, waitFor, extensionId, version, close };
}
