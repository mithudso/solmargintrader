#!/usr/bin/env node
/**
 * Fills gaps in the recorder's archive from a second machine's short-lived
 * recording, and writes down how the two compared. Reads and writes files only:
 * it opens no connection to a venue. With --pull it first runs rsync to bring
 * the local copy of the second recording up to date.
 *
 *   node tools/market-recorder-fill.mjs --from ~/.local/state/solmargintrader/market-standby --pull 5080:CoinTradingStandby/
 *
 * FILL_USAGE in lib/market-recorder-fill.mjs says what is taken and what is not.
 */
import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { FILL_USAGE, fill, parseFillArgs } from './lib/market-recorder-fill.mjs';

const PULL_TIMEOUT_MS = 300_000;

let options;
try { options = parseFillArgs(process.argv.slice(2)); } catch (error) { console.error(`${error.message}\n\n${FILL_USAGE}`); process.exit(2); }
if (options.help) { console.log(FILL_USAGE); process.exit(0); }

let pulled = null;
if (options.pull) {
  // The copy is this machine's own folder, so it may be created. The archive never is.
  mkdirSync(options.from, { recursive: true });
  // --delete keeps the copy as short-lived as its source: hours the second recorder dropped are dropped here too.
  const run = spawnSync('rsync', ['-a', '--delete', '--timeout=60', '--', options.pull, `${options.from}/`], { stdio: ['ignore', 'ignore', 'pipe'], timeout: PULL_TIMEOUT_MS });
  pulled = run.status === 0;
  // The other machine being away is not a failure of this run: hours already copied are still looked at.
  if (!pulled) console.error(`Could not copy from ${options.pull} (${String(run.error?.message ?? run.stderr ?? '').trim().split('\n').at(-1) || `rsync exit ${run.status}`}). Using the copy as it is.`);
}

try {
  const result = fill({ from: options.from, into: options.into, host: options.host, dryRun: options.dryRun, log: text => console.error(text) });
  const brief = result.hours.map(hour => ({ hour: hour.hour, added: hour.added, files: hour.files, refused: hour.refused,
    gaps: Object.fromEntries(Object.entries(hour.windows).map(([venue, list]) => [venue, list.length])), oracle: hour.compare.oracle, trades: hour.compare.trades,
    unreadable: hour.unreadable.length }));
  console.log(JSON.stringify({ from: options.from, into: options.into, host: result.host, pulled, dryRun: options.dryRun, hours: brief, skipped: result.skipped }, null, 1));
} catch (error) {
  console.error(error.message);
  process.exit(['ENOFOLDER', 'ENOTSTANDBY', 'ENOTARCHIVE', 'EBADHOST'].includes(error.code) ? 2 : 1);
}
