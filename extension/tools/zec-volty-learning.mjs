/** Shadow consumer of the standalone Volty owner's durable GUM tick stream. */
import { constants, closeSync, fsyncSync, fstatSync, lstatSync, openSync, readFileSync,
  renameSync, unlinkSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { randomUUID } from 'node:crypto';
import { parseArgs } from 'node:util';
import { setTimeout as sleep } from 'node:timers/promises';
import { DatabaseSync } from 'node:sqlite';
import { LIVE_ORACLE, VOLTY_TICK_IDENTITY, liveIdentity, liveSnapshot, transitionLive,
  validateLiveState } from '../src/1000x/oracle-live-model.js';

const identity = VOLTY_TICK_IDENTITY;
const CHECKPOINT_BYTES = 12 * 1024 * 1024;
const CHECKPOINT_INTERVAL_MS = 60_000;
const POLL_MS = 2000;
const { values } = parseArgs({ options: { 'state-dir': { type: 'string' }, once: { type: 'boolean' } } });
const dir = resolve(values['state-dir'] ?? join(homedir(), '.soltui', 'zec-volty'));
const checkpointPath = join(dir, 'learning-checkpoint.json');
const statusPath = join(dir, 'learning-status.json');
const ticksPath = join(dir, 'learning-ticks.sqlite3');

function privatePath(stat, type) {
  if (!stat[type]() || stat.uid !== process.getuid() || (stat.mode & 0o077)) {
    throw new Error('volty_learning_private_path_required');
  }
}

function atomicWrite(path, value) {
  const temp = `${path}.${randomUUID()}.tmp`;
  try {
    const fd = openSync(temp, 'wx', 0o600);
    try {
      writeFileSync(fd, JSON.stringify(value));
      fsyncSync(fd);
    } finally { closeSync(fd); }
    renameSync(temp, path);
  } finally {
    try { unlinkSync(temp); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
}

function readCheckpoint() {
  let fd;
  try { fd = openSync(checkpointPath, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK); }
  catch (error) { if (error.code === 'ENOENT') return { last: 0, ticks: 0, model: null }; throw error; }
  try {
    const stat = fstatSync(fd);
    privatePath(stat, 'isFile');
    if (stat.size > CHECKPOINT_BYTES) throw new Error('volty_learning_checkpoint_too_large');
    const data = JSON.parse(readFileSync(fd, 'utf8'));
    validateLiveState(data.model, liveIdentity(identity));
    if (!Number.isSafeInteger(data.last) || data.last < 1 || !Number.isSafeInteger(data.ticks) || data.ticks < 1
      || data.model.lastQuote?.exchangeMs !== data.last * 1000) throw new Error('volty_learning_checkpoint_invalid');
    return data;
  } finally { closeSync(fd); }
}

function publish(data, failure = false) {
  const snapshot = data.model && liveSnapshot(data.model, Date.now());
  const horizons = snapshot ? LIVE_ORACLE.horizons.map(seconds => {
    const h = snapshot.horizons[seconds];
    return { seconds, trained: h.resolved, pending: h.pending, expired: h.expired, capacity_drops: h.capacityDrops,
      candidate_brier: h.resolved ? h.candidate.brier / h.resolved : null,
      frequency_brier: h.resolved ? h.frequency.brier / h.resolved : null };
  }) : [];
  atomicWrite(statusPath, { schema: 1, mode: 'shadow', state: failure ? 'unavailable' : snapshot?.status ?? 'waiting',
    updated_at: Math.floor(Date.now() / 1000), last_tick_at: data.last || null, ticks: data.ticks, horizons });
}

async function run() {
  privatePath(lstatSync(dir), 'isDirectory');
  const lockFile = join(dir, 'learning-owner.sqlite3');
  const lockFd = openSync(lockFile, constants.O_CREAT | constants.O_RDWR | constants.O_NOFOLLOW | constants.O_NONBLOCK, 0o600);
  try { privatePath(fstatSync(lockFd), 'isFile'); }
  finally { closeSync(lockFd); }
  const lock = new DatabaseSync(lockFile, { timeout: 0 });
  let ticksDb;
  let data = { last: 0, ticks: 0, model: null };
  let running = true;
  process.on('SIGINT', () => { running = false; });
  process.on('SIGTERM', () => { running = false; });
  try {
    // An OS-released SQLite lock fences the shadow checkpoint across restarts.
    lock.exec('BEGIN EXCLUSIVE');
  } catch (error) { lock.close(); throw error; }
  try {
    data = readCheckpoint();
    let saved = data.last, lastCheckpoint = 0, lastPublish = 0;
    while (running) {
      if (!ticksDb) {
        try {
          privatePath(lstatSync(ticksPath), 'isFile');
          ticksDb = new DatabaseSync(ticksPath, { readOnly: true, timeout: 1000 });
          if (data.last) {
            const anchor = ticksDb.prepare('SELECT received_ms, mark FROM ticks WHERE mark_at = ?').get(data.last);
            if (anchor?.received_ms !== data.model.lastQuote.receivedMs || anchor.mark !== data.model.lastQuote.price) {
              throw new Error('volty_learning_journal_anchor_changed');
            }
          }
        } catch (error) { if (error.code !== 'ENOENT') throw error; }
      }
      const rows = ticksDb?.prepare('SELECT mark_at, received_ms, mark FROM ticks WHERE mark_at > ? ORDER BY mark_at LIMIT 64').all(data.last) ?? [];
      for (const row of rows) {
        const nowMs = row.received_ms;
        const quote = { price: row.mark, exchangeMs: row.mark_at * 1000, receivedMs: nowMs };
        const next = transitionLive(data.model, { identity, quote, nowMs });
        if (!next.changed || next.state.lastQuote?.exchangeMs !== quote.exchangeMs) {
          throw new Error('volty_learning_invalid_recorded_tick');
        }
        data = { last: row.mark_at, ticks: data.ticks + 1, model: next.state };
      }
      const now = Date.now();
      if (data.last !== saved && (values.once || now - lastCheckpoint >= CHECKPOINT_INTERVAL_MS)) {
        atomicWrite(checkpointPath, data);
        saved = data.last;
        lastCheckpoint = now;
      }
      if (rows.length || now - lastPublish >= 5000) { publish(data); lastPublish = now; }
      if (values.once && rows.length < 64) break;
      if (rows.length < 64) await sleep(POLL_MS);
    }
    if (data.last !== saved) atomicWrite(checkpointPath, data);
  } catch (error) {
    publish(data, true);
    throw error;
  } finally {
    ticksDb?.close();
    lock.close();
  }
}

await run().catch(() => {
  console.error('Volty tick learner stopped. Check the private journal, checkpoint and owner lock.');
  process.exitCode = 1;
});
