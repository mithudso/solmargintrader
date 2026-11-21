import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { chmodSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const { DatabaseSync } = await import('node:sqlite').catch(error => {
  if (error.code !== 'ERR_UNKNOWN_BUILTIN_MODULE') throw error;
  return {};
});
const worker = fileURLToPath(new URL('../tools/zec-volty-learning.mjs', import.meta.url));

test('Volty starts a fresh score history once and resumes it from the new tick cursor', { skip: !DatabaseSync }, t => {
  const dir = mkdtempSync(join(tmpdir(), 'volty-learning-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const ticksPath = join(dir, 'learning-ticks.sqlite3');
  const statusPath = join(dir, 'learning-status.json');
  const checkpointPath = join(dir, 'learning-checkpoint-v2.json');
  const legacyPath = join(dir, 'learning-checkpoint.json');
  const start = 1_790_000_000;
  const resetAt = start * 1000 + 900;
  const legacy = JSON.stringify({ ticks: 23000, model: { retired: true } });
  writeFileSync(legacyPath, legacy, { mode: 0o600 });
  writeFileSync(statusPath, JSON.stringify({ ticks: 23000, horizons: [{ candidate_brier: 0.85 }] }), { mode: 0o600 });

  const db = new DatabaseSync(ticksPath);
  t.after(() => db.close());
  chmodSync(ticksPath, 0o600);
  db.exec('CREATE TABLE ticks (mark_at INTEGER PRIMARY KEY, received_ms INTEGER NOT NULL, mark REAL NOT NULL)');
  const insert = db.prepare('INSERT INTO ticks VALUES (?, ?, ?)');
  insert.run(start, start * 1000 + 100, 800);
  insert.run(start + 1, resetAt - 50, 805);
  const snapshot = path => JSON.parse(readFileSync(path, 'utf8'));
  const run = (now, expectSuccess = true) => {
    const clock = encodeURIComponent(`Date.now = () => ${now};`);
    const child = spawnSync(process.execPath, [`--import=data:text/javascript,${clock}`, worker, '--state-dir', dir, '--once'],
      { encoding: 'utf8', timeout: 10_000 });
    assert.ifError(child.error);
    assert.equal(child.status, expectSuccess ? 0 : 1, child.stderr);
  };
  run(resetAt);
  const empty = snapshot(checkpointPath);
  assert.deepEqual(empty, { startedAtMs: resetAt, last: 0, ticks: 0, model: null });
  assert.deepEqual(snapshot(statusPath), { schema: 1, mode: 'shadow', state: 'waiting',
    updated_at: start, last_tick_at: null, ticks: 0, horizons: [] });

  for (let offset = 2; offset <= 32; offset += 5) insert.run(start + offset, (start + offset) * 1000, 700 + offset);
  run((start + 32) * 1000);
  let status = snapshot(statusPath);
  assert.equal(status.state, 'warming');
  assert.equal(status.ticks, 7);
  assert.equal(status.horizons.length, 6);
  assert.equal(status.horizons[0].trained, 0);
  assert.equal(status.horizons[0].pending, 1);
  assert.equal(status.horizons[0].candidate_brier, null);

  const last = start + 1_652;
  for (let markAt = start + 37; markAt <= last; markAt += 5) {
    insert.run(markAt, markAt * 1000, 700 + ((markAt - start) % 251));
  }
  run(last * 1000);
  const resumed = snapshot(checkpointPath);
  status = snapshot(statusPath);
  assert.equal(resumed.startedAtMs, empty.startedAtMs);
  assert.equal(resumed.last, last);
  assert.equal(resumed.ticks, 331);
  assert.equal(status.ticks, resumed.ticks);
  assert.equal(status.last_tick_at, last);
  assert.equal(status.state, 'learning');
  const minute = status.horizons[0];
  assert.equal(minute.trained, 27);
  assert.equal(minute.pending, 1);
  const metrics = resumed.model.metrics[60];
  const recent = metrics.recent.slice(-24);
  const meanBrier = field => recent.reduce((total, row) =>
    total + row[field].reduce((score, p, i) => score + (p - Number(i === row.y)) ** 2, 0), 0) / recent.length;
  assert.equal(minute.candidate_brier, meanBrier('p'));
  assert.equal(minute.frequency_brier, meanBrier('baseline'));
  assert.notEqual(minute.candidate_brier, metrics.candidate.brier / minute.trained);
  run(last * 1000);
  assert.deepEqual(snapshot(checkpointPath), resumed);
  assert.equal(readFileSync(legacyPath, 'utf8'), legacy);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM ticks').get().n, resumed.ticks + 2);

  db.prepare('UPDATE ticks SET mark = mark + 1 WHERE mark_at = ?').run(last);
  run(last * 1000, false);
  assert.equal(snapshot(statusPath).state, 'unavailable');
  assert.deepEqual(snapshot(statusPath).horizons, []);
  assert.deepEqual(snapshot(checkpointPath), resumed);
});
