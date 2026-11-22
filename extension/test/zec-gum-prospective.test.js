import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { practiceSignals } from '../src/perps/strategies.js';
import { openProspectiveJournal, paperSettings, ProspectiveSession, shortZScoreState } from '../tools/lib/zec-gum-prospective.mjs';

const start = 72000;
const terms = { venue: 'GUM', max: 25, baseBps: 3.5, maintenanceBps: 100, liquidationBps: 75, carryBps: 0,
  firstTierCap: 30000, maxOrder: 10000, minOrder: 5, maxQty: 100, stepSize: 0.001 };
const paperSource = { 'test-source.js': 'a'.repeat(64) };

const bar = (time, close) => ({ time, open: close, high: close + 0.05, low: close - 0.05, close });
const makeCandles = closingPrice => async (_market, from, to) => Array.from({ length: (to - from) / 60 }, (_, index) => {
  const time = from + 60 * index;
  return bar(time, closingPrice(time));
});

async function sample(session, time, price, candles = makeCandles(() => 100)) {
  return session.sample(undefined, { clock: () => time, candles,
    snapshot: async () => ({ mark: { time, price }, short: terms, long: terms }) });
}

const book = (event, id) => event.profiles.find(profile => profile.id === id);

test('rolling short Z-score retains the exact canonical reflected state when window slices advance', () => {
  const bars = Array.from({ length: 400 }, (_, i) => bar(300 * i, 400 + Math.sin(i / 3) * 4 + (i % 47 === 0 ? 80 : 0)));
  const reflected = bars.map(row => ({ ...row, close: -row.close }));
  const canonical = practiceSignals(reflected, { step: 300, members: [
    { strategy: 'zscore', params: { window: 12, entry_z: -2.5, exit_z: 0 } },
  ] });
  assert.ok(canonical.some(row => row?.weight === 1));
  let after = null;
  let weight = 0;
  for (let i = 0; i < bars.length; i += 1) {
    ({ weight } = shortZScoreState(bars.slice(Math.max(0, i - 24), i + 1), { after, weight }));
    assert.equal(weight, canonical[i]?.weight ?? 0, 'canonical state at candle ' + i);
    after = bars[i].time + 300;
  }
});

test('Z-score short enters a fresh edge, charges both slippage schedules and waits to reset after a stop', async () => {
  const prices = time => time < start ? 100 : time < start + 300 ? 130
    : time < start + 600 ? 126 : time < start + 900 ? 90 : 160;
  const candles = makeCandles(prices);
  const session = new ProspectiveSession(start);
  let event;
  for (let time = start + 10; time <= start + 1200 + 10; time += 25) {
    const mark = time === start + 335 ? 132.2 : prices(time - 15);
    event = await sample(session, time, mark, candles);
    if (time === start + 310) {
      const base = book(event, 'zscore-short').position;
      const stress = book(event, 'zscore-short-stress').position;
      assert.equal(base.direction, -1);
      assert.equal(stress.direction, -1);
      assert.ok(base.entry > stress.entry);
      assert.equal(base.stop, base.entry * 1.016);
      assert.equal(base.take, base.entry * 0.98);
      assert.ok(Math.abs(base.sizeUsd - paperSettings.amount) < 1);
    }
    if (time === start + 335) {
      assert.equal(book(event, 'zscore-short').newExits[0].reason, 'stop');
      assert.equal(book(event, 'zscore-short-stress').newExits[0].reason, 'stop');
    }
    if (time === start + 610) {
      assert.equal(book(event, 'zscore-short').position, null);
      assert.equal(book(event, 'zscore-short').decision.value.weight, 1);
      assert.equal(book(event, 'zscore-short').exits, 1);
    }
    if (time === start + 910) assert.equal(book(event, 'zscore-short').decision.value.weight, 0);
  }
  assert.equal(book(event, 'zscore-short').position?.direction, -1);
  assert.equal(book(event, 'cash').equity, 1000);
});

test('short-only Volty keeps the opposite breakout exit and suppresses the reverse long', async () => {
  const session = new ProspectiveSession(start);
  for (let time = start + 10; time <= start + 310; time += 25) await sample(session, time, 100);
  const breached = await sample(session, start + 335, 99.7);
  assert.equal(book(breached, 'volty-short').position?.direction, -1);
  const opposite = await sample(session, start + 360, 100.16);
  assert.equal(book(opposite, 'volty-short').newExits[0].reason, 'signal');
  assert.equal(book(opposite, 'volty-short').position, null);
  assert.equal(book(opposite, 'volty-short-stress').position, null);
});

test('warmup and quote gaps seed signals without opening stale paper entries', async () => {
  const activation = start + 300;
  const session = new ProspectiveSession(activation);
  const candles = makeCandles(time => time < start ? 100 : 130);
  const first = await sample(session, activation + 10, 130, candles);
  assert.equal(book(first, 'zscore-short').decision.value.weight, 1);
  assert.equal(book(first, 'zscore-short').position, null);
  assert.equal(book(first, 'volty-short').position, null);
  const gap = await sample(session, activation + 320, 120, candles);
  assert.equal(gap.quoteGap, true);
  assert.equal(book(gap, 'volty-short').decision.status, 'resync');
  assert.equal(book(gap, 'volty-short').position, null);
  assert.equal(book(gap, 'zscore-short').position, null);
});

test('paper journal retains one cohort and exact trades across restarts, with one writer', async t => {
  let DatabaseSync;
  try {
    ({ DatabaseSync } = await import('node:sqlite'));
  } catch (error) {
    if (error?.code !== 'ERR_UNKNOWN_BUILTIN_MODULE') throw error;
    t.skip('Prospective paper journaling needs Node with built-in SQLite.');
    return;
  }
  const path = await mkdtemp(join(tmpdir(), 'zec-gum-paper-fixture-'));
  t.after(() => rm(path, { recursive: true, force: true }));
  let journal = await openProspectiveJournal(path, 10, paperSource, { clock: () => start });
  assert.equal(journal.config.startedAt, start);
  try {
    await assert.rejects(openProspectiveJournal(path, 10, paperSource), /active writer/);
    for (let time = start + 10; time <= start + 310; time += 25) {
      journal.append(await sample(journal.session, time, 100));
    }
    const armed = await sample(journal.session, start + 335, 99.7);
    journal.append(armed);
    assert.equal(book(armed, 'volty-short').position.direction, -1);
  } finally {
    journal.close();
  }

  await assert.rejects(openProspectiveJournal(path, 10, { 'test-source.js': 'b'.repeat(64) }), /different rules/);
  journal = await openProspectiveJournal(path, 10, paperSource);
  try {
    assert.equal(journal.config.startedAt, start);
    assert.equal((await sample(journal.session, start + 335, 99.7)).type, 'feed-unavailable');
    const stopped = await sample(journal.session, start + 400, 101);
    assert.equal(stopped.quoteGap, true);
    assert.equal(book(stopped, 'volty-short').newExits[0].reason, 'stop');
    journal.append(stopped);
    assert.throws(() => journal.append(stopped), /advance|UNIQUE/);
    journal.append(await sample(journal.session, start + 410, 99.7));

    const reader = new DatabaseSync(join(path, 'cohort.sqlite3'), { readOnly: true });
    try {
      const events = reader.prepare('SELECT event FROM observations ORDER BY mark_at').all()
        .map(row => JSON.parse(row.event));
      assert.equal(events.length, 16);
      assert.equal(events.reduce((sum, event) => sum + book(event, 'volty-short').newExits.length, 0), 1);
      assert.equal(book(events.at(-1), 'volty-short').exits, 1);
      assert.equal(book(events.at(-1), 'volty-short').position, null);
    } finally {
      reader.close();
    }
  } finally {
    journal.close();
  }
  const mutator = new DatabaseSync(join(path, 'cohort.sqlite3'));
  try {
    assert.throws(() => mutator.exec('DELETE FROM observations'), /append-only/);
    assert.throws(() => mutator.exec('UPDATE cohort SET started_at = 1'), /immutable/);
  } finally {
    mutator.close();
  }
});
