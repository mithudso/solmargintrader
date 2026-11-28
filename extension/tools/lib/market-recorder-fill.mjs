/**
 * Fills gaps in a recorded archive from a second, short-lived recording of the
 * same markets, and compares the two where both recorded.
 *
 * The archive is the recorder's output folder (the NAS). The second recording is
 * a copy of another machine's recorder folder, one that was started with
 * --keep-hours and so holds only the last few hours. Rows flow one way: from
 * that copy into the archive, never back.
 *
 * What counts as a gap is decided per venue, not per file: a stream that writes
 * only when something changed is quiet for minutes on a healthy recorder, but a
 * venue as a whole (every Jupiter stream of every coin, or every Coinbase one)
 * never is. A stretch in which the archive has no row at all from a venue is one
 * in which it was not recording that venue, and only rows from inside such a
 * stretch are taken. Outside them the two recordings are compared, not merged:
 * the archive stays what one listener saw.
 *
 * An hour's file is rewritten only as a whole, beside the old one, checked to
 * hold every line the old one held in the same order, and put in its place in
 * one step. A row that came from the second recording carries `h`, the name of
 * the machine it came from; its `r` is that machine's receive time.
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { gunzipSync, gzipSync } from 'node:zlib';
import { STREAMS, hourStart, safeCoin } from './market-recorder.mjs';

export { hourStart };

/** Which streams stop together: one socket or one API per venue. */
export const VENUES = Object.freeze({
  jupiter: Object.freeze(['oracle', 'perps-book', 'perps-funding', '1000x-market', 'perps-pool']),
  coinbase: Object.freeze(['coinbase-book', 'coinbase-trades', 'coinbase-depth']),
});
/** A venue with no row from any coin for this long was not being recorded. Measured normal silence is under five seconds. */
export const OUTAGE_MS = 15_000;
/** Rows this close to a row the archive has are left out: the two machines' clocks and arrival times differ a little. */
export const EDGE_MS = 1000;
/** An hour is looked at once it has been over this long, so both recorders have closed and compressed it. */
export const SETTLE_MS = 600_000;
/** After this long an hour is taken with whatever the second recording managed to compress. */
const GIVE_UP_WAITING_MS = 3_600_000;
const HOUR_MS = 3_600_000;
const KEEP_DONE_MS = 7 * 86_400_000;
const HOUR_FILE = /^([A-Z0-9]{1,16})-([a-z0-9-]+)-((\d{4})(\d{2})(\d{2})T(\d{2}))\.jsonl(\.gz|\.gz\.ready|\.gz\.merge|\.gz\.tmp|\.gz\.fill)?$/;
const HOST = /^[A-Za-z0-9._-]{1,64}$/;
/** What makes two rows the same event, for the streams that have such a thing. */
const IDENTITY = Object.freeze({ oracle: row => row.e, 'coinbase-trades': row => row.tradeId });
const VENUE_OF = new Map(Object.entries(VENUES).flatMap(([venue, streams]) => streams.map(stream => [stream, venue])));

const coded = (code, message) => Object.assign(new Error(message), { code });
const isFolder = path => { try { return statSync(path).isDirectory(); } catch { return false; } };
const list = folder => { try { return readdirSync(folder, { withFileTypes: true }); } catch { return []; } };
const iso = ms => new Date(ms).toISOString();

/**
 * Every recorded hour under a recorder folder: its compressed files by
 * `<COIN>/<stream>`, and whether anything of it is still being written or
 * compressed (`unsettled`).
 */
export function listHours(folder) {
  const hours = new Map();
  for (const coin of list(folder)) {
    if (!coin.isDirectory() || !safeCoin(coin.name)) continue;
    for (const stream of STREAMS) {
      for (const day of list(join(folder, coin.name, stream))) {
        if (!day.isDirectory()) continue;
        for (const { name } of list(join(folder, coin.name, stream, day.name))) {
          const m = HOUR_FILE.exec(name);
          if (!m || m[1] !== coin.name || m[2] !== stream) continue;
          const entry = hours.get(m[3]) ?? { files: new Map(), unsettled: false, leftovers: [] };
          hours.set(m[3], entry);
          const path = join(folder, coin.name, stream, day.name, name);
          if (m[8] === '.gz') entry.files.set(`${coin.name}/${stream}`, path);
          else if (m[8] === '.gz.fill') entry.leftovers.push(path);
          else entry.unsettled = true;
        }
      }
    }
  }
  return hours;
}

/** A compressed hour file as lines, each with the receive time it sorts by. A line that is not a row keeps the time of the row before it. */
export function readHourFile(path, floor = 0) {
  const text = gunzipSync(readFileSync(path)).toString('utf8');
  const out = [];
  let last = floor;
  for (const line of text.split('\n')) {
    if (!line) continue;
    let row = null;
    try { row = JSON.parse(line); } catch { /* a row cut off by a crash stays a line, and is carried along */ }
    if (row === null || typeof row !== 'object' || Array.isArray(row)) row = null;
    if (row && Number.isFinite(row.r)) last = row.r;
    out.push({ line, r: last, row });
  }
  return out;
}

/**
 * The stretches of [start, end) in which `times` (sorted) has no entry for more
 * than `threshold`. `fromRow` and `toRow` say whether a stretch is bounded by a
 * row or by the edge of the hour.
 */
export function outages(times, start, end, threshold = OUTAGE_MS) {
  const out = [];
  let prev = start, prevIsRow = false;
  for (const t of times) {
    if (t >= end) break;
    if (t - prev > threshold) out.push({ from: prev, to: t, fromRow: prevIsRow, toRow: true });
    if (t >= prev) { prev = t; prevIsRow = true; }
  }
  if (end - prev > threshold) out.push({ from: prev, to: end, fromRow: prevIsRow, toRow: false });
  return out;
}

/** Whether a receive time falls inside one of the stretches, away from the rows that bound it. */
const inside = (r, windows) => windows.some(w => r >= (w.fromRow ? w.from + EDGE_MS : w.from) && r < (w.toRow ? w.to - EDGE_MS : w.to));
/** The same, but generous at the edges: for leaving rows out of a comparison. */
const near = (r, windows) => windows.some(w => r >= w.from - EDGE_MS && r < w.to + EDGE_MS);

function venueTimes(files, streams) {
  const times = [];
  for (const [key, rows] of files) {
    if (!streams.includes(key.split('/')[1])) continue;
    for (const entry of rows) if (entry.row && Number.isFinite(entry.row.r)) times.push(entry.row.r);
  }
  return times.sort((a, b) => a - b);
}

const quantile = (sorted, q) => sorted.length ? sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] : null;

/** How far the two recordings agree on one identified stream, over the time both were recording its venue. */
function compareStream(stream, fields, archive, standby, windows, standbyWindows) {
  const identity = IDENTITY[stream], venue = VENUE_OF.get(stream);
  const result = { both: 0, onlyArchive: 0, onlyStandby: 0, differing: 0, lagMsP50: null, lagMsP95: null };
  const lags = [];
  const keys = new Set([...archive.keys(), ...standby.keys()].filter(key => key.split('/')[1] === stream));
  for (const key of keys) {
    const index = (rows, skip) => {
      const map = new Map();
      for (const { row } of rows ?? []) {
        // A row that was itself filled in from another machine is not the archive's own observation.
        if (!row || row.h !== undefined || !Number.isFinite(row.r) || identity(row) === undefined || near(row.r, skip)) continue;
        map.set(identity(row), row);
      }
      return map;
    };
    const blind = [...windows[venue], ...standbyWindows[venue]];
    const mine = index(archive.get(key), blind), theirs = index(standby.get(key), blind);
    for (const [id, row] of mine) {
      const other = theirs.get(id);
      if (!other) { result.onlyArchive += 1; continue; }
      result.both += 1;
      if (fields.some(field => row[field] !== other[field])) result.differing += 1;
      lags.push(other.r - row.r);
    }
    for (const id of theirs.keys()) if (!mine.has(id)) result.onlyStandby += 1;
  }
  lags.sort((a, b) => a - b);
  result.lagMsP50 = quantile(lags, 0.5); result.lagMsP95 = quantile(lags, 0.95);
  return result;
}

/**
 * What one hour needs. `archive` and `standby` map `<COIN>/<stream>` to the lines
 * of that hour's file (readHourFile). Returns the stretches each side was not
 * recording a venue, the rows to add per file, and the comparison. Reads nothing
 * and writes nothing.
 */
export function planHour(hour, archive, standby, host) {
  const start = hourStart(hour), end = start + HOUR_MS;
  const windows = {}, standbyWindows = {};
  for (const [venue, streams] of Object.entries(VENUES)) {
    windows[venue] = outages(venueTimes(archive, streams), start, end);
    standbyWindows[venue] = outages(venueTimes(standby, streams), start, end);
  }
  const additions = new Map();
  for (const [key, rows] of standby) {
    const stream = key.split('/')[1], gaps = windows[VENUE_OF.get(stream)];
    if (!gaps?.length) continue;
    const identity = IDENTITY[stream];
    const have = new Set(identity ? (archive.get(key) ?? []).filter(entry => entry.row).map(entry => identity(entry.row)) : []);
    const add = [];
    for (const { row } of rows) {
      if (!row || !Number.isFinite(row.r) || row.r < start || row.r >= end || !inside(row.r, gaps)) continue;
      if (identity && have.has(identity(row))) continue;
      add.push({ r: row.r, line: JSON.stringify({ ...row, h: host }) });
    }
    if (add.length) additions.set(key, add.sort((a, b) => a.r - b.r));
  }
  return { windows, standbyWindows, additions,
    compare: { oracle: compareStream('oracle', ['p'], archive, standby, windows, standbyWindows),
      trades: compareStream('coinbase-trades', ['price', 'size', 'side'], archive, standby, windows, standbyWindows) } };
}

/**
 * The lines of a file with rows added in time order. The original lines keep
 * their order whatever their times: an added row goes before the first original
 * line that is later than it.
 */
export function mergeLines(original, added) {
  const out = [];
  let next = 0, top = -Infinity;
  for (const entry of original) {
    top = Math.max(top, entry.r);
    while (next < added.length && added[next].r < top) out.push(added[next++].line);
    out.push(entry.line);
  }
  while (next < added.length) out.push(added[next++].line);
  return out;
}

/**
 * Put the merged lines in place of an hour's file. Refused, and nothing
 * changed, unless the result holds every original line in its original order
 * and the file on disk is still the one that was read (`stamp`; null for an
 * hour the archive has no file for).
 */
export function replaceHourFile(target, original, lines, stamp) {
  const packed = gzipSync(lines.join('\n') + '\n', { level: 9 });
  const back = gunzipSync(packed).toString('utf8').split('\n').filter(Boolean);
  let kept = 0;
  for (const line of back) if (kept < original.length && line === original[kept].line) kept += 1;
  if (kept !== original.length || back.length !== lines.length) throw coded('EFILLCHECK', `The merged copy of ${target} does not hold every original row.`);
  const partial = `${target}.fill`;
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(partial, packed);
  let now = null;
  try { const s = statSync(target); now = { size: s.size, mtimeMs: s.mtimeMs }; } catch { /* no file there */ }
  const same = stamp === null ? now === null : now !== null && now.size === stamp.size && now.mtimeMs === stamp.mtimeMs;
  if (!same) { unlinkSync(partial); return false; }
  renameSync(partial, target);
  return true;
}

/** The name the second recording gives itself, from the marker its recorder wrote. */
function standbyHost(from) {
  try {
    const host = JSON.parse(readFileSync(join(from, '_recorder', 'standby'), 'utf8')).host;
    return typeof host === 'string' && HOST.test(host) ? host : null;
  } catch { return null; }
}

function readState(path) {
  try {
    const state = JSON.parse(readFileSync(path, 'utf8'));
    return state && typeof state.done === 'object' && state.done !== null && !Array.isArray(state.done) ? state : { done: {} };
  } catch { return { done: {} }; }
}

const ranges = windows => Object.fromEntries(Object.entries(windows).map(([venue, list]) => [venue, list.slice(0, 50).map(w => [iso(w.from), iso(w.to)])]));

/**
 * Look at every finished hour of the second recording that has not been looked
 * at yet. Returns { hours: [...], skipped: [...] }.
 *
 *   from: a copy of a recorder folder that was started with --keep-hours;
 *   into: the archive; now: ms; host: a name for the second machine (default: the one in its marker);
 *   dryRun: plan and compare, write nothing.
 */
export function fill({ from, into, now = Date.now(), host = null, dryRun = false, log = () => {} }) {
  if (!isFolder(from)) throw coded('ENOFOLDER', `There is no folder ${from}.`);
  if (!isFolder(into)) throw coded('ENOFOLDER', `There is no folder ${into}. Mount the disk, then start again.`);
  // Rows go one way. The marker is written by a recorder started with --keep-hours, and only into a folder that was empty.
  if (!existsSync(join(from, '_recorder', 'standby'))) throw coded('ENOTSTANDBY', `${from} is not a short-lived copy: it has no _recorder/standby marker.`);
  if (!isFolder(join(into, '_recorder')) || existsSync(join(into, '_recorder', 'standby'))) {
    throw coded('ENOTARCHIVE', `${into} is not an archive: it must be a recorder folder that was not started with --keep-hours.`);
  }
  const label = host ?? standbyHost(from) ?? 'standby';
  if (!HOST.test(label)) throw coded('EBADHOST', 'The machine name may hold letters, digits, dot, dash and underscore only.');
  const device = statSync(into).dev;
  // A network disk that went away must not be written around: nothing is created under a path that is no longer that disk.
  const present = () => { try { return statSync(into).dev === device; } catch { return false; } };
  const statePath = join(into, '_recorder', 'fill-state.json');
  const state = readState(statePath);
  const theirs = listHours(from), mine = listHours(into);
  const result = { host: label, hours: [], skipped: [] };

  for (const hour of [...theirs.keys()].sort()) {
    if (state.done[hour]) continue;
    const end = hourStart(hour) + HOUR_MS, standby = theirs.get(hour), archive = mine.get(hour) ?? { files: new Map(), unsettled: false, leftovers: [] };
    if (now < end + SETTLE_MS) { result.skipped.push({ hour, why: 'too recent' }); continue; }
    if (standby.unsettled && now < end + GIVE_UP_WAITING_MS) { result.skipped.push({ hour, why: 'the second recording is still closing it' }); continue; }
    if (archive.unsettled) { result.skipped.push({ hour, why: 'the archive is still closing it' }); continue; }
    if (!standby.files.size) continue;

    const unreadable = [];
    const load = (files, side) => {
      const rows = new Map(), stamps = new Map();
      for (const [key, path] of files) {
        try {
          const s = statSync(path);
          rows.set(key, readHourFile(path, hourStart(hour)));
          stamps.set(key, { size: s.size, mtimeMs: s.mtimeMs });
        } catch (error) { unreadable.push({ side, key, reason: String(error?.message ?? error).slice(0, 120) }); }
      }
      return { rows, stamps };
    };
    const a = load(archive.files, 'archive'), s = load(standby.files, 'standby');
    const plan = planHour(hour, a.rows, s.rows, label);
    const entry = { hour, added: 0, files: 0, refused: 0, windows: ranges(plan.windows), standbyWindows: ranges(plan.standbyWindows), compare: plan.compare, unreadable };

    for (const [key, add] of plan.additions) {
      // A file of the archive that could not be read is left exactly as it is.
      if (archive.files.has(key) && !a.rows.has(key)) continue;
      entry.added += add.length; entry.files += 1;
      if (dryRun) continue;
      if (!present()) throw coded('ENODISK', 'The archive folder is gone or is no longer the same disk.');
      const [coin, stream] = key.split('/');
      const day = `${hour.slice(0, 4)}-${hour.slice(4, 6)}-${hour.slice(6, 8)}`;
      const target = join(into, coin, stream, day, `${coin}-${stream}-${hour}.jsonl.gz`);
      const original = a.rows.get(key) ?? [];
      const done = replaceHourFile(target, original, mergeLines(original, add), a.stamps.get(key) ?? null);
      if (!done) { entry.added -= add.length; entry.files -= 1; entry.refused += 1; continue; }
      appendFileSync(join(into, '_recorder', 'fills.jsonl'), JSON.stringify({ at: iso(now), hour, coin, stream, added: add.length, from: label,
        first: iso(add[0].r), last: iso(add.at(-1).r) }) + '\n');
    }
    result.hours.push(entry);
    if (dryRun) continue;
    if (!present()) throw coded('ENODISK', 'The archive folder is gone or is no longer the same disk.');
    for (const path of archive.leftovers) { try { unlinkSync(path); } catch { /* already gone */ } }
    appendFileSync(join(into, '_recorder', 'compare.jsonl'), JSON.stringify({ at: iso(now), from: label, ...entry }) + '\n');
    // A file that changed while it was being merged is tried again on the next run; everything else about the hour is done.
    if (!entry.refused) state.done[hour] = iso(now);
    for (const old of Object.keys(state.done)) if (hourStart(old) < now - KEEP_DONE_MS) delete state.done[old];
    writeFileSync(`${statePath}.tmp`, JSON.stringify(state, null, 1) + '\n');
    renameSync(`${statePath}.tmp`, statePath);
    log(`${hour}: ${entry.added} rows added to ${entry.files} files`);
  }
  return result;
}

export const FILL_USAGE = `Fill gaps in a recorded archive from a second, short-lived recording, and compare the two.

  node tools/market-recorder-fill.mjs --from <folder> [--into /Volumes/dasdata/CoinTradingData]
       [--pull <machine>:<folder>/] [--host <name>] [--dry-run]

--from      a copy of the second recorder's folder (one started with --keep-hours)
--into      the archive the main recorder writes
--pull      first bring --from up to date from another machine with rsync over ssh
--host      a name for the second machine in the rows it supplied (default: the name in its folder)
--dry-run   say what would be added, write nothing

Only finished hours are looked at, ten minutes after they end, once each. Rows are taken only
from stretches in which the archive recorded nothing at all from a venue for more than
${OUTAGE_MS / 1000} seconds. Every row taken carries "h": the machine it came from. What was
added is listed in _recorder/fills.jsonl, and how the two recordings compared, hour by hour,
in _recorder/compare.jsonl.`;

/** Options of the fill tool. Throws RangeError on anything it does not know. */
export function parseFillArgs(argv, defaults = { into: '/Volumes/dasdata/CoinTradingData', from: null, pull: null, host: null, dryRun: false }) {
  const out = { ...defaults };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dry-run') { out.dryRun = true; continue; }
    if (arg === '--help' || arg === '-h') { out.help = true; continue; }
    if (!['--from', '--into', '--pull', '--host'].includes(arg) || i + 1 >= argv.length) throw new RangeError(`Unknown or incomplete option ${arg}.`);
    const value = argv[++i];
    if (arg === '--host') { if (!HOST.test(value)) throw new RangeError('--host may hold letters, digits, dot, dash and underscore only.'); out.host = value; continue; }
    // Handed to rsync as one argument: it must read as machine:folder, never as an option.
    if (arg === '--pull') {
      if (!/^[A-Za-z0-9][A-Za-z0-9._@-]*:[A-Za-z0-9._~/-]+$/.test(value)) throw new RangeError('--pull needs <machine>:<folder>.');
      out.pull = value.endsWith('/') ? value : `${value}/`; continue;
    }
    if (!value.startsWith('/')) throw new RangeError(`${arg} must be an absolute folder.`);
    out[arg.slice(2)] = value.replace(/\/+$/, '') || '/';
  }
  if (!out.help && !out.from) throw new RangeError('--from is needed: the copy of the second recording.');
  if (!out.help && out.from === out.into) throw new RangeError('--from and --into are the same folder.');
  return out;
}
