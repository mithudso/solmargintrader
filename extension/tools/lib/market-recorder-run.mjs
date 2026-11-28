/**
 * The market recorder itself: polls, the oracle stream, hourly files and their
 * compression. The clock, the network and the timers are handed in, so the
 * whole of it runs in a test against a temporary folder; the disk is real.
 *
 * It is meant to run unattended for weeks on a network disk. The rules it
 * keeps: a row is never written anywhere but under the folder it was started
 * on, and only while that folder is still the same mounted disk; a disk that
 * stops taking writes ends the run with an error, so a supervisor restarts it;
 * one failing market never costs the others their rows.
 */
import { closeSync, createReadStream, createWriteStream, existsSync, mkdirSync, openSync, readFileSync, readSync, readdirSync, renameSync, rmdirSync,
  statSync, unlinkSync, writeFileSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { hostname, uptime } from 'node:os';
import { dirname, join } from 'node:path';
import { Worker } from 'node:worker_threads';
import { pipeline } from 'node:stream/promises';
import { createGzip } from 'node:zlib';
import { ENDPOINTS, JLP_MARKETS, STREAMS, backoffMs, changed, coinbaseDepth, coinbaseRows, coinbaseSubscription, feedMap, hourOf, hourStart, oracleSubscription,
  oracleTicks, parseCoinbaseProducts, parseFunding, parseGumMarkets, parsePool, parseYoloMarkets, relativePath, safeCoin } from './market-recorder.mjs';

export const STREAM_SILENCE_MS = 20_000;
export const WATCH_EVERY_MS = 10_000;
const STOP_GRACE_MS = 5000;
const FIRST_FUNDING_MS = 3000;
// The Coinbase product list is read once the Jupiter catalogs have named the coins, then now and then for new listings.
const FIRST_PRODUCTS_MS = 5000, PRODUCTS_EVERY_S = 600;
const DEPTH_EVERY_MS = 1000;
// Plain files whose compression failed are tried again this often, not only at the next start.
const SWEEP_EVERY_S = 3600;
// The hourly pass looks at the last days only. Every older folder was finished by the pass at the start.
const SWEEP_RECENT_MS = 2 * 86_400_000;
// A stream must stay up this long before its run of failures is forgotten: one that opens, answers and then fails is still failing.
export const STREAM_STEADY_MS = 30_000;
// A read that failed is tried again within this long at first, however rarely it is normally made.
const FIRST_RETRY_MS = 5000;
// The Coinbase product list is read again this soon while a Jupiter catalog has yet to name its coins, a few times at most.
const PRODUCTS_SOON_MS = 15_000, PRODUCTS_SOON_TRIES = 8;
const HOUR_MS = 3_600_000;
// A compressed hour of this recorder, by its own name. Only such a file is ever deleted, and only from a short-lived copy.
const COMPRESSED_HOUR = /^([A-Z0-9]{1,16})-([a-z0-9-]+)-(\d{8}T\d{2})\.jsonl\.gz$/;
// A lock written before this machine last started belongs to a process that is gone, whatever now has its number.
const BOOT_SLACK_S = 10;
export const bootedAt = () => Math.round(Date.now() / 1000 - uptime());
// Rows waiting in memory for a disk that has stopped taking them. Past this the run ends, before memory does.
const MAX_BUFFERED_BYTES = 64 * 2 ** 20;
// Another machine's recorder on the same folder is taken to be running while its status file is this fresh.
const FOREIGN_LOCK_FRESH_MS = 60_000;
const gone = () => Object.assign(new Error('The output folder is gone or is no longer the same disk.'), { code: 'ENODISK' });
const brief = error => String(error?.message ?? error).slice(0, 160);

/**
 * Ends the process when its event loop has stopped turning. A network disk that
 * hangs can block a file call for good; the recorder then looks alive and
 * records nothing, and only a kill lets the supervisor start a fresh one. The
 * watcher runs on its own thread and counts its own turns, not the wall clock,
 * so a machine waking from sleep is not mistaken for a hang.
 */
export function startWatchdog({ beatMs = 1000, checkMs = 5000, stalledChecks = 12 } = {}) {
  const beat = new Int32Array(new SharedArrayBuffer(4));
  const heart = setInterval(() => Atomics.add(beat, 0, 1), beatMs);
  heart.unref();
  // getBuiltinModule works whether the worker's source is read as a script or as a module.
  const worker = new Worker(`
    const { workerData } = process.getBuiltinModule('node:worker_threads');
    let last = -1, still = 0;
    setInterval(() => {
      const now = Atomics.load(workerData.beat, 0);
      if (now !== last) { last = now; still = 0; return; }
      if (++still >= workerData.stalledChecks) process.kill(process.pid, 'SIGKILL');
    }, workerData.checkMs);`, { eval: true, workerData: { beat, checkMs, stalledChecks } });
  // The watchdog is a safeguard: if it fails itself, the recorder carries on without it.
  worker.on('error', error => console.error(`The hang watchdog stopped (${String(error?.message ?? error).slice(0, 120)}). Recording continues.`));
  worker.unref();
  // The watcher needs a few turns of this thread's loop to start. `ready` resolves once it is watching (or has failed, or two seconds passed).
  const ready = new Promise(resolve => {
    const timer = setTimeout(resolve, 2000);
    const done = () => { clearTimeout(timer); resolve(); };
    worker.once('online', done); worker.once('error', done);
  });
  return { ready, stop: () => { clearInterval(heart); void worker.terminate(); } };
}

/** Whether a file that is about to be appended to ends in the middle of a line (a crash cut its last row). */
export function endsMidLine(path) {
  let size;
  try { size = statSync(path).size; } catch { return false; }
  if (!size) return false;
  const fd = openSync(path, 'r'), last = Buffer.alloc(1);
  try { readSync(fd, last, 0, 1, size - 1); } finally { closeSync(fd); }
  return last[0] !== 0x0a;
}

export class Recorder {
  #options; #fetchJson; #WebSocket; #now; #setTimer; #clearTimer; #exit; #log;
  #meta; #device; #startedMs; #endMs; #openFile;
  #open = new Map(); #closing = new Set(); #events = null;
  #counts = Object.fromEntries(STREAMS.map(stream => [stream, 0]));
  #lastRow = Object.fromEntries(STREAMS.map(stream => [stream, null]));
  #failures = {}; #lastOk = {}; #coins = new Set();
  #lastSnapshot = new Map(); #lastTick = new Map();
  #feeds = new Map(); #lastTickMs = 0; #oracle; #coinbase;
  #book = { products: new Map(), books: new Map(), tops: new Map(), trades: new Map() };
  #perpsCoins = [];
  #clockMs = 0; #timers = new Set(); #compressing = Promise.resolve(); #compressFailed = 0;
  #stopping = false; #exitCode = 0; #locked = false; #replacedLock = null; #maxBuffered;
  #fullSweepDue = true; #productsSoon = 0; #dropped = 0;

  /**
   * @param {object} deps
   *   options: parseArgs() result; fetchJson(url) -> parsed JSON; WebSocket: a WebSocket class;
   *   now() -> ms; setTimer(fn, ms) -> handle; clearTimer(handle); exit(code); log(text);
   *   openFile(path) -> a writable stream that appends to the file (a test can hold one open).
   */
  constructor({ options, fetchJson, WebSocket: Socket, now = Date.now, setTimer = setTimeout, clearTimer = clearTimeout, exit = code => process.exit(code), log = () => {},
    maxBufferedBytes = MAX_BUFFERED_BYTES, openFile = path => createWriteStream(path, { flags: 'a' }) }) {
    this.#openFile = openFile;
    this.#options = options; this.#fetchJson = fetchJson; this.#WebSocket = Socket; this.#now = now; this.#maxBuffered = maxBufferedBytes;
    this.#setTimer = setTimer; this.#clearTimer = clearTimer; this.#exit = exit; this.#log = log;
    this.#meta = join(options.out, '_recorder');
    this.#startedMs = now();
    this.#endMs = options.minutes > 0 ? this.#startedMs + options.minutes * 60_000 : Infinity;
    this.#oracle = this.#link('oracle', ENDPOINTS.oracleStream, () => this.#feeds.size ? oracleSubscription(this.#feeds.keys()) : null,
      (frame, now) => this.#oracleFrame(frame, now));
    this.#coinbase = this.#link('coinbase', ENDPOINTS.coinbaseStream, () => this.#book.products.size ? coinbaseSubscription(this.#book.products.keys()) : null,
      (frame, now) => this.#coinbaseFrame(frame, now),
      // A new connection starts from a new snapshot: the old book may have missed changes.
      () => { this.#book.books.clear(); this.#book.tops.clear(); });
  }

  get stopping() { return this.#stopping; }
  get exitCode() { return this.#exitCode; }
  /** Resolves when every file closed so far has been compressed. For tests and for a clean stop. */
  get compressed() { return this.#compressing; }

  /* ---------------------------------------------------------------- disk -- */

  /** The folder is still there and still the disk the run started on. A missing network disk must never be written around. */
  #diskPresent() {
    try { return statSync(this.#options.out).dev === this.#device; } catch { return false; }
  }

  /** A disk that stops taking writes ends the run: a supervisor restarts it once the disk is back. */
  #diskFailed(error) {
    if (this.#stopping) return;
    this.#log(`Write failed (${error?.code ?? brief(error)}). Stopping.`);
    this.#exitCode = 1;
    void this.stop('disk');
  }

  #note(type, detail = {}) {
    if (!this.#events || this.#events.destroyed) return;
    this.#events.write(JSON.stringify({ at: new Date(this.#now()).toISOString(), type, ...detail }) + '\n');
  }

  /** The clock as the files see it: it never runs backwards, so a step in system time cannot reopen an hour that was closed. */
  #clock() {
    this.#clockMs = Math.max(this.#clockMs, this.#now());
    return this.#clockMs;
  }

  /**
   * Compress a finished hour's file and remove the plain one, one file at a
   * time. The order is what keeps a crash from doubling an hour: the compressed
   * copy is completed under a `.ready` name, the plain file is removed, and only
   * then is the copy published. Whatever a crash leaves, `#finish` and the sweep
   * can tell apart: a plain file means "not compressed yet", a `.ready` file
   * without one means "compressed, not yet published".
   */
  #compress(path) {
    if (!this.#options.gzip) return this.#compressing;
    this.#compressing = this.#compressing.then(async () => {
      if (!existsSync(path) || !this.#diskPresent()) return;
      const partial = `${path}.gz.tmp`, ready = `${path}.gz.ready`;
      try {
        // A `.ready` beside a plain file is from a run that died before removing the plain one: start over from the plain file.
        if (existsSync(ready)) unlinkSync(ready);
        await pipeline(createReadStream(path), createGzip({ level: 9 }), createWriteStream(partial));
        renameSync(partial, ready);
        unlinkSync(path);
        this.#publish(path);
      } catch (error) {
        this.#compressFailed += 1;
        this.#note('compress-failed', { path, reason: brief(error) });
        try { unlinkSync(partial); } catch { /* nothing partial to remove */ }
      }
    });
    return this.#compressing;
  }

  /**
   * Publish a finished `.ready` copy as the hour's `.gz`. If that hour already
   * has one (a restart, or the hour was reopened), the two are joined: gzip
   * members one after the other read as one file. The joined file is built
   * beside the old one and put in its place in one step, so a crash leaves
   * either the old file with its `.ready` still to add, or the joined one.
   */
  #publish(path) {
    const ready = `${path}.gz.ready`, merge = `${path}.gz.merge`, target = `${path}.gz`;
    if (!existsSync(target)) return renameSync(ready, target);
    writeFileSync(merge, Buffer.concat([readFileSync(target), readFileSync(ready)]));
    unlinkSync(ready);
    renameSync(merge, target);
  }

  /**
   * What a run that ended in the middle of publishing left behind. A `.merge`
   * beside its `.ready` may be half written and is made again; one without is
   * complete and only needs its name. A `.ready` whose plain file is gone is
   * compressed and not yet published.
   */
  #finish(path) {
    this.#compressing = this.#compressing.then(() => {
      const ready = `${path}.gz.ready`, merge = `${path}.gz.merge`;
      try {
        if (!this.#diskPresent()) return;
        if (existsSync(merge)) { if (existsSync(ready)) unlinkSync(merge); else renameSync(merge, `${path}.gz`); }
        if (!existsSync(path) && existsSync(ready)) this.#publish(path);
      } catch (error) { this.#compressFailed += 1; this.#note('compress-failed', { path, reason: brief(error) }); }
    });
    return this.#compressing;
  }

  #close(key) {
    const file = this.#open.get(key);
    if (!file) return;
    this.#open.delete(key);
    // A polled stream's next file starts with a full row, so each of its files can be read on its own.
    this.#lastSnapshot.delete(key);
    // Until the last rows are on disk the file is not a leftover: the sweep must not compress a part of it.
    this.#closing.add(file.path);
    file.handle.end(() => { this.#closing.delete(file.path); void this.#compress(file.path); });
  }

  /** Append one row to the coin's file for this stream and hour. Returns false when it could not be written. */
  #write(coin, stream, row) {
    if (this.#stopping) return false;
    const nowMs = this.#clock(), key = `${coin}/${stream}`, { hour } = hourOf(nowMs);
    try {
      let file = this.#open.get(key);
      if (file && file.hour !== hour) { this.#close(key); file = null; }
      if (!file) {
        if (!this.#diskPresent()) throw gone();
        const path = join(this.#options.out, relativePath(coin, stream, nowMs));
        mkdirSync(dirname(path), { recursive: true });
        // A finished copy of this hour that was never published (a crash, then a clock set back into the same hour)
        // is published before the hour gets a new plain file: beside one, it would be taken for a stale duplicate.
        if (this.#options.gzip && existsSync(`${path}.gz.ready`) && !existsSync(path)) this.#publish(path);
        const torn = endsMidLine(path);
        const handle = this.#openFile(path);
        handle.on('error', error => this.#diskFailed(error));
        // A row cut off by a crash stays one bad line: the next row must not be glued onto it.
        if (torn) handle.write('\n');
        file = { hour, path, handle };
        this.#open.set(key, file);
      }
      file.handle.write(JSON.stringify(row) + '\n');
    } catch (error) { this.#diskFailed(error); return false; }
    this.#counts[stream] += 1;
    this.#lastRow[stream] = nowMs;
    this.#coins.add(coin);
    return true;
  }

  /** Write a polled snapshot only when it differs from the last one written for that coin and stream. */
  #snapshot(coin, stream, fields) {
    const key = `${coin}/${stream}`, row = { r: this.#now(), ...fields };
    // A file about to roll over gets its row regardless, so the new hour opens with the current state.
    const rolling = this.#open.get(key) && this.#open.get(key).hour !== hourOf(this.#clock()).hour;
    if (!rolling && !changed(this.#lastSnapshot.get(key), row)) return;
    if (this.#write(coin, stream, row)) this.#lastSnapshot.set(key, row);
  }

  /**
   * Plain files left by an earlier run, for hours that are over, are compressed,
   * and a publish a crash cut short is completed. A file this run has open, or is
   * still closing, is never touched. The folders are read without blocking: on a
   * network disk a listing can take seconds, and the streams must keep being read.
   * A folder that cannot be read is passed over and noted, and the others are
   * still swept. Returns whether every folder could be read.
   *
   * In a short-lived copy (--keep-hours) the same pass deletes compressed hours
   * that ended longer ago than that, and nothing else.
   */
  async sweep({ full = true } = {}) {
    const out = this.#options.out, keepMs = this.#standby ? this.#options.keepHours * HOUR_MS : 0;
    const since = full ? '' : new Date(this.#clock() - SWEEP_RECENT_MS).toISOString().slice(0, 10);
    let unread = 0, why = null;
    const list = async folder => {
      try { return await readdir(folder, { withFileTypes: true }); }
      catch (error) {
        if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') { unread += 1; why = error; }
        return [];
      }
    };
    for (const coin of await list(out)) {
      if (!coin.isDirectory() || !safeCoin(coin.name)) continue;
      for (const stream of STREAMS) {
        for (const day of await list(join(out, coin.name, stream))) {
          if (!day.isDirectory() || day.name < since) continue;
          const folder = join(out, coin.name, stream, day.name);
          const names = (await list(folder)).map(entry => entry.name);
          let left = names.length;
          for (const name of names) {
            if (this.#stopping) return false;
            const leftover = ['.gz.ready', '.gz.merge'].find(suffix => name.endsWith(`.jsonl${suffix}`));
            if (leftover) { await this.#finish(join(folder, name.slice(0, -leftover.length))); continue; }
            const path = join(folder, name);
            if (keepMs && this.#expired(name, coin.name, stream, keepMs)) {
              try { unlinkSync(path); this.#dropped += 1; left -= 1; } catch (error) { this.#note('drop-failed', { path, reason: brief(error) }); }
              continue;
            }
            if (!name.endsWith('.jsonl')) continue;
            const busy = this.#closing.has(path) || [...this.#open.values()].some(file => file.path === path);
            if (!busy && !name.endsWith(`${hourOf(this.#clock()).hour}.jsonl`)) await this.#compress(path);
          }
          // A day with nothing left in it is removed; a folder that is not empty refuses, and stays.
          if (keepMs && left === 0 && names.length) { try { rmdirSync(folder); } catch { /* something was written there meanwhile */ } }
        }
      }
    }
    if (unread) this.#note('sweep-skipped', { folders: unread, reason: brief(why) });
    return unread === 0;
  }

  /** Whether a file is a compressed hour of this coin and stream that ended longer ago than a short-lived copy keeps. */
  #expired(name, coin, stream, keepMs) {
    const m = COMPRESSED_HOUR.exec(name);
    return Boolean(m) && m[1] === coin && m[2] === stream && hourStart(m[3]) + HOUR_MS + keepMs < this.#clock();
  }

  /** Whether this folder is a short-lived copy: one a recorder started with --keep-hours has marked. */
  get #standby() { return this.#options.keepHours > 0; }

  status() {
    const iso = ms => ms ? new Date(ms).toISOString() : null;
    return { startedAt: iso(this.#startedMs), updatedAt: iso(this.#now()), out: this.#options.out, coins: [...this.#coins].sort(), rows: { ...this.#counts },
      lastRowAt: Object.fromEntries(Object.entries(this.#lastRow).map(([stream, ms]) => [stream, iso(ms)])),
      // A reader that last succeeded long ago is stuck, whatever the market is doing.
      lastReadOkAt: Object.fromEntries(Object.entries(this.#lastOk).map(([name, ms]) => [name, iso(ms)])),
      failuresInARow: { ...this.#failures },
      oracle: { connected: this.#oracle.open, feeds: this.#feeds.size, lastFrameAt: iso(this.#oracle.lastFrameMs), lastNewTickAt: iso(this.#lastTickMs) },
      coinbase: { connected: this.#coinbase.open, products: [...this.#book.products.keys()].sort(), lastFrameAt: iso(this.#coinbase.lastFrameMs),
        booksInStep: this.#book.books.size },
      openFiles: this.#open.size,
      // Rows written to a file's buffer and not yet taken by the disk. A number that keeps growing is a disk that has stalled.
      bufferedBytes: this.#buffered(), compressFailed: this.#compressFailed,
      // A short-lived copy: how many hours it keeps, and how many hour files it has deleted in this run.
      ...(this.#standby ? { keepHours: this.#options.keepHours, hourFilesDropped: this.#dropped } : {}) };
  }

  #buffered() {
    let bytes = 0;
    for (const file of this.#open.values()) bytes += file.handle.writableLength;
    return bytes;
  }

  #writeStatus() {
    if (!this.#diskPresent()) return this.#diskFailed(gone());
    if (this.#buffered() > this.#maxBuffered) return this.#diskFailed(Object.assign(new Error('The disk has stopped taking rows.'), { code: 'EBACKLOG' }));
    try {
      writeFileSync(join(this.#meta, 'status.json.tmp'), JSON.stringify(this.status(), null, 1) + '\n');
      renameSync(join(this.#meta, 'status.json.tmp'), join(this.#meta, 'status.json'));
    } catch (error) { this.#diskFailed(error); }
  }

  /* ------------------------------------------------------------- network -- */

  #later(fn, ms) {
    const handle = this.#setTimer(() => { this.#timers.delete(handle); fn(); }, ms);
    this.#timers.add(handle);
    return handle;
  }

  /**
   * Run `task` every `seconds`, first after `firstMs`. One failing read never stops
   * the others. After a failure the next try comes sooner than a long interval would
   * bring it, then more and more slowly, up to a minute. A task may return a number
   * of milliseconds to be run again sooner than its interval.
   */
  #every(name, seconds, task, firstMs = 0) {
    this.#failures[name] = 0; this.#lastOk[name] = null;
    const run = async () => {
      if (this.#stopping) return;
      let wait = seconds * 1000;
      try {
        const sooner = await task();
        this.#failures[name] = 0; this.#lastOk[name] = this.#now();
        // Never sooner than a failed read would be tried again: a task cannot ask for a tight loop.
        if (Number.isFinite(sooner)) wait = Math.min(wait, Math.max(sooner, FIRST_RETRY_MS));
      }
      catch (error) {
        this.#failures[name] += 1;
        if (this.#failures[name] === 1 || this.#failures[name] % 20 === 0) this.#note('read-failed', { name, failures: this.#failures[name], reason: brief(error) });
        wait = Math.max(Math.min(wait, FIRST_RETRY_MS), backoffMs(this.#failures[name]));
      }
      if (!this.#stopping) this.#later(run, wait);
    };
    if (firstMs > 0) this.#later(run, firstMs); else void run();
  }

  /** One read per coin; a coin whose read fails is skipped, and the read fails as a whole only when every coin did. */
  async #perCoin(coins, read) {
    let failed = 0, last = null;
    for (const coin of coins) {
      if (this.#stopping) return;
      try { await read(coin); } catch (error) { failed += 1; last = error; }
    }
    if (coins.length && failed === coins.length) throw last;
    if (failed) this.#note('coins-skipped', { failed, of: coins.length, reason: brief(last) });
  }

  /**
   * One stream: a socket that is opened when there is something to subscribe to,
   * retried one attempt at a time with a growing wait, and replaced when it goes
   * silent. `subscription()` gives the message to send on opening, or null when
   * there is nothing to ask for yet.
   */
  #link(name, url, subscription, onFrame, onOpen = () => {}) {
    const link = { name, socket: null, open: false, failures: 0, lastFrameMs: 0, upSince: null, timer: null };
    link.connect = () => {
      // One socket at a time: a retry that is already waiting, or a live socket, is left to do its work.
      if (this.#stopping || link.socket || link.timer || !subscription()) return;
      const mine = new this.#WebSocket(url);
      link.socket = mine; link.open = false; link.upSince = null;
      link.lastFrameMs = this.#now();
      onOpen();
      mine.onopen = () => {
        if (link.socket !== mine) return;
        link.open = true;
        const message = subscription();
        if (message) mine.send(JSON.stringify(message));
        this.#note('stream-open', { name });
      };
      mine.onmessage = event => {
        if (link.socket !== mine) return;
        let frame;
        try { frame = JSON.parse(event.data); } catch { return; }
        const now = this.#now();
        // Any frame shows the stream is alive, even one that repeats the last tick.
        link.lastFrameMs = now;
        // A run of failures ends only once usable frames have kept coming for a while: a stream that opens, answers and then
        // sends something that cannot be used, every time, must still be retried more and more slowly.
        try {
          onFrame(frame, now);
          link.upSince ??= now;
          if (now - link.upSince >= STREAM_STEADY_MS) link.failures = 0;
        } catch (error) { link.restart(brief(error), false); }
      };
      const lost = () => {
        mine.onclose = mine.onerror = null;
        if (link.socket !== mine || this.#stopping) return;
        link.socket = null; link.open = false; link.failures += 1;
        if (link.failures === 1 || link.failures % 20 === 0) this.#note('stream-lost', { name, failures: link.failures });
        link.timer = this.#later(() => { link.timer = null; link.connect(); }, backoffMs(link.failures));
      };
      mine.onclose = mine.onerror = lost;
    };
    link.close = () => {
      const old = link.socket;
      link.socket = null; link.open = false;
      if (old) { old.onclose = old.onerror = old.onmessage = null; try { old.close(); } catch { /* already closed */ } }
    };
    // `atOnce` is for a restart we chose (a new list to subscribe to). Any other is a failure and waits its turn.
    link.restart = (reason, atOnce = false) => {
      link.close();
      if (atOnce) { this.#note('stream-restart', { name, reason }); return link.connect(); }
      link.failures += 1;
      if (link.failures === 1 || link.failures % 20 === 0) this.#note('stream-restart', { name, reason, failures: link.failures });
      if (!link.timer) link.timer = this.#later(() => { link.timer = null; link.connect(); }, backoffMs(link.failures));
    };
    return link;
  }

  #oracleFrame(frame, now) {
    for (const tick of oracleTicks(frame, this.#feeds, now)) {
      if (this.#lastTick.get(tick.coin) === tick.key) continue;
      this.#lastTick.set(tick.coin, tick.key);
      if (this.#write(tick.coin, 'oracle', tick.row)) this.#lastTickMs = now;
    }
  }

  #coinbaseFrame(frame, now) {
    for (const { coin, stream, row } of coinbaseRows(frame, this.#book, now)) this.#write(coin, stream, row);
  }

  /** Once a second: how much size rests near the middle of each Coinbase book. Written when it changed. */
  #sampleDepth() {
    for (const { coin, row } of coinbaseDepth(this.#book, this.#now())) this.#snapshot(coin, 'coinbase-depth', row);
  }

  /** Which of the recorded coins Coinbase lists. A changed list starts the stream again with the new products. */
  async #readProducts() {
    const coins = new Set([...this.#perpsCoins, ...this.#feeds.values(), ...Object.keys(JLP_MARKETS)]);
    const products = parseCoinbaseProducts(await this.#fetchJson(ENDPOINTS.coinbaseProducts), coins);
    const next = new Map(products.map(row => [row.product, row.coin]));
    const same = next.size === this.#book.products.size && [...next].every(([product, coin]) => this.#book.products.get(product) === coin);
    this.#book.products = next;
    if (!same && this.#coinbase.socket) this.#coinbase.restart('the product list changed', true); else this.#coinbase.connect();
    // Until both Jupiter catalogs have answered, the coin list is short: look again soon, not in ten minutes.
    // Only a few times: a catalog that stays down must not have the whole product list fetched every few seconds.
    const short = this.#lastOk['perps-book'] === null || this.#lastOk['1000x-market'] === null;
    if (!short) this.#productsSoon = 0;
    return short && ++this.#productsSoon <= PRODUCTS_SOON_TRIES ? PRODUCTS_SOON_MS : undefined;
  }

  async #readCatalog() {
    const markets = parseYoloMarkets(await this.#fetchJson(ENDPOINTS.yoloMarkets));
    for (const market of markets) {
      this.#snapshot(market.coin, '1000x-market', { closed: market.closed, closeOnly: market.closeOnly, longOi: market.longOi, shortOi: market.shortOi,
        volume24h: market.volume24h, totalVolume: market.totalVolume });
    }
    const next = feedMap(markets), same = next.size === this.#feeds.size && [...next].every(([id, coin]) => this.#feeds.get(id) === coin);
    this.#feeds = next;
    if (!same && this.#oracle.socket) this.#oracle.restart('the market list changed', true); else this.#oracle.connect();
  }

  async #readBook() {
    const markets = parseGumMarkets(await this.#fetchJson(ENDPOINTS.gumMarkets));
    this.#perpsCoins = markets.map(market => market.coin);
    for (const { coin, ...fields } of markets) this.#snapshot(coin, 'perps-book', fields);
  }

  #readFunding() {
    return this.#perCoin(this.#perpsCoins, async coin => {
      const row = parseFunding(coin, await this.#fetchJson(ENDPOINTS.gumFunding + encodeURIComponent(coin)));
      if (row) this.#snapshot(coin, 'perps-funding', row);
    });
  }

  #readPools() {
    return this.#perCoin(Object.keys(JLP_MARKETS), async coin => {
      const row = parsePool(await this.#fetchJson(ENDPOINTS.poolInfo + JLP_MARKETS[coin].mint));
      if (row) this.#snapshot(coin, 'perps-pool', row);
    });
  }

  /* ---------------------------------------------------------------- loop -- */

  /** One look every ten seconds: the time limit, files whose hour is over, a silent stream, the status file. */
  watch() {
    if (this.#stopping) return;
    const now = this.#clock();
    if (now >= this.#endMs) return void this.stop('time');
    const { hour } = hourOf(now);
    // A stream that went quiet is closed and compressed when its hour ends, not when its next row arrives.
    for (const [key, file] of [...this.#open]) if (file.hour !== hour) this.#close(key);
    // A stream that is open but sends nothing is replaced: the venue can stop sending without closing.
    for (const link of [this.#oracle, this.#coinbase]) {
      if (link.socket && now - link.lastFrameMs > STREAM_SILENCE_MS) link.restart(`no frame for ${STREAM_SILENCE_MS / 1000} seconds`, true);
    }
    this.#writeStatus();
  }

  /**
   * One recorder per folder: two would write every row twice. The lock names the
   * process and the machine. A lock left by a process that is gone is replaced;
   * one held by another machine counts as live while that machine's status file
   * is fresh, since its process cannot be asked.
   */
  #lock() {
    const path = join(this.#meta, 'lock');
    const mine = JSON.stringify({ pid: process.pid, host: hostname(), boot: bootedAt(), startedAt: new Date(this.#now()).toISOString() });
    for (let attempt = 0; attempt < 2; attempt++) {
      try { writeFileSync(path, mine, { flag: 'wx' }); this.#locked = true; return; }
      catch (error) { if (error.code !== 'EEXIST') throw error; }
      let holder = null;
      try { holder = JSON.parse(readFileSync(path, 'utf8')); } catch { /* an unreadable lock is a stale one */ }
      let live = false;
      if (holder?.host === hostname()) {
        // A process number is reused: after a restart of the machine another program can hold the dead recorder's.
        // And 0 or a negative number would ask about a whole group of processes, not one.
        const sameBoot = !Number.isFinite(holder.boot) || Math.abs(holder.boot - bootedAt()) <= BOOT_SLACK_S;
        if (sameBoot && Number.isSafeInteger(holder.pid) && holder.pid > 1) {
          try { process.kill(holder.pid, 0); live = holder.pid !== process.pid; } catch (error) { live = error.code === 'EPERM'; }
        }
      } else if (holder) {
        try { live = Date.now() - statSync(join(this.#meta, 'status.json')).mtimeMs < FOREIGN_LOCK_FRESH_MS; } catch { live = false; }
      }
      if (live) throw Object.assign(new Error(`Another recorder is already writing to this folder (process ${holder.pid} on ${holder.host}).`), { code: 'ELOCKED' });
      // Noted once the events file is open (start() does that next).
      this.#replacedLock = holder ? { pid: holder.pid ?? null, host: holder.host ?? null } : { unreadable: true };
      unlinkSync(path);
    }
    throw Object.assign(new Error('The recorder lock could not be taken.'), { code: 'ELOCKED' });
  }

  /**
   * A short-lived copy deletes old hours, so it may never be an archive by
   * mistake. --keep-hours starts only in a folder that holds no recording yet,
   * which it marks, or in one already marked; and a marked folder does not start
   * without --keep-hours, so it cannot quietly turn into a second archive that the
   * fill tool would still read as a copy.
   */
  #checkStandby() {
    const marker = join(this.#meta, 'standby'), marked = existsSync(marker);
    if (!this.#standby) {
      if (marked) throw Object.assign(new Error('This folder is a short-lived copy (it was started with --keep-hours). Start it with --keep-hours again.'), { code: 'ESTANDBY' });
      return;
    }
    if (marked) return;
    const recorded = readdirSync(this.#options.out, { withFileTypes: true }).some(entry => entry.isDirectory() && safeCoin(entry.name));
    if (recorded) {
      throw Object.assign(new Error('--keep-hours deletes old hours, and this folder already holds a recording. Start a short-lived copy in an empty folder.'),
        { code: 'ESTANDBY' });
    }
    writeFileSync(marker, JSON.stringify({ host: hostname(), keepHours: this.#options.keepHours, since: new Date(this.#now()).toISOString() }) + '\n');
  }

  start() {
    const { out } = this.#options;
    this.#device = statSync(out).dev;
    mkdirSync(this.#meta, { recursive: true });
    this.#lock();
    try { this.#checkStandby(); }
    catch (error) { try { unlinkSync(join(this.#meta, 'lock')); } catch { /* nothing to release */ } this.#locked = false; throw error; }
    this.#events = createWriteStream(join(this.#meta, 'events.jsonl'), { flags: 'a' });
    this.#events.on('error', error => this.#diskFailed(error));
    this.#note('started', { out, minutes: this.#options.minutes, bookEvery: this.#options.bookEvery, keepHours: this.#options.keepHours });
    if (this.#replacedLock) this.#note('lock-replaced', { holder: this.#replacedLock });
    // Every folder once, at the start; after that only the last days, once an hour. A pass that could not
    // read some folder is not that once: the next one looks at everything again.
    this.#every('sweep', SWEEP_EVERY_S, async () => { if (await this.sweep({ full: this.#fullSweepDue })) this.#fullSweepDue = false; });
    this.#every('1000x-market', this.#options.catalogEvery, () => this.#readCatalog());
    this.#every('perps-book', this.#options.bookEvery, () => this.#readBook());
    // Funding is read per coin, and the coins come from the book's first read.
    this.#every('perps-funding', this.#options.fundingEvery, () => this.#readFunding(), FIRST_FUNDING_MS);
    this.#every('perps-pool', this.#options.poolEvery, () => this.#readPools());
    this.#every('coinbase-products', PRODUCTS_EVERY_S, () => this.#readProducts(), FIRST_PRODUCTS_MS);
    const depth = () => { this.#sampleDepth(); if (!this.#stopping) this.#later(depth, DEPTH_EVERY_MS); };
    this.#later(depth, DEPTH_EVERY_MS);
    const tick = () => { this.watch(); if (!this.#stopping) this.#later(tick, WATCH_EVERY_MS); };
    this.#later(tick, WATCH_EVERY_MS);
  }

  /** A fault nobody caught: say so and end the run, so the supervisor starts a clean one. */
  fault(error) {
    this.#note('fault', { reason: brief(error) });
    this.#log(`Unexpected fault (${brief(error)}). Stopping.`);
    this.#exitCode = this.#exitCode || 1;
    void this.stop('fault');
  }

  async stop(reason) {
    if (this.#stopping) return;
    this.#stopping = true;
    // Armed first: a disk that has gone away may never call back, and the run must still end.
    const grace = setTimeout(() => this.#exit(this.#exitCode || 1), STOP_GRACE_MS);
    grace.unref?.();
    for (const handle of this.#timers) this.#clearTimer(handle);
    this.#timers.clear();
    this.#oracle.close(); this.#coinbase.close();
    this.#note('stopped', { reason, rows: this.#counts });
    const closing = [...this.#open.values()];
    this.#open.clear();
    await Promise.all(closing.map(file => new Promise(resolve => file.handle.end(resolve))));
    if (this.#exitCode === 0) {
      try {
        writeFileSync(join(this.#meta, 'status.json.tmp'), JSON.stringify({ ...this.status(), stoppedAt: new Date(this.#now()).toISOString(), reason }, null, 1) + '\n');
        renameSync(join(this.#meta, 'status.json.tmp'), join(this.#meta, 'status.json'));
      } catch { /* the run is ending */ }
    }
    if (this.#locked) { try { unlinkSync(join(this.#meta, 'lock')); } catch { /* the folder may be gone */ } }
    await new Promise(resolve => this.#events ? this.#events.end(resolve) : resolve());
    clearTimeout(grace);
    this.#exit(this.#exitCode);
  }
}
