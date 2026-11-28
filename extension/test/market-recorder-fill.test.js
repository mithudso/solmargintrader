import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, utimesSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync, gzipSync } from 'node:zlib';
import { STREAMS } from '../tools/lib/market-recorder.mjs';
import { EDGE_MS, FILL_USAGE, OUTAGE_MS, SETTLE_MS, VENUES, fill, hourStart, listHours, mergeLines, outages, parseFillArgs, planHour, readHourFile,
  replaceHourFile } from '../tools/lib/market-recorder-fill.mjs';

const TOOL = fileURLToPath(new URL('../tools/market-recorder-fill.mjs', import.meta.url));
const LIB = fileURLToPath(new URL('../tools/lib/market-recorder-fill.mjs', import.meta.url));
const HOUR = '20261128T10', START = hourStart(HOUR), HOUR_MS = 3_600_000, MIN = 60_000;
const LATER = START + HOUR_MS + SETTLE_MS + MIN;

/** Two recorder folders: an archive and a short-lived copy of a second machine's recording. */
function folders() {
  const root = mkdtempSync(join(tmpdir(), 'market-recorder-fill-'));
  const into = join(root, 'archive'), from = join(root, 'standby');
  mkdirSync(join(into, '_recorder'), { recursive: true });
  mkdirSync(join(from, '_recorder'), { recursive: true });
  writeFileSync(join(from, '_recorder', 'standby'), JSON.stringify({ host: '5080', keepHours: 3 }));
  const path = (folder, coin, stream, hour = HOUR, suffix = '.gz') =>
    join(folder, coin, stream, `${hour.slice(0, 4)}-${hour.slice(4, 6)}-${hour.slice(6, 8)}`, `${coin}-${stream}-${hour}.jsonl${suffix}`);
  const put = (folder, coin, stream, rows, hour = HOUR) => {
    const target = path(folder, coin, stream, hour);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, gzipSync(rows.map(row => typeof row === 'string' ? row : JSON.stringify(row)).join('\n') + '\n'));
    return target;
  };
  const rows = target => gunzipSync(readFileSync(target)).toString().split('\n').filter(Boolean).map(line => { try { return JSON.parse(line); } catch { return line; } });
  return { root, into, from, path, put, rows, cleanup: () => rmSync(root, { recursive: true, force: true }) };
}

/** Oracle ticks twice a second from `from` to `to` (ms into the hour), received `late` ms after they were made. */
const ticks = (coin, from, to, late = 0, hour = HOUR) => {
  const out = [], start = hourStart(hour);
  for (let t = from; t < to; t += 500) out.push({ a: coin, p: 100 + t / 1e6, e: start + t - 200, r: start + t + late });
  return out;
};
/** Coinbase book rows twice a second. */
const tops = (from, to, late = 0) => {
  const out = [];
  for (let t = from; t < to; t += 500) out.push({ bid: 1, ask: 2, bidSize: 1, askSize: 1, t: START + t - 50, r: START + t + late });
  return out;
};
const entries = rows => rows.map(row => ({ line: JSON.stringify(row), r: row.r, row }));

test('every stream belongs to exactly one venue', () => {
  assert.deepEqual(Object.values(VENUES).flat().sort(), [...STREAMS].sort());
  assert.match(FILL_USAGE, new RegExp(`more than\\s+${OUTAGE_MS / 1000} seconds`));
});

test('an hour name is read as UTC, and anything else is refused', () => {
  assert.equal(hourStart('20261128T10'), Date.UTC(2026, 10, 28, 10));
  for (const bad of ['2026112810', '20261128T1', '', '20261128T10.jsonl']) assert.throws(() => hourStart(bad), RangeError);
});

test('a stretch with no row for longer than the threshold is an outage, at the edges of the hour too', () => {
  const end = START + HOUR_MS;
  assert.deepEqual(outages([], START, end), [{ from: START, to: end, fromRow: false, toRow: false }]);
  const steady = []; for (let t = START; t < end; t += 10_000) steady.push(t);
  assert.deepEqual(outages(steady, START, end), [], 'ten seconds is not an outage');
  const holed = steady.filter(t => t < START + 20 * MIN || t >= START + 22 * MIN);
  assert.deepEqual(outages(holed, START, end), [{ from: START + 20 * MIN - 10_000, to: START + 22 * MIN, fromRow: true, toRow: true }]);
  const late = steady.filter(t => t >= START + MIN && t < START + 58 * MIN);
  assert.deepEqual(outages(late, START, end).map(w => [w.from - START, w.to - START, w.fromRow, w.toRow]),
    [[0, MIN, false, true], [58 * MIN - 10_000, HOUR_MS, true, false]]);
  // A row stamped just before the hour, or after it, does not hide or invent an outage.
  assert.equal(outages([START - 5, ...steady, end + 5], START, end).length, 0);
  assert.equal(outages([START + OUTAGE_MS, START + 2 * OUTAGE_MS + 1], START, START + 2 * OUTAGE_MS + 2).length, 1, 'exactly the threshold is not an outage; one more millisecond is');
});

test('rows are taken only from a stretch in which the archive recorded nothing from that venue', () => {
  // The archive lost Jupiter for two minutes and kept Coinbase throughout.
  const archive = new Map([
    ['BTC/oracle', entries(ticks('BTC', 0, HOUR_MS).filter(row => row.r < START + 20 * MIN || row.r >= START + 22 * MIN))],
    ['BTC/coinbase-book', entries(tops(0, HOUR_MS))],
    ['ZEC/perps-funding', entries([{ rateBps1h: 1, r: START + 5 }])],
  ]);
  const standby = new Map([
    ['BTC/oracle', entries(ticks('BTC', 0, HOUR_MS, 30))],
    ['BTC/coinbase-book', entries(tops(0, HOUR_MS, 30))],
    // One change inside the stretch and one outside it. Neither is in the archive, and only the first is its gap.
    ['ZEC/perps-funding', entries([{ rateBps1h: 1, r: START + 35 }, { rateBps1h: 2, r: START + 21 * MIN }, { rateBps1h: 3, r: START + 40 * MIN }])],
    // A stream the archive has no file for at all.
    ['ANT/perps-book', entries([{ bid: 9, r: START + 21 * MIN + 7 }, { bid: 8, r: START + 50 * MIN }])],
  ]);
  const plan = planHour(HOUR, archive, standby, '5080');
  assert.deepEqual(plan.windows.coinbase, []);
  assert.deepEqual(plan.windows.jupiter.map(w => [w.from - START, w.to - START]), [[20 * MIN - 500, 22 * MIN]]);
  assert.deepEqual([...plan.additions.keys()].sort(), ['ANT/perps-book', 'BTC/oracle', 'ZEC/perps-funding']);
  const added = plan.additions.get('BTC/oracle').map(entry => JSON.parse(entry.line));
  // Kept a second away from the rows that bound the stretch: 20:00.530 to 21:58.530.
  assert.equal(added.length, 237);
  assert.deepEqual([added[0].r - START, added.at(-1).r - START], [20 * MIN + 530, 22 * MIN - 1470]);
  assert.equal(added.every(row => row.h === '5080' && row.r - START >= 20 * MIN - 500 + EDGE_MS && row.r - START < 22 * MIN - EDGE_MS), true);
  assert.deepEqual(plan.additions.get('ZEC/perps-funding').map(entry => JSON.parse(entry.line).rateBps1h), [2]);
  assert.deepEqual(plan.additions.get('ANT/perps-book').map(entry => JSON.parse(entry.line).bid), [9]);
});

test('a venue that kept recording gives nothing, whatever the other venue lost', () => {
  const archive = new Map([['BTC/oracle', entries(ticks('BTC', 0, HOUR_MS))],
    ['BTC/coinbase-book', entries(tops(0, HOUR_MS).filter(row => row.r < START + 30 * MIN || row.r >= START + 31 * MIN))]]);
  const standby = new Map([['BTC/oracle', entries(ticks('BTC', 0, HOUR_MS, 30))], ['BTC/coinbase-book', entries(tops(0, HOUR_MS, 30))],
    ['BTC/coinbase-trades', entries([{ price: 1, size: 1, side: 'buy', tradeId: 7, r: START + 30 * MIN + 20_000 }])]]);
  const plan = planHour(HOUR, archive, standby, 'b');
  assert.deepEqual([...plan.additions.keys()].sort(), ['BTC/coinbase-book', 'BTC/coinbase-trades']);
  assert.equal(plan.additions.get('BTC/coinbase-book').length, 117);
});

test('a tick or a trade the archive already has is not added again, wherever its copy says it arrived', () => {
  const kept = ticks('BTC', 0, HOUR_MS).filter(row => row.r < START + 20 * MIN || row.r >= START + 22 * MIN);
  const same = { ...kept.find(row => row.r === START + 22 * MIN), r: START + 21 * MIN };
  const trade = { price: 5, size: 1, side: 'buy', tradeId: 42, r: START + 21 * MIN };
  const archive = new Map([['BTC/oracle', entries(kept)], ['BTC/coinbase-trades', entries([{ ...trade, r: START + 19 * MIN }])]]);
  const standby = new Map([['BTC/oracle', entries([same, { a: 'BTC', p: 7, e: 1, r: START + 21 * MIN + 1 }])], ['BTC/coinbase-trades', entries([trade])]]);
  const plan = planHour(HOUR, archive, standby, 'b');
  assert.deepEqual(plan.additions.get('BTC/oracle').map(entry => JSON.parse(entry.line).e), [1]);
  // Coinbase was not recorded at all by this archive, so the whole hour is its gap, and still the trade it has is not doubled.
  assert.equal(plan.additions.has('BTC/coinbase-trades'), false);
});

test('added rows go in by time, and the original lines keep their order whatever their times', () => {
  const original = [{ line: 'a', r: 10 }, { line: 'b', r: 30 }, { line: 'c', r: 20 }, { line: 'torn', r: 20 }, { line: 'd', r: 40 }];
  assert.deepEqual(mergeLines(original, [{ line: 'x', r: 5 }, { line: 'y', r: 25 }, { line: 'z', r: 35 }, { line: 'w', r: 99 }]), ['x', 'a', 'y', 'b', 'c', 'torn', 'z', 'd', 'w']);
  assert.deepEqual(mergeLines([], [{ line: 'x', r: 1 }]), ['x']);
  assert.deepEqual(mergeLines(original, []), ['a', 'b', 'c', 'torn', 'd']);
});

test('an hour file is replaced only by a copy that holds every original line, and only if it has not changed since it was read', () => {
  const f = folders();
  try {
    const target = f.put(f.into, 'BTC', 'oracle', [{ r: 1 }, '{"cut', { r: 3 }]);
    const original = readHourFile(target), before = readFileSync(target);
    assert.deepEqual(original.map(entry => [entry.line, entry.r]), [['{"r":1}', 1], ['{"cut', 1], ['{"r":3}', 3]]);
    const stamp = { size: statSync(target).size, mtimeMs: statSync(target).mtimeMs };
    // A merged copy that lost a line, or reordered two, is refused before anything is written.
    for (const bad of [['{"r":1}', '{"r":2,"h":"b"}', '{"r":3}'], ['{"cut', '{"r":1}', '{"r":3}', 'x']]) {
      assert.throws(() => replaceHourFile(target, original, bad, stamp), error => error.code === 'EFILLCHECK');
    }
    // The recorder added to the file after it was read: left alone, with nothing of ours beside it.
    const older = new Date(Date.now() - 60_000);
    utimesSync(target, older, older);
    assert.equal(replaceHourFile(target, original, ['{"r":1}', '{"cut', '{"r":2,"h":"b"}', '{"r":3}'], stamp), false);
    assert.deepEqual(readFileSync(target), before);
    assert.deepEqual(readdirSync(dirname(target)), ['BTC-oracle-20261128T10.jsonl.gz']);
    // A file that appeared where there was none is not overwritten either.
    assert.equal(replaceHourFile(target, [], ['{"r":2,"h":"b"}'], null), false);
    assert.deepEqual(readFileSync(target), before);
    const fresh = { size: statSync(target).size, mtimeMs: statSync(target).mtimeMs };
    assert.equal(replaceHourFile(target, original, ['{"r":1}', '{"cut', '{"r":2,"h":"b"}', '{"r":3}'], fresh), true);
    assert.deepEqual(f.rows(target), [{ r: 1 }, '{"cut', { r: 2, h: 'b' }, { r: 3 }]);
  } finally { f.cleanup(); }
});

test('a gap in the archive is filled from the second recording, once, and everything else is left as it was', () => {
  const f = folders();
  try {
    const mine = ticks('BTC', 0, HOUR_MS).filter(row => row.r < START + 20 * MIN || row.r >= START + 22 * MIN);
    const oracle = f.put(f.into, 'BTC', 'oracle', [...mine.slice(0, 5), '{"a":"BTC","p":1,"e"', ...mine.slice(5)]);
    const book = f.put(f.into, 'BTC', 'coinbase-book', tops(0, HOUR_MS));
    const bookBytes = readFileSync(book);
    f.put(f.from, 'BTC', 'oracle', ticks('BTC', 0, HOUR_MS, 30));
    f.put(f.from, 'BTC', 'coinbase-book', tops(0, HOUR_MS, 30));
    f.put(f.from, 'ZEC', 'perps-funding', [{ rateBps1h: 2, r: START + 21 * MIN }, { rateBps1h: 3, r: START + 40 * MIN }]);
    // The hour in progress on the second machine, and one that has only just ended.
    f.put(f.from, 'BTC', 'oracle', ticks('BTC', 0, 60_000, 30, '20261128T11'), '20261128T11');
    writeFileSync(f.path(f.from, 'BTC', 'oracle', '20261128T12', ''), '{"r":1}\n');
    // A copy left half made by a run that died.
    writeFileSync(`${oracle}.fill`, 'half');

    const planned = fill({ from: f.from, into: f.into, now: LATER, dryRun: true });
    assert.deepEqual([planned.hours.length, planned.hours[0].added, planned.hours[0].files], [1, 238, 2]);
    assert.equal(existsSync(join(f.into, '_recorder', 'fills.jsonl')) || existsSync(join(f.into, '_recorder', 'fill-state.json')), false, 'a dry run writes nothing');
    assert.equal(f.rows(oracle).length, mine.length + 1);

    const logs = [];
    const result = fill({ from: f.from, into: f.into, now: LATER, log: text => logs.push(text) });
    assert.equal(result.host, '5080', 'the name comes from the second recording\'s own marker');
    assert.deepEqual(result.hours.map(hour => [hour.hour, hour.added, hour.files, hour.refused]), [[HOUR, 238, 2, 0]]);
    assert.deepEqual(result.skipped, [{ hour: '20261128T11', why: 'too recent' }, { hour: '20261128T12', why: 'too recent' }]);
    assert.deepEqual(logs, [`${HOUR}: 238 rows added to 2 files`]);
    const after = f.rows(oracle);
    assert.equal(after.length, mine.length + 1 + 237);
    assert.deepEqual(after.filter(row => typeof row === 'string' || row.h === undefined), [...mine.slice(0, 5), '{"a":"BTC","p":1,"e"', ...mine.slice(5)], 'every original line, in order');
    const added = after.filter(row => row.h === '5080');
    assert.equal(added.length, 237);
    assert.equal(added.every(row => row.r >= START + 20 * MIN && row.r < START + 22 * MIN), true);
    const times = after.filter(row => typeof row !== 'string').map(row => row.r);
    assert.deepEqual(times, [...times].sort((a, b) => a - b), 'in time order');
    assert.deepEqual(readFileSync(book), bookBytes, 'the venue that kept recording was not touched');
    assert.deepEqual(f.rows(f.path(f.into, 'ZEC', 'perps-funding')), [{ rateBps1h: 2, r: START + 21 * MIN, h: '5080' }], 'a file the archive lacked is made, with only the rows from the gap');
    assert.equal(existsSync(`${oracle}.fill`), false);

    const fills = readFileSync(join(f.into, '_recorder', 'fills.jsonl'), 'utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.deepEqual(fills.map(row => [row.hour, row.coin, row.stream, row.added, row.from]), [[HOUR, 'BTC', 'oracle', 237, '5080'], [HOUR, 'ZEC', 'perps-funding', 1, '5080']]);
    const compared = readFileSync(join(f.into, '_recorder', 'compare.jsonl'), 'utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.equal(compared.length, 1);
    assert.deepEqual(compared[0].windows.jupiter, [[new Date(START + 20 * MIN - 500).toISOString(), new Date(START + 22 * MIN).toISOString()]]);
    assert.deepEqual(Object.keys(JSON.parse(readFileSync(join(f.into, '_recorder', 'fill-state.json'), 'utf8')).done), [HOUR]);

    // A second run has nothing to do, and a state file that was lost changes nothing either: the gap is no longer one.
    const bytes = readFileSync(oracle);
    assert.deepEqual(fill({ from: f.from, into: f.into, now: LATER }).hours, []);
    rmSync(join(f.into, '_recorder', 'fill-state.json'));
    assert.deepEqual(fill({ from: f.from, into: f.into, now: LATER }).hours.map(hour => [hour.added, hour.files]), [[0, 0]]);
    assert.deepEqual(readFileSync(oracle), bytes);
  } finally { f.cleanup(); }
});

test('an hour the archive missed entirely is taken whole', () => {
  const f = folders();
  try {
    f.put(f.from, 'SOL', 'oracle', ticks('SOL', 0, 10_000));
    f.put(f.from, 'SOL', 'coinbase-trades', [{ price: 1, size: 2, side: 'sell', tradeId: 9, t: START + 1, r: START + 2 }]);
    const result = fill({ from: f.from, into: f.into, now: LATER, host: 'spare' });
    assert.deepEqual(result.hours.map(hour => [hour.added, hour.files]), [[21, 2]]);
    assert.equal(f.rows(f.path(f.into, 'SOL', 'oracle')).every(row => row.h === 'spare'), true);
    assert.deepEqual(f.rows(f.path(f.into, 'SOL', 'coinbase-trades')), [{ price: 1, size: 2, side: 'sell', tradeId: 9, t: START + 1, r: START + 2, h: 'spare' }]);
  } finally { f.cleanup(); }
});

test('an hour either recorder is still closing waits, and a file that cannot be read is left exactly as it is', () => {
  const f = folders();
  try {
    const standby = f.put(f.from, 'BTC', 'oracle', ticks('BTC', 0, HOUR_MS));
    const plain = f.path(f.into, 'BTC', 'oracle', HOUR, '');
    mkdirSync(dirname(plain), { recursive: true });
    writeFileSync(plain, '{"r":1}\n');
    assert.deepEqual(fill({ from: f.from, into: f.into, now: LATER }).skipped, [{ hour: HOUR, why: 'the archive is still closing it' }]);
    assert.equal(existsSync(join(f.into, '_recorder', 'fill-state.json')), false, 'not marked as done');
    rmSync(plain);
    // The second recording has a file of that hour still plain: wait for it, but not for ever.
    mkdirSync(dirname(f.path(f.from, 'ZEC', 'oracle', HOUR, '')), { recursive: true });
    writeFileSync(f.path(f.from, 'ZEC', 'oracle', HOUR, ''), '{"r":1}\n');
    assert.deepEqual(fill({ from: f.from, into: f.into, now: LATER }).skipped, [{ hour: HOUR, why: 'the second recording is still closing it' }]);
    // An unreadable file in the archive: reported, untouched, and the readable ones are still filled.
    const broken = f.path(f.into, 'BTC', 'oracle');
    writeFileSync(broken, 'not gzip');
    f.put(f.from, 'ETH', 'oracle', ticks('ETH', 0, 5000));
    assert.ok(existsSync(standby));
    const result = fill({ from: f.from, into: f.into, now: START + 2 * HOUR_MS + MIN });
    assert.deepEqual(result.hours.map(hour => [hour.files, hour.unreadable.map(u => [u.side, u.key])]), [[1, [['archive', 'BTC/oracle']]]]);
    assert.equal(readFileSync(broken, 'utf8'), 'not gzip');
    assert.equal(f.rows(f.path(f.into, 'ETH', 'oracle')).length, 10);
  } finally { f.cleanup(); }
});

test('rows go one way: from a short-lived copy into an archive, and never around a missing folder', () => {
  const f = folders();
  try {
    assert.throws(() => fill({ from: f.into, into: f.from, now: LATER }), error => error.code === 'ENOTSTANDBY', 'an archive is not a source');
    writeFileSync(join(f.into, '_recorder', 'standby'), '{}');
    assert.throws(() => fill({ from: f.from, into: f.into, now: LATER }), error => error.code === 'ENOTARCHIVE', 'a short-lived copy is not a destination');
    rmSync(join(f.into, '_recorder'), { recursive: true });
    assert.throws(() => fill({ from: f.from, into: f.into, now: LATER }), error => error.code === 'ENOTARCHIVE', 'a folder no recorder wrote is not an archive');
    assert.throws(() => fill({ from: f.from, into: join(f.root, 'absent'), now: LATER }), error => error.code === 'ENOFOLDER');
    assert.throws(() => fill({ from: join(f.root, 'absent'), into: f.into, now: LATER }), error => error.code === 'ENOFOLDER');
    assert.equal(existsSync(join(f.root, 'absent')), false, 'nothing was created in its place');
    mkdirSync(join(f.into, '_recorder'));
    assert.throws(() => fill({ from: f.from, into: f.into, now: LATER, host: 'a b' }), error => error.code === 'EBADHOST');
  } finally { f.cleanup(); }
});

test('the two recordings are compared where both recorded: shared ticks, ticks only one saw, differing values and the arrival lag', () => {
  const mine = ticks('BTC', 0, HOUR_MS), theirs = ticks('BTC', 0, HOUR_MS, 40);
  // The second recording missed five ticks, saw one the archive did not, and has one price that differs.
  const standbyRows = theirs.filter((row, i) => i < 100 || i >= 105);
  standbyRows[200] = { ...standbyRows[200], p: 1 };
  const archiveRows = mine.filter((row, i) => i !== 300);
  const trade = id => ({ price: 5, size: 1, side: 'buy', tradeId: id, r: START + id * 1000 });
  const archive = new Map([['BTC/oracle', entries(archiveRows)], ['BTC/coinbase-trades', entries([1, 2, 3].map(trade))], ['BTC/coinbase-book', entries(tops(0, HOUR_MS))]]);
  const standby = new Map([['BTC/oracle', entries(standbyRows)], ['BTC/coinbase-trades', entries([{ ...trade(1), size: 2 }, trade(2), trade(4)])],
    ['BTC/coinbase-book', entries(tops(0, HOUR_MS, 40))]]);
  const { compare, additions, windows } = planHour(HOUR, archive, standby, 'b');
  assert.deepEqual([windows.jupiter, windows.coinbase, additions.size], [[], [], 0]);
  assert.deepEqual(compare.oracle, { both: 7200 - 6, onlyArchive: 5, onlyStandby: 1, differing: 1, lagMsP50: 40, lagMsP95: 40 });
  assert.deepEqual(compare.trades, { both: 2, onlyArchive: 1, onlyStandby: 1, differing: 1, lagMsP50: 0, lagMsP95: 0 });
  // Ticks from a stretch one side was not recording are not counted against the other, and a filled row is not the archive's own.
  const gappy = new Map([['BTC/oracle', entries([...mine.filter(row => row.r < START + 20 * MIN || row.r >= START + 22 * MIN), { ...mine[2500], h: 'b' }])]]);
  const again = planHour(HOUR, gappy, new Map([['BTC/oracle', entries(theirs)]]), 'b').compare.oracle;
  assert.deepEqual([again.onlyArchive, again.onlyStandby, again.differing], [0, 0, 0]);
  // 240 ticks fell in the stretch; the three before it and the two after it are within a second of its edges and left out.
  assert.equal(again.both, 7200 - 240 - 5);
});

test('a recorder folder is listed by hour, with files of other names ignored and anything unfinished noted', () => {
  const f = folders();
  try {
    f.put(f.into, 'BTC', 'oracle', [{ r: 1 }]);
    writeFileSync(f.path(f.into, 'BTC', 'oracle', '20261128T11', ''), '{"r":1}\n');
    writeFileSync(join(dirname(f.path(f.into, 'BTC', 'oracle')), 'notes.txt'), 'x');
    writeFileSync(join(dirname(f.path(f.into, 'BTC', 'oracle')), 'ETH-oracle-20261128T10.jsonl.gz'), 'x');
    mkdirSync(join(f.into, 'lower', 'oracle', '2026-11-28'), { recursive: true });
    writeFileSync(join(f.into, 'lower', 'oracle', '2026-11-28', 'lower-oracle-20261128T10.jsonl.gz'), 'x');
    const hours = listHours(f.into);
    assert.deepEqual([...hours.keys()].sort(), ['20261128T10', '20261128T11']);
    assert.deepEqual([[...hours.get(HOUR).files.keys()], hours.get(HOUR).unsettled, hours.get('20261128T11').unsettled], [['BTC/oracle'], false, true]);
    assert.deepEqual([...listHours(join(f.root, 'absent'))], []);
  } finally { f.cleanup(); }
});

test('the options are checked before anything runs, and --pull cannot be read as an rsync option', () => {
  assert.deepEqual(parseFillArgs(['--from', '/a/b/', '--pull', '5080:CoinTradingStandby', '--host', 'spare', '--dry-run']),
    { into: '/Volumes/dasdata/CoinTradingData', from: '/a/b', pull: '5080:CoinTradingStandby/', host: 'spare', dryRun: true });
  assert.equal(parseFillArgs(['--help']).help, true);
  for (const bad of [[], ['--from', 'relative'], ['--from', '/a', '--into', '/a'], ['--from', '/a', '--pull', '-e sh:x'], ['--from', '/a', '--pull', '--rsh=x:y'],
    ['--from', '/a', '--pull', 'host'], ['--from', '/a', '--pull', 'host:a b'], ['--from', '/a', '--host', 'a/b'], ['--from'], ['--from', '/a', '--nope', 'x']]) {
    assert.throws(() => parseFillArgs(bad), RangeError, JSON.stringify(bad));
  }
});

test('the tool reports what it did as JSON, refuses a wrong folder with exit 2, and opens no connection to a venue', () => {
  const f = folders();
  try {
    f.put(f.from, 'SOL', 'oracle', ticks('SOL', 0, 3000, 0, '20200101T00'), '20200101T00');
    const run = args => spawnSync(process.execPath, [TOOL, ...args], { encoding: 'utf8' });
    const done = run(['--from', f.from, '--into', f.into]);
    assert.equal(done.status, 0, done.stderr);
    const report = JSON.parse(done.stdout);
    assert.deepEqual([report.host, report.pulled, report.hours.map(hour => [hour.hour, hour.added, hour.files, hour.gaps.jupiter])], ['5080', null, [['20200101T00', 6, 1, 1]]]);
    assert.equal(run(['--from', f.into, '--into', f.from]).status, 2);
    assert.equal(run(['--from', join(f.root, 'absent'), '--into', f.into]).status, 2);
    assert.equal(run([]).status, 2);
    assert.equal(run(['--help']).status, 0);
    for (const path of [TOOL, LIB]) {
      const source = readFileSync(path, 'utf8');
      assert.equal(/fetch\(|WebSocket|https?:\/\/|wss?:\/\/|process\.env|Authorization|api[-_]?key|secret/i.test(source), false, `${path}: files only, no venue, no credential`);
    }
  } finally { f.cleanup(); }
});
