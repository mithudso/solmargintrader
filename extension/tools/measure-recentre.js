#!/usr/bin/env node
/**
 * How often does the shipped auto-recentre gate actually open?
 *
 *   node tools/measure-recentre.js --csv ../data/SOL_1d.csv
 *
 * `recentreDecision()` refuses to move the ladder while anything is resting or
 * any lot is open, because `tick()` cannot cancel. That gate is deliberately
 * tight, and the honest question is whether it is so tight the feature never
 * fires. This answers it by driving the real `tick()` over a real close series,
 * once with `autoRecentre` off and once on, and reporting how many times the
 * ladder actually moved.
 *
 * The venue here never fills anything, which is the regime `tools/dryrun.js`
 * itself ends in (`{"filled":4,"resting":4}`): once bids are placed below the
 * market they rest, so the gate stays shut. A run with fills would let the book
 * empty and could move more often, bounded by the number of times every order
 * clears and every lot closes.
 *
 * This measures *ladder placement*, not P&L. For the economics of the ladder see
 * `backtester/core/gridsim.py` and `research/results/ladder_grid_sol.csv`.
 */

import { readFileSync } from 'node:fs';
import { tick } from '../src/core/engine.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore, DEFAULT_CONFIG } from '../src/storage/store.js';

function parseArgs(argv) {
  const out = { csv: '../data/SOL_1d.csv', column: null };
  for (let i = 0; i < argv.length; i += 2) {
    const flag = argv[i];
    if (!flag?.startsWith('--')) throw new Error(`expected a --flag, got "${flag}"`);
    const key = flag.slice(2);
    // Object.hasOwn, not `in`: `in` walks the prototype chain, so --constructor
    // and --__proto__ would pass a check that looks like a whitelist.
    if (!Object.hasOwn(out, key)) throw new Error(`unknown flag --${key}`);
    const value = argv[i + 1];
    if (value === undefined) throw new Error(`--${key} needs a value`);
    if (key === 'column') {
      const n = Number(value);
      if (!Number.isInteger(n) || n < 0) throw new Error(`--column must be a non-negative integer, got "${value}"`);
      out.column = n;
    } else {
      out[key] = value;
    }
  }
  return out;
}

/**
 * Index of the close column, resolved from the header by name.
 *
 * Hardcoding an index is the trap this repo has already paid for once: a source
 * that reorders its columns would silently measure the wrong series rather than
 * fail. `--column` overrides for a headerless file.
 */
function closeColumn(firstLine, override) {
  const cells = firstLine.split(',').map((h) => h.trim());
  if (override !== null) {
    // A headerless file must not lose its first bar to a slice(1) that assumes a
    // header. Decide by whether the target cell parses as a price.
    const hasHeader = !(Number(cells[override]) > 0);
    return { column: override, hasHeader };
  }
  const at = cells.map((h) => h.toLowerCase()).indexOf('close');
  if (at === -1) {
    throw new Error(`no "close" column in header [${cells.join(', ')}] - pass --column <index>`);
  }
  return { column: at, hasHeader: true };
}

/** A venue that remembers what it placed and echoes it back as live. */
function recordingVenue(readPrice) {
  const live = [];
  return {
    kind: 'spot',
    live,
    getPrice: async () => readPrice(),
    getOpenOrders: async () => live.slice(),
    getFills: async () => [],
    getCarryCosts: async () => [],
    placeOrder: async ({ intent }) => {
      live.push({ intentKey: intent.intentKey, side: intent.side, triggerPriceUsd: intent.level });
      return { venueOrderId: `v-${intent.intentKey}`, simulated: true };
    },
  };
}

async function run({ closes, autoRecentre }) {
  const configStore = new ConfigStore(null);
  // The stock defaults on purpose: the scenario that matters is a fresh install
  // whose hardcoded 60-90 ladder may be nowhere near the live price.
  await configStore.setConfig({
    lower: DEFAULT_CONFIG.lower,
    upper: DEFAULT_CONFIG.upper,
    rungs: DEFAULT_CONFIG.rungs,
    notionalPerRungUsd: DEFAULT_CONFIG.notionalPerRungUsd,
    autoRecentre,
  });
  await configStore.setRuntime({ armed: true });

  let price = 0;
  const venue = recordingVenue(() => price);
  const store = new MemoryStore();
  const moves = [];
  let outside = 0;

  for (const close of closes) {
    price = close;
    const result = await tick({ venue, store, configStore });
    // Read back AFTER the tick, so the bar that triggers a move is judged against
    // the ladder it moved to. That is the question being asked: did this run have
    // a ladder around the market on this bar?
    const config = await configStore.getConfig();
    if (close < config.lower || close > config.upper) outside += 1;
    if (result.recentre?.applied) {
      moves.push({ at: close, from: result.recentre.from, to: result.recentre.to });
    }
  }

  const config = await configStore.getConfig();
  return { moves, outside, bars: closes.length, final: config, resting: venue.live.length };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const lines = readFileSync(args.csv, 'utf8').trim().split('\n');
  const { column, hasHeader } = closeColumn(lines[0], args.column);
  const closes = lines
    .slice(hasHeader ? 1 : 0)
    .map((line) => Number(line.split(',')[column]))
    .filter((c) => c > 0);
  if (closes.length < 2) {
    console.error(`error: ${args.csv} column ${column} yielded ${closes.length} usable closes`);
    return 1;
  }

  console.log(`${args.csv}: ${closes.length} bars, $${closes[0].toFixed(2)} -> $${closes.at(-1).toFixed(2)}\n`);
  for (const autoRecentre of [false, true]) {
    const r = await run({ closes, autoRecentre });
    const pct = ((100 * r.outside) / r.bars).toFixed(1);
    console.log(`autoRecentre=${String(autoRecentre).padEnd(5)}  ladder moved ${r.moves.length}x  `
      + `price outside the ladder on ${r.outside}/${r.bars} bars (${pct}%)  `
      + `final ${r.final.lower}-${r.final.upper}  ${r.resting} resting`);
    for (const m of r.moves) {
      console.log(`    $${m.at.toFixed(2)}: ${m.from.lower}-${m.from.upper} -> ${m.to.lower}-${m.to.upper}`);
    }
  }
  console.log('\nLadder placement only, not P&L. Historical simulation, NOT investment advice.');
  return 0;
}

main().then((code) => {
  process.exitCode = code;
}).catch((err) => {
  console.error(`error: ${err.message}`);
  process.exitCode = 1;
});
