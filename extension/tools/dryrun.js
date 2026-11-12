#!/usr/bin/env node
/**
 * Headless dry run.
 *
 * Runs the real tick — real Jupiter price, real grid engine, real risk rails,
 * real journal — with simulated fills, in Node. This is the integration gate:
 * loading an unpacked extension cannot be automated (chrome://extensions needs
 * a human), so end-to-end verification happens here instead.
 *
 *   node tools/dryrun.js                 # 3 ticks around the live SOL price
 *   node tools/dryrun.js --ticks 6       # more ticks
 *   node tools/dryrun.js --walk 4        # simulate a -4%/tick walk to force fills
 *   node tools/dryrun.js --offline 75    # no network; pin the price
 */

import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore, DEFAULT_CONFIG } from '../src/storage/store.js';
import { DryRunVenue, TriggerVenue } from '../src/venues/index.js';
import { tick } from '../src/core/engine.js';
import { DEFAULT_LIMITS } from '../src/core/risk.js';
import { snapshot } from '../src/core/pnl.js';
import { capitalRequirement, gridLevels, rungWidthBps } from '../src/core/grid.js';
import { NullSigner } from '../src/wallet/signer.js';

const args = parseArgs(process.argv.slice(2));

/** A venue that reports a price we control, so a walk can force fills. */
class ScriptedPriceVenue extends DryRunVenue {
  constructor({ inner, priceFn }) {
    super({ inner });
    this.priceFn = priceFn;
  }

  async getPrice() {
    return this.priceFn();
  }

  async getDecimals() {
    return { base: 9, quote: 6 };
  }
}

async function main() {
  const configStore = new ConfigStore(null); // in-memory: no chrome.storage in Node
  const store = new MemoryStore();

  let price;
  if (args.offline != null) {
    price = Number(args.offline);
    console.log(`price pinned to $${price} (offline)`);
  } else {
    const live = new TriggerVenue({
      baseMint: DEFAULT_CONFIG.baseMint,
      quoteMint: DEFAULT_CONFIG.quoteMint,
      userPubkey: 'DRYRUN00000000000000000000000000000000000000',
      signer: new NullSigner(),
    });
    price = await live.getPrice();
    console.log(`live ${DEFAULT_CONFIG.baseSymbol} price: $${price.toFixed(4)}`);
  }

  // Centre a grid on the current price so rungs straddle the market.
  const lower = round(price * 0.85);
  const upper = round(price * 1.15);
  const config = await configStore.setConfig({
    lower,
    upper,
    rungs: 7,
    notionalPerRungUsd: 12,
    spacing: 'geom',
  });
  await configStore.setRuntime({ armed: true, killSwitch: false });

  const levels = gridLevels(config).map((l) => Number(l.toFixed(4)));
  const req = capitalRequirement({ config, price });
  console.log(`\ngrid ${lower}–${upper}, ${config.rungs} rungs, $${config.notionalPerRungUsd}/rung`);
  console.log(`levels: ${levels.join('  ')}`);
  console.log(`rung width: ${rungWidthBps(config).toFixed(1)} bps`);
  console.log(
    `capital needed: $${req.totalUsd.toFixed(2)} quote (bids only; exits are funded by the ` +
      `${req.baseQty.toFixed(4)} base those bids acquire)`,
  );

  const walkPct = Number(args.walk ?? 0);
  const oscPct = Number(args.osc ?? 0);
  const ticks = Number(args.ticks ?? 3);
  let step = 0;
  let lastPrice = price;

  /**
   * `--walk` trends one direction, which fills bids but never their exits.
   * `--osc` walks down then back up, so a round trip actually closes — the only
   * way to see whether the grid captures its rung width.
   */
  const priceFn = () => {
    if (oscPct) {
      const half = Math.max(1, Math.floor(ticks / 2));
      const leg = step <= half ? step : half - (step - half);
      return price * (1 - (oscPct / 100) * leg);
    }
    return price * (1 - (walkPct / 100) * step);
  };

  const venue = new ScriptedPriceVenue({
    inner: { id: 'scripted', kind: 'spot', capabilities: { canPlaceLive: false }, getCarryCosts: async () => [] },
    priceFn,
  });

  // No seeded inventory: exits are self-funding now, so the grid must acquire
  // its own base by filling bids first. That makes this an honest run.
  for (step = 0; step < ticks; step++) {
    const r = await tick({ venue, store, configStore, limits: DEFAULT_LIMITS });
    if (r.errors?.length || !Number.isFinite(r.price) || r.price <= 0) throw new Error(`tick ${step + 1} failed; inspect the safe tick diagnostic`);
    lastPrice = r.price;
    const filled = (await store.allFills()).length
    console.log(
      `\ntick ${step + 1}  price $${r.price.toFixed(4)}  placed ${r.placed.length}  ` +
        `rejected ${r.rejected.length}  fills ${filled}  ` +
        `net ${Number.isFinite(r.pnl?.totalNetUsd) ? '$' + r.pnl.totalNetUsd.toFixed(4) : 'unavailable'}`,
    );
    for (const p of r.placed) console.log(`    + ${p.intentKey}`);
    for (const rej of r.rejected) console.log(`    - ${rej.intent.intentKey}: ${rej.reasons[0]}`);
    for (const e of r.errors) console.log(`    ! ${e.error}`);
    if (r.lastTickDeltaMs != null) console.log(`    wake delta: ${r.lastTickDeltaMs}ms`);
  }

  const fills = await store.allFills();
  const intents = await store.allIntents();
  console.log(`\njournal: ${intents.length} intents, ${fills.length} fills`);
  const byStatus = {};
  for (const i of intents) byStatus[i.status] = (byStatus[i.status] ?? 0) + 1;
  console.log(`statuses: ${JSON.stringify(byStatus)}`);

  // The gate is the CLOSED round trips, net of fees. The per-tick `net` above
  // also marks open lots to the last price, so it can be negative while every
  // closed round trip is positive.
  const snap = snapshot({ fills, markPriceUsd: lastPrice });
  if (!snap.accountingComplete) throw new Error('dry-run accounting evidence is incomplete');
  if (args['assert-economics'] && (!(snap.roundTripCount > 0) || !(snap.realizedNetUsd > 0))) throw new Error('economics gate needs a positive closed round trip net of costs');
  console.log(
    `closed round trips: ${snap.roundTripCount}  gross $${snap.realizedGrossUsd.toFixed(4)}  ` +
      `fees $${snap.realizedFeeUsd.toFixed(4)}  net $${snap.realizedNetUsd.toFixed(4)}  ` +
      `unknown-fee fills ${fills.filter((f) => f.feeUnknown).length}`,
  );
}

function round(n) {
  return Number(n.toFixed(4));
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i].startsWith('--') ? argv[i].slice(2) : '';
    if (!['ticks', 'walk', 'osc', 'offline', 'assert-economics'].includes(key)) throw new Error('unknown dry-run flag');
    if (key === 'assert-economics') { out[key] = true; continue; }
    const raw = argv[++i];
    if (typeof raw !== 'string' || !raw.trim() || raw.startsWith('--')) throw new Error(`--${key} needs a value`);
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new Error(`--${key} must be finite`);
    out[key] = value;
  }
  if (!Number.isSafeInteger(out.ticks ?? 3) || (out.ticks ?? 3) < 1 || (out.ticks ?? 3) > 100000) throw new Error('ticks must be a positive integer at most 100000');
  if (out.offline !== undefined && out.offline <= 0) throw new Error('offline price must be positive');
  return out;
}

main().catch((err) => {
  console.error('dry run failed:', err.message);
  process.exitCode = 1;
});
