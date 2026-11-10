/**
 * The command registry — single source of truth for every action this project
 * can perform.
 *
 * Three surfaces drive this one registry:
 *
 *   extension  src/bg/service-worker.js  (chrome.runtime messages)
 *   CLI        tools/cli.js              (argv)
 *   HTTP API   tools/api-server.js       (POST /v1/<command>)
 *
 * Nothing may be reachable from one surface and not the others. A parity test
 * enumerates this object and fails if any surface is missing a command, which
 * is the mechanism that stops the extension and the CLI from drifting apart.
 *
 * Handlers are pure of transport: they receive resolved dependencies and plain
 * arguments, and return plain JSON-serialisable data. They never touch
 * chrome.*, process.*, Request or Response.
 */

import { tick, withStoreLock, stopEngine, resumeEngine, engineStopGeneration, occupiedIntentKeys } from './engine.js';
import { planGrid, gridLevels, capitalRequirement, rungWidthBps, expectedRoundTripUsd } from './grid.js';
import { DEFAULT_LIMITS, dayKey } from './risk.js';
import { snapshot, equityCurve, maxDrawdown, fillsToCsv } from './pnl.js';
import { INTENT_STATUS, DEFAULT_CONFIG } from '../storage/store.js';
import { MODE, MARGIN_SOURCE, leverageFeasibility } from '../venues/index.js';
import { createSessionKey } from '../wallet/signer.js';
import { soltuiList, soltuiCall, SOLTUI_TIMEOUT_MS } from './soltui.js';
import { DEFAULT_PREFS, prefsProblem, computeAlerts, qualifyingLeads, mergeAlerts, notifiable } from './alerts.js';
import { readHoldings } from '../market/holdings.js';
import { fetchPoolsCached, rankPools } from '../market/pools.js';
import { quote } from '../market/quote.js';
import { BASE_TOKENS, SOLANA_TOKENS, isSolanaAddress } from '../market/tokens.js';
import { isAddress } from '../market/evm.js';
import { MarketError } from '../market/net.js';
import { managerSnapshot, managerPoll, paperConfigStore, MANAGER_KEY } from './bot-manager.js';
import { controlRoomSnapshot, openControlRoom } from './control-room.js';

/** Argument types the surfaces know how to coerce. */
export const TYPE = { STRING: 'string', NUMBER: 'number', BOOL: 'bool', JSON: 'json' };

/**
 * @typedef {object} Deps
 * @property {object} store        Store | MemoryStore | FileStore
 * @property {object} configStore  ConfigStore
 * @property {function} buildVenue () => venue, already wired with signer + key
 * @property {function} [clock]
 * @property {function} [log]
 * @property {object} [soltui]    transport to the soltui host: request({op, command?, params?}, {timeoutMs}) => envelope
 */

/* ----------------------------------------------------------------- helpers -- */

async function currentPrice(deps) {
  const venue = await deps.buildVenue();
  return venue.getPrice();
}

async function pnlSnapshot(deps, { markPriceUsd } = {}) {
  const [fills, carry] = await Promise.all([deps.store.allFills(), deps.store.allCarry()]);
  const price = markPriceUsd ?? (await currentPrice(deps));
  return { pnl: snapshot({ fills, markPriceUsd: price, carryEntries: carry }), price, fills, carry };
}

/** Strip the bulky arrays a status/pnl response does not need. */
function summarisePnl(pnl) {
  const { roundTrips, openLots, ...rest } = pnl;
  return { ...rest, roundTripCount: pnl.roundTripCount, openLotCount: openLots.length };
}

const CONTEXT_FIELDS = ['mode', 'venue', 'userPubkey', 'baseMint', 'quoteMint', 'gridId'];
const LADDER_FIELDS = ['lower', 'upper', 'rungs', 'spacing', 'direction'];
const DISARM_FIELDS = [...CONTEXT_FIELDS, ...LADDER_FIELDS];
const plainObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)
  && [Object.prototype, null].includes(Object.getPrototypeOf(value));

function configPatch(args) {
  const { patch, ...flat } = args;
  const merged = { ...(patch ?? {}), ...flat };
  if (!Object.keys(merged).length) throw new CommandError('nothing to set — pass --patch or a named field', 400);
  if (Object.keys(merged).some((key) => !Object.hasOwn(DEFAULT_CONFIG, key))) {
    throw new CommandError('unknown configuration field; secrets use their dedicated command', 400);
  }
  return merged;
}

function validateConfig(config) {
  const invalid = (key) => { throw new CommandError(`invalid configuration field "${key}"`, 400); };
  for (const [key, fallback] of Object.entries(DEFAULT_CONFIG)) {
    const value = config[key];
    if (fallback === null) {
      if (value !== null && (typeof value !== 'string' || !value.trim())) invalid(key);
    } else if (typeof value !== typeof fallback || (typeof value === 'number' && !Number.isFinite(value))) invalid(key);
    if (typeof fallback === 'string' && !value.trim()) invalid(key);
  }
  if (!Object.values(MODE).includes(config.mode)) invalid('mode');
  if (!['trigger', 'perps'].includes(config.venue)) invalid('venue');
  if (!['neutral', 'long', 'short'].includes(config.direction)) invalid('direction');
  if (!Object.values(MARGIN_SOURCE).includes(config.marginSource)) invalid('marginSource');
  for (const key of ['notionalPerRungUsd', 'ttlMs', 'tickSeconds', 'minOrderUsd']) if (!(config[key] > 0)) invalid(key);
  if (config.leverage < 1) invalid('leverage');
  for (const key of ['slippageBps', 'deadbandBps', 'recentreDriftBps']) if (config[key] < 0) invalid(key);
  if (!(config.recentreSpanPct > 0 && config.recentreSpanPct < 1)) invalid('recentreSpanPct');
  if (config.baseMint === config.quoteMint) invalid('quoteMint');
  try { gridLevels(config); } catch { throw new CommandError('invalid grid bounds, rung count or spacing', 400); }
}

/* ------------------------------------------------------- market helpers -- */

const PREFS_KEY = 'prefs';
const SCAN_KEY = 'scan';
const ACKS_KEY = 'alertAcks';
const MAX_ACKS = 500;
const MAX_ALERT_ID = 200;

// Scans and acknowledgements run one at a time per store: scanAlerts is unlocked
// (it reads the network for up to a minute and must not stall the engine), so two
// overlapping scans would each write the whole scan and lose the other's fresh
// set, and an "acknowledge all" could miss the alerts a running scan is writing.
const alertQueues = new WeakMap();
function alertQueue(configStore, fn) {
  const tail = alertQueues.get(configStore) ?? Promise.resolve();
  const run = tail.then(fn, fn);
  alertQueues.set(configStore, run.catch(() => {}));
  return run;
}

async function readPrefs(deps) {
  const stored = await deps.configStore.get(PREFS_KEY, {});
  const values = plainObject(stored) ? stored : {};
  return Object.fromEntries(Object.entries(DEFAULT_PREFS).map(([k, v]) => [k, Object.hasOwn(values, k) ? values[k] : v]));
}

/** A market read failure is a 502 with the source named, never an unhandled throw. */
async function market(fn) {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof MarketError) throw new CommandError(err.message, 502);
    if (err instanceof RangeError) throw new CommandError(err.message, 400);
    throw err;
  }
}

/**
 * The addresses to read: preferences first, then the grid's wallet pubkey for
 * Solana, then the public addresses saved in soltui. Each answer says where it
 * came from so the page never shows a balance for an address nobody chose.
 */
async function resolveAddresses(deps, prefs) {
  const out = { baseAddress: prefs.baseAddress, solanaAddress: prefs.solanaAddress, from: {} };
  if (out.baseAddress) out.from.base = 'preferences';
  if (out.solanaAddress) out.from.solana = 'preferences';
  if (!out.solanaAddress) {
    const { userPubkey } = await deps.configStore.getConfig();
    if (isSolanaAddress(userPubkey)) { out.solanaAddress = userPubkey; out.from.solana = 'grid wallet pubkey'; }
  }
  if ((!out.baseAddress || !out.solanaAddress) && deps.soltui) {
    const env = await soltuiCall(deps, { command: 'wallet.addresses', params: {}, timeoutMs: SOLTUI_TIMEOUT_MS.probe });
    if (env.ok) {
      if (!out.baseAddress && isAddress(env.result?.base_address)) { out.baseAddress = env.result.base_address; out.from.base = 'soltui settings'; }
      if (!out.solanaAddress && isSolanaAddress(env.result?.solana_address)) { out.solanaAddress = env.result.solana_address; out.from.solana = 'soltui settings'; }
    }
  }
  return out;
}

/** One soltui read for the scan: the result, or null with the reason noted. */
async function soltuiRead(deps, command, params, notes) {
  if (!deps.soltui) { notes.push(`${command}: soltui is not connected on this surface`); return null; }
  const env = await soltuiCall(deps, { command, params, timeoutMs: SOLTUI_TIMEOUT_MS.quick });
  if (!env.ok) { notes.push(`${command}: ${env.error?.message ?? 'failed'}`); return null; }
  return env.result;
}

/* ---------------------------------------------------------------- registry -- */

export const COMMANDS = {
  openLiveWindow: {
    describe: 'Open or reuse a floating live view. An existing workspace can pin with one click.',
    params: [{ name: 'asset', type: TYPE.STRING, describe: 'Optional coin symbol.' }],
    unlocked: true,
    browserUi: true,
    handler({ deps, args }) {
      const asset = args.asset ?? 'SOL';
      if (!/^[A-Z0-9]{1,20}$/.test(asset)) throw new CommandError('Invalid signal coin', 400);
      if (!deps.liveWindows) throw new CommandError('Floating live views require the Chrome extension.', 501);
      return deps.liveWindows.open(asset);
    },
  },
  /* ---- inspection (read-only) ---- */

  status: {
    describe: 'Current mode, arm state, limits, last tick summary and venue capabilities.',
    params: [],
    readOnly: true,
    async handler({ deps }) {
      const [config, runtime, limits, lastTick] = await Promise.all([
        deps.configStore.getConfig(),
        deps.configStore.getRuntime(),
        deps.configStore.get('limits', {}).then((l) => ({ ...DEFAULT_LIMITS, ...l })),
        deps.configStore.get('lastTick', null),
      ]);
      const venue = await deps.buildVenue();
      const feasible = leverageFeasibility({
        venue,
        leverage: config.leverage,
        marginSource: config.marginSource,
      });
      return {
        config,
        runtime,
        limits,
        lastTick,
        venue: { id: venue.id, kind: venue.kind, capabilities: venue.capabilities },
        leverageFeasible: feasible,
        today: dayKey(),
      };
    },
  },

  getConfig: {
    describe: 'Print the effective grid configuration.',
    params: [],
    readOnly: true,
    handler: ({ deps }) => deps.configStore.getConfig(),
  },

  getLimits: {
    describe: 'Print the effective risk rails.',
    params: [],
    readOnly: true,
    async handler({ deps }) {
      return { ...DEFAULT_LIMITS, ...(await deps.configStore.get('limits', {})) };
    },
  },

  levels: {
    describe: 'Grid price levels, rung width and the gross spread each round trip captures.',
    params: [],
    readOnly: true,
    async handler({ deps }) {
      const config = await deps.configStore.getConfig();
      const levels = gridLevels(config);
      return {
        levels,
        rungWidthBps: rungWidthBps(config),
        expectedRoundTripUsd: levels.slice(0, -1).map((level) => ({
          level,
          grossUsd: expectedRoundTripUsd({ config, level }),
        })),
      };
    },
  },

  capital: {
    describe: 'Capital the configured grid needs at the current (or given) price.',
    params: [{ name: 'price', type: TYPE.NUMBER, describe: 'Override the live price.' }],
    readOnly: true,
    async handler({ deps, args }) {
      const config = await deps.configStore.getConfig();
      const price = args.price ?? (await currentPrice(deps));
      return { price, ...capitalRequirement({ config, price }) };
    },
  },

  price: {
    describe: 'Live mark price for the configured base mint.',
    params: [],
    readOnly: true,
    async handler({ deps }) {
      const config = await deps.configStore.getConfig();
      return { mint: config.baseMint, symbol: config.baseSymbol, priceUsd: await currentPrice(deps) };
    },
  },

  plan: {
    describe: 'Orders the grid WOULD place right now. Computes only; places nothing.',
    params: [{ name: 'price', type: TYPE.NUMBER, describe: 'Override the live price.' }],
    readOnly: true,
    async handler({ deps, args }) {
      const config = await deps.configStore.getConfig();
      const price = args.price ?? (await currentPrice(deps));
      const { pnl } = await pnlSnapshot(deps, { markPriceUsd: price });
      const resting = occupiedIntentKeys(await deps.store.allIntents());
      const { intents, skipped, recentre } = planGrid({
        config,
        price,
        openIntentKeys: resting,
        openLots: pnl.openLots,
      });
      // recentre is reported, not applied: `plan` is readOnly, so a move it
      // previews is uncommitted until a real tick books orders on it.
      return { price, intents, skipped, restingCount: resting.length, recentre };
    },
  },

  pnl: {
    describe: 'Full P&L: realized, unrealized, fees, equity curve and max drawdown.',
    params: [{ name: 'price', type: TYPE.NUMBER, describe: 'Override the mark price.' }],
    readOnly: true,
    async handler({ deps, args }) {
      const { pnl, price, carry } = await pnlSnapshot(deps, { markPriceUsd: args.price });
      const curve = equityCurve({ roundTrips: pnl.roundTrips, carryEntries: carry });
      return {
        markPriceUsd: price,
        ...summarisePnl(pnl),
        drawdown: maxDrawdown(curve),
        equityCurve: curve,
        roundTrips: pnl.roundTrips,
      };
    },
  },

  data: {
    describe: 'Raw journal: intents, fills, carry entries and recent events.',
    params: [{ name: 'limit', type: TYPE.NUMBER, describe: 'Cap on events returned (default 50).' }],
    readOnly: true,
    async handler({ deps, args }) {
      const [intents, fills, carry, events] = await Promise.all([
        deps.store.allIntents(),
        deps.store.allFills(),
        deps.store.allCarry(),
        deps.store.recentEvents(args.limit ?? 50),
      ]);
      return { intents, fills, carry, events };
    },
  },

  exportCsv: {
    describe: 'Fill log as CSV — the same export the dashboard button produces.',
    params: [],
    readOnly: true,
    async handler({ deps }) {
      const fills = await deps.store.allFills();
      return { csv: fillsToCsv(fills), rows: fills.length };
    },
  },

  venueInfo: {
    describe: 'Venue id, kind and capabilities, including why a venue is read-only.',
    params: [],
    readOnly: true,
    async handler({ deps }) {
      const venue = await deps.buildVenue();
      return { id: venue.id, kind: venue.kind, capabilities: venue.capabilities };
    },
  },

  /* ---- portfolio, discovery, swaps and alerts (src/market, src/core/alerts.js) ---- */

  getPrefs: {
    describe: 'Wallet addresses and alert thresholds used by holdings, the alert scan and notifications.',
    params: [],
    readOnly: true,
    handler: ({ deps }) => readPrefs(deps),
  },

  setPrefs: {
    describe: 'Merge a patch into the preferences. Addresses are public addresses only; pass null to clear one.',
    params: [
      { name: 'patch', type: TYPE.JSON, describe: 'JSON object of preference fields.' },
      { name: 'baseAddress', type: TYPE.STRING, describe: 'Public Base (EVM) address, 0x + 40 hex.' },
      { name: 'solanaAddress', type: TYPE.STRING, describe: 'Public Solana address (base58).' },
      { name: 'alertsEnabled', type: TYPE.BOOL, describe: 'Run the periodic alert scan and raise notifications.' },
      { name: 'alertIntervalMinutes', type: TYPE.NUMBER, describe: 'Minutes between scans, 15-1440.' },
      { name: 'minAprGainPct', type: TYPE.NUMBER, describe: 'APR points a scouted (modelled) pool must beat a position by.' },
      { name: 'minIdleUsd', type: TYPE.NUMBER, describe: 'Idle Base stablecoins worth an alert.' },
      { name: 'minNetAprPct', type: TYPE.NUMBER, describe: 'Modelled net APR worth moving idle capital for.' },
      { name: 'leadMinTvlUsd', type: TYPE.NUMBER, describe: 'TVL floor for a quoted pool lead.' },
      { name: 'leadMinApyPct', type: TYPE.NUMBER, describe: '30-day mean APY floor for a quoted pool lead.' },
      { name: 'notifyLeads', type: TYPE.BOOL, describe: 'Also notify for quoted (DefiLlama) pool leads.' },
      { name: 'maxScoutAgeHours', type: TYPE.NUMBER, describe: 'Scout output older than this cannot raise an act alert (default 48).' },
      { name: 'activeStrategy', type: TYPE.STRING, describe: 'Top 5 label of the strategy in use, compared on each scan.' },
      { name: 'minSharpeGain', type: TYPE.NUMBER, describe: 'Median-Sharpe margin for a better-strategy alert.' },
    ],
    async handler({ deps, args }) {
      const { patch, ...flat } = args;
      const merged = { ...(patch ?? {}), ...flat };
      if (!Object.keys(merged).length) throw new CommandError('nothing to set — pass --patch or a named preference', 400);
      const problem = prefsProblem(merged);
      if (problem) throw new CommandError(problem, 400);
      if (merged.baseAddress != null && !isAddress(merged.baseAddress)) throw new CommandError('baseAddress must be 0x followed by 40 hex characters', 400);
      if (merged.solanaAddress != null && !isSolanaAddress(merged.solanaAddress)) throw new CommandError('solanaAddress must be a base58 Solana address', 400);
      const prefs = { ...(await readPrefs(deps)), ...merged };
      await deps.configStore.set(PREFS_KEY, prefs);
      return { prefs };
    },
  },

  holdings: {
    describe: 'Live balances and USD values at the Base and Solana addresses, read from public RPC and price APIs.',
    params: [{ name: 'chain', type: TYPE.STRING, describe: 'all (default), base or solana.' }],
    readOnly: true,
    async handler({ deps, args }) {
      const chain = args.chain ?? 'all';
      if (!['all', 'base', 'solana'].includes(chain)) throw new CommandError('chain must be all, base or solana', 400);
      const addresses = await resolveAddresses(deps, await readPrefs(deps));
      const summary = await market(() => readHoldings(deps, { ...addresses, chain }));
      return { ...summary, addressSource: addresses.from };
    },
  },

  pools: {
    describe: 'Base and Solana liquidity pools from DefiLlama, ranked. Every APY is QUOTED by DefiLlama, not measured.',
    params: [
      { name: 'chain', type: TYPE.STRING, describe: 'all (default), base or solana.' },
      { name: 'minTvlUsd', type: TYPE.NUMBER, describe: 'TVL floor (default 250000).' },
      { name: 'stableOnly', type: TYPE.BOOL, describe: 'Stablecoin pools only.' },
      { name: 'singleOnly', type: TYPE.BOOL, describe: 'Single-asset (lending/staking) pools only.' },
      { name: 'includeOutliers', type: TYPE.BOOL, describe: 'Keep rows DefiLlama flags as outliers.' },
      { name: 'search', type: TYPE.STRING, describe: 'Substring of project, symbol or pool note.' },
      { name: 'sort', type: TYPE.STRING, describe: 'apyMean30d (default), apy, apyBase or tvlUsd.' },
      { name: 'limit', type: TYPE.NUMBER, describe: 'Rows to return, 1-500 (default 50).' },
    ],
    readOnly: true,
    async handler({ deps, args }) {
      const { atMs, pools } = await market(() => fetchPoolsCached(deps));
      return {
        fetchedAtMs: atMs,
        total: pools.length,
        pools: rankPools(pools, args),
        quoted: true,
        note: 'APYs are quoted by DefiLlama and include reward emissions. Measured Aero figures come from the scout (liquidity.data).',
      };
    },
  },

  swapTokens: {
    describe: 'Tokens the swap quote accepts on each chain, with addresses and decimals.',
    params: [],
    readOnly: true,
    handler: () => ({ base: BASE_TOKENS, solana: SOLANA_TOKENS }),
  },

  swapQuote: {
    describe: 'Quote a swap (Jupiter on Solana, Aero Slipstream on Base). Quote only: sign it on the venue page it links to.',
    params: [
      { name: 'chain', type: TYPE.STRING, required: true, describe: 'base or solana.' },
      { name: 'from', type: TYPE.STRING, required: true, describe: 'Input token symbol or address (see swapTokens).' },
      { name: 'to', type: TYPE.STRING, required: true, describe: 'Output token symbol or address.' },
      { name: 'amount', type: TYPE.STRING, required: true, describe: 'Input amount as a decimal string, e.g. 0.25.' },
      { name: 'slippageBps', type: TYPE.NUMBER, describe: 'Slippage tolerance for the minimum received (default 50).' },
    ],
    readOnly: true,
    handler: ({ deps, args }) => market(() => quote(deps, args)),
  },

  overview: {
    describe: 'The last alert scan: holdings, alerts with acknowledgement, and notes. Reads storage only.',
    params: [],
    readOnly: true,
    async handler({ deps }) {
      const [scan, acks, prefs] = await Promise.all([
        deps.configStore.get(SCAN_KEY, null), deps.configStore.get(ACKS_KEY, []), readPrefs(deps),
      ]);
      const acked = new Set(Array.isArray(acks) ? acks : []);
      return {
        scan: scan ? { ...scan, alerts: (scan.alerts ?? []).map((a) => ({ ...a, acked: acked.has(a.id) })) } : null,
        prefs,
      };
    },
  },

  scanAlerts: {
    describe: 'Read holdings, the Aero scout, Top 5 and pool leads; compute and store alerts. Places nothing.',
    params: [],
    // Network reads for up to a minute, and it touches only its own storage keys;
    // alertQueue serialises it against other scans and acknowledgements.
    unlocked: true,
    handler: ({ deps }) => alertQueue(deps.configStore, async () => {
      const now = deps.clock?.() ?? Date.now();
      const prefs = await readPrefs(deps);
      const notes = [];
      const [previous, acks] = await Promise.all([deps.configStore.get(SCAN_KEY, null), deps.configStore.get(ACKS_KEY, [])]);

      const addresses = await resolveAddresses(deps, prefs);
      let holdings = null;
      try { holdings = await readHoldings(deps, addresses); } catch (err) { notes.push(`holdings: ${err.message}`); }
      const liquidity = await soltuiRead(deps, 'liquidity.data', { top: 25 }, notes);
      const top5 = await soltuiRead(deps, 'top5.list', {}, notes);

      let qualifying = [];
      try {
        const { pools } = await fetchPoolsCached(deps);
        qualifying = qualifyingLeads(pools, prefs);
      } catch (err) { notes.push(`pools: ${err.message}`); }
      const prevLeadIds = Array.isArray(previous?.leadIds) ? previous.leadIds : [];
      // The first scan that reads the feed records the set without alerting: every
      // pool would be "new". After that, even an empty set is a baseline.
      const known = new Set(prevLeadIds);
      const leads = previous?.leadsBaselined === true ? qualifying.filter((p) => !known.has(p.id)) : [];
      const feedRead = !notes.some((n) => n.startsWith('pools:'));
      const leader = top5?.configs?.find?.((c) => c.rank === 1)?.label ?? previous?.leader ?? null;

      const computed = computeAlerts({ holdings, liquidity, leads, top5, previousLeader: previous?.leader ?? null, prefs, nowMs: now });
      const scoutAge = liquidity?.scout?.generated_at ? (now / 1000 - liquidity.scout.generated_at) / 3600 : null;
      if (scoutAge !== null && scoutAge > prefs.maxScoutAgeHours) {
        notes.push(`Aero scout is ${scoutAge.toFixed(0)} h old (limit ${prefs.maxScoutAgeHours} h): no pool can raise an act alert until it reruns`);
      }
      const { alerts, fresh } = mergeAlerts(previous?.alerts, computed, now, Array.isArray(acks) ? acks : []);
      const scan = {
        scannedAtMs: now,
        holdings,
        alerts,
        leadIds: feedRead ? qualifying.map((p) => p.id) : prevLeadIds,
        leadsBaselined: previous?.leadsBaselined === true || feedRead,
        leader,
        liquidity: liquidity ? { killed: liquidity.killed, mode: liquidity.mode, positions: liquidity.positions,
          wallet: liquidity.wallet, scoutAt: liquidity.scout?.generated_at ?? null,
          bestScout: liquidity.scout?.pools?.slice?.(0, 5) ?? [] } : null,
        notes,
      };
      await deps.configStore.set(SCAN_KEY, scan);
      return { scan, fresh, notify: notifiable(alerts, fresh, prefs) };
    }),
  },

  ackAlerts: {
    describe: 'Acknowledge one alert by id, or all current alerts, so it stops showing as new.',
    // alertQueue already serializes these keys. Waiting for a scan must not
    // prevent the engine from reconciling or applying new safety limits.
    unlocked: true,
    params: [
      { name: 'id', type: TYPE.STRING, describe: 'Alert id from overview or scanAlerts.' },
      { name: 'all', type: TYPE.BOOL, describe: 'Acknowledge every current alert.' },
    ],
    handler: ({ deps, args }) => alertQueue(deps.configStore, async () => {
      if (!args.id && args.all !== true) throw new CommandError('pass --id or --all', 400);
      if (args.id && args.id.length > MAX_ALERT_ID) throw new CommandError(`an alert id is at most ${MAX_ALERT_ID} characters`, 400);
      const scan = await deps.configStore.get(SCAN_KEY, null);
      const current = (scan?.alerts ?? []).map((a) => a.id);
      const ids = args.all === true ? current : [args.id];
      const acks = new Set(await deps.configStore.get(ACKS_KEY, []));
      for (const id of ids) acks.add(id);
      // Newest last; the oldest acknowledgements fall off first.
      const kept = [...acks].slice(-MAX_ACKS);
      await deps.configStore.set(ACKS_KEY, kept);
      return { acked: ids.length, total: kept.length };
    }),
  },

  /* ---- soltui bridge (src/core/soltui.js) ---- */

  controlRoomStatus: {
    describe: 'Read managed-suite availability and machine health without starting a server.',
    params: [], readOnly: true, unlocked: true,
    handler: ({ deps }) => controlRoomSnapshot(deps),
  },

  controlRoomStart: {
    describe: 'Start the locally configured managed suite; preserves all trading and stage gates.',
    params: [], unlocked: true,
    handler: ({ deps }) => controlRoomSnapshot(deps, 'start'),
  },

  controlRoomOpen: {
    describe: 'Open the verified local control room; start its configured servers when down.',
    params: [], unlocked: true,
    handler: ({ deps }) => openControlRoom(deps),
  },

  soltuiSession: {
    describe: 'Keep dashboard replay and job state alive while this dashboard is open.',
    unlocked: true,
    params: [
      { name: 'session', type: TYPE.STRING, required: true, describe: 'Dashboard session id.' },
      { name: 'active', type: TYPE.BOOL, required: true, describe: 'Renew or release this dashboard session.' },
    ],
    handler: async ({ deps, args }) => deps.soltui?.session?.(args.session, args.active)
      ?? { available: false, connected: false },
  },

  soltuiCommands: {
    describe: 'List the soltui commands (name, params, read_only, long_running, requires_confirm) as soltui\'s own envelope.',
    params: [],
    readOnly: true,
    handler: ({ deps }) => soltuiList(deps),
  },

  soltuiCall: {
    describe:
      'Run one soltui command by its registry name and return soltui\'s envelope unchanged. '
      + 'A command that has requires_confirm in soltuiCommands needs confirm:true inside params.',
    params: [
      { name: 'command', type: TYPE.STRING, required: true, describe: 'A soltui registry name from soltuiCommands, for example liquidity.status.' },
      { name: 'params', type: TYPE.JSON, describe: 'JSON object of that command\'s parameters, forwarded untouched.' },
    ],
    // soltui commands touch no extension state, and a backtest can run for
    // minutes. Taking the engine's store lock would stall every tick behind it.
    unlocked: true,
    handler: ({ deps, args }) => soltuiCall(deps, { command: args.command, params: args.params ?? {} }),
  },

  /* ---- configuration (writes settings, never orders) ---- */

  setConfig: {
    describe: 'Merge a patch into the grid configuration.',
    params: [
      { name: 'patch', type: TYPE.JSON, describe: 'JSON object of config fields.' },
      { name: 'mode', type: TYPE.STRING, describe: `One of ${Object.values(MODE).join(', ')}.` },
      { name: 'lower', type: TYPE.NUMBER },
      { name: 'upper', type: TYPE.NUMBER },
      { name: 'rungs', type: TYPE.NUMBER },
      { name: 'spacing', type: TYPE.STRING, describe: 'geom | arith' },
      { name: 'notionalPerRungUsd', type: TYPE.NUMBER },
      { name: 'direction', type: TYPE.STRING, describe: 'neutral | long | short' },
      { name: 'autoRecentre', type: TYPE.BOOL, describe: 'Move the ladder to track price. Off by default; only acts when nothing rests and no lot is open.' },
      { name: 'recentreSpanPct', type: TYPE.NUMBER, describe: 'Half-width of a re-centred ladder, 0-1 exclusive (0.15 = 0.85x-1.15x).' },
      { name: 'recentreDriftBps', type: TYPE.NUMBER, describe: 'Slack beyond the ladder before a re-centre is worth it.' },
      { name: 'slippageBps', type: TYPE.NUMBER },
      { name: 'leverage', type: TYPE.NUMBER },
      { name: 'marginSource', type: TYPE.STRING },
      { name: 'tickSeconds', type: TYPE.NUMBER },
      { name: 'userPubkey', type: TYPE.STRING },
      { name: 'baseMint', type: TYPE.STRING },
      { name: 'quoteMint', type: TYPE.STRING },
    ],
    async handler({ deps, args }) {
      const patch = configPatch(args);
      const current = await deps.configStore.getConfig();
      const config = { ...current, ...patch };
      validateConfig(config);
      const contextChanged = CONTEXT_FIELDS.some((key) => config[key] !== current[key]);
      if (DISARM_FIELDS.some((key) => config[key] !== current[key])) {
        await deps.configStore.setRuntime({ armed: false });
      }
      if (contextChanged) {
        const [intents, fills, carry] = await Promise.all([
          deps.store.allIntents(), deps.store.allFills(), deps.store.allCarry(),
        ]);
        if (intents.length || fills.length || carry.length) {
          throw new CommandError('execution context has financial history; reconcile venue orders and explicitly reset before changing context', 409);
        }
      }
      return { config: await deps.configStore.setConfig(patch) };
    },
  },

  setLimits: {
    describe: 'Merge a patch into the risk rails.',
    params: [
      { name: 'patch', type: TYPE.JSON, describe: 'JSON object of limit fields.' },
      ...Object.keys(DEFAULT_LIMITS)
        .filter((k) => k !== 'killSwitch')
        .map((name) => ({ name, type: TYPE.NUMBER })),
    ],
    async handler({ deps, args }) {
      const { patch, ...flat } = args;
      const merged = { ...(patch ?? {}), ...flat };
      if (Object.keys(merged).length === 0) {
        throw new CommandError('nothing to set — pass --patch or a named limit', 400);
      }
      // A limit is compared against with `>` / `<=`; a NaN, string or missing
      // value makes that comparison false and silently turns the rail off. Refuse
      // it here so a bad patch is never stored (risk.js re-checks on every read).
      for (const [key, value] of Object.entries(merged)) {
        if (key === 'killSwitch') {
          if (typeof value !== 'boolean') throw new CommandError('killSwitch must be boolean', 400);
          continue;
        }
        if (!Object.hasOwn(DEFAULT_LIMITS, key)) {
          throw new CommandError(`unknown limit "${key}"`, 400);
        }
        if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 ||
            (['maxConcurrentOrders', 'maxOrdersPerTick'].includes(key) && !Number.isSafeInteger(value))) {
          throw new CommandError(
            `${key} must be a finite nonnegative number (count limits require safe integers)`,
            400,
          );
        }
      }
      const current = await deps.configStore.get('limits', {});
      const limits = { ...DEFAULT_LIMITS, ...current, ...merged };
      await deps.configStore.set('limits', limits);
      return { limits };
    },
  },

  setApiKey: {
    describe: 'Store the Jupiter API key locally. Never echoed back.',
    params: [{ name: 'apiKey', type: TYPE.STRING, required: true }],
    async handler({ deps, args }) {
      await deps.configStore.set('secrets', { apiKey: args.apiKey || undefined });
      // Deliberately returns only a length: echoing a secret puts it in shell
      // history, server logs and terminal scrollback.
      return { stored: Boolean(args.apiKey), keyLength: args.apiKey ? args.apiKey.length : 0 };
    },
  },

  createSessionKey: {
    describe:
      'Generate a dedicated full-auto signing key, encrypted under a passphrase. Fund it with grid capital only.',
    params: [{ name: 'passphrase', type: TYPE.STRING, required: true }],
    async handler({ deps, args }) {
      if (!args.passphrase || args.passphrase.length < 12) {
        throw new CommandError('passphrase must be at least 12 characters', 400);
      }
      const { pubkeyBs58, vault } = await createSessionKey({ passphrase: args.passphrase });
      await deps.configStore.set('sessionKeyVault', { pubkeyBs58, vault });
      // The vault record is returned (it contains no plaintext) but the seed
      // never leaves sealSeed().
      return {
        pubkeyBs58,
        vault,
        warning:
          'Fund this address with grid working capital only. It is a hot key held in browser/disk storage.',
      };
    },
  },

  browserManagerSnapshot: {
    describe: 'Read the registered browser-owned singleton paper grid identity.',
    params: [], readOnly: true,
    handler: async ({ deps }) => ({ snapshot: await managerSnapshot(deps) }),
  },

  browserManagerPoll: {
    describe: 'Register the browser paper owner and reconcile durable delegated controls.',
    params: [],
    async handler({ deps, stopGeneration }) {
      const before = await deps.configStore.get(MANAGER_KEY, null);
      const result = await managerPoll(deps);
      // Registration and replay do not own the legacy engine queue. Only a
      // committed paper lifecycle transition may change its execution gate.
      if (result.snapshot.generation !== before?.generation) {
        if (result.snapshot.running) resumeEngine(deps.store, stopGeneration);
        else if (before?.running && result.snapshot.mode === 'dry-run' && !result.snapshot.armed) stopEngine(deps.store);
      }
      return result;
    },
  },

  /* ---- lifecycle ---- */

  arm: {
    describe: 'Allow the engine to place orders. Live modes require confirmLive.',
    params: [
      { name: 'confirmLive', type: TYPE.BOOL, describe: 'Required to arm any non-dry-run mode.' },
    ],
    async handler({ deps, args, stopGeneration }) {
      const config = await deps.configStore.getConfig();
      const runtime = await deps.configStore.getRuntime();
      if (runtime.killSwitch) {
        throw new CommandError('kill switch is engaged — clearKill first', 409);
      }
      if (config.mode !== MODE.DRY_RUN && args.confirmLive !== true) {
        throw new CommandError(
          `mode is "${config.mode}" and will spend real funds — re-run with confirmLive`,
          412,
        );
      }
      validateConfig(config);
      const next = await deps.configStore.setRuntime({ armed: true });
      resumeEngine(deps.store, stopGeneration);
      return { runtime: next };
    },
  },

  disarm: {
    describe: 'Stop placing new orders. Resting orders are left alone.',
    params: [],
    handler: async ({ deps }) => ({ runtime: await deps.configStore.setRuntime({ armed: false }) }),
  },

  kill: {
    describe: 'Latching hard stop: disarms and blocks every rail until cleared.',
    params: [],
    handler: async ({ deps }) => ({
      runtime: await deps.configStore.setRuntime({ armed: false, killSwitch: true }),
    }),
  },

  clearKill: {
    describe: 'Release the kill switch. Does not re-arm.',
    params: [],
    handler: async ({ deps }) => ({
      runtime: await deps.configStore.setRuntime({ killSwitch: false }),
    }),
  },

  /* ---- execution ---- */

  tick: {
    describe: 'Run one full engine tick: reconcile, ingest fills, plan, admit, place.',
    params: [
      { name: 'count', type: TYPE.NUMBER, describe: 'Run this many ticks in sequence (default 1).' },
    ],
    async handler({ deps, args }) {
      if ((await deps.configStore.get(MANAGER_KEY, null))?.running) {
        await managerSnapshot(deps, { initialize: true });
      }
      const count = Math.max(1, Math.min(50, args.count ?? 1));
      if (!Number.isSafeInteger(count)) throw new CommandError('count must be an integer', 400);
      const results = [];
      for (let i = 0; i < count; i++) {
        const result = await tick({
          buildVenue: () => deps.buildVenue(),
          readLimits: async () => ({ ...DEFAULT_LIMITS, ...(await deps.configStore.get('limits', {})) }),
          store: deps.store,
          configStore: paperConfigStore(deps.configStore, typeof deps.loadedSourceHash === 'function' ? deps.loadedSourceHash : undefined),
          clock: deps.clock,
          log: deps.log,
        });
        results.push({ ...result, pnl: result.pnl ? summarisePnl(result.pnl) : null });
      }
      await withStoreLock(deps.store, () => deps.configStore.set('lastTick', results.at(-1)));
      return count === 1 ? results[0] : { ticks: results };
    },
  },

  cancelOrder: {
    describe: 'Cancel one resting order on the venue and mark its intent cancelled.',
    params: [{ name: 'venueOrderId', type: TYPE.STRING, required: true }],
    async handler({ deps, args }) {
      const intent = (await deps.store.allIntents()).find((i) => i.venueOrderId === args.venueOrderId);
      if (!intent) throw new CommandError('order is not journaled; run tick to reconcile before cancelling', 409);
      // The cancellation request itself can have an ambiguous outcome. Retain
      // occupancy even if the venue throws after accepting it.
      await deps.store.updateIntent(intent.intentKey, { status: INTENT_STATUS.UNKNOWN });
      const venue = await deps.buildVenue();
      let result;
      try { result = await venue.cancelOrder({ venueOrderId: args.venueOrderId }); }
      catch {
        deps.log?.({ level: 'warn', msg: 'cancellation outcome unknown; intent held', intentKey: intent.intentKey });
        throw new CommandError('cancellation outcome unknown; intent held for review', 502);
      }
      if (result?.cancelled === true) {
        await deps.store.updateIntent(intent.intentKey, { status: INTENT_STATUS.CANCELLED });
      } else {
        deps.log?.({ level: 'warn', msg: 'cancellation unconfirmed; intent held', intentKey: intent.intentKey });
      }
      return { result, intentKey: intent.intentKey };
    },
  },

  /* ---- destructive ---- */

  resolveIntent: {
    describe:
      'Release an UNKNOWN intent (submitted but not found on the venue) so its rung can be planned again. '
      + 'Check the venue and your wallet first: if the order actually filled or is still live, releasing it can double-fire the rung.',
    params: [
      { name: 'intentKey', type: TYPE.STRING, required: true, describe: 'Key of an UNKNOWN intent, as listed by data or the tick result.' },
      { name: 'confirm', type: TYPE.BOOL, required: true, describe: 'Must be true.' },
    ],
    destructive: true,
    async handler({ deps, args }) {
      if (args.confirm !== true) {
        throw new CommandError('releasing an unknown intent can double-fire its rung — pass confirm', 412);
      }
      const intent = (await deps.store.allIntents()).find((i) => i.intentKey === args.intentKey);
      if (!intent) throw new CommandError(`no intent with key ${args.intentKey}`, 404);
      // Only UNKNOWN: a RESTING or FILLED intent is not ambiguous, and releasing
      // it would hide a live order or a booked position from the planner.
      if (intent.status !== INTENT_STATUS.UNKNOWN) {
        throw new CommandError(
          `intent ${args.intentKey} is "${intent.status}", only "${INTENT_STATUS.UNKNOWN}" intents can be released`,
          409,
        );
      }
      await deps.store.updateIntent(args.intentKey, {
        status: INTENT_STATUS.CANCELLED,
        resolvedByHuman: true,
      });
      return { intentKey: args.intentKey, was: intent.status, now: INTENT_STATUS.CANCELLED };
    },
  },

  reset: {
    describe: 'Erase the local journal, fills, carry and events. Does NOT cancel venue orders.',
    params: [{ name: 'confirm', type: TYPE.BOOL, required: true, describe: 'Must be true.' }],
    destructive: true,
    async handler({ deps, args }) {
      if (args.confirm !== true) {
        throw new CommandError('reset erases local history — pass confirm', 412);
      }
      const before = {
        intents: (await deps.store.allIntents()).length,
        fills: (await deps.store.allFills()).length,
      };
      // Resting venue orders are deliberately untouched: wiping local records
      // does not unwind anything on chain, and pretending otherwise would be
      // worse than saying so.
      if (typeof deps.store.clearAll !== 'function') {
        throw new CommandError('this store does not support reset', 501);
      }
      await deps.configStore.setRuntime({ armed: false });
      await deps.store.clearAll();
      await deps.configStore.setRuntime({
        armed: false,
        lastTickMs: null,
        dayStartRealizedUsd: null,
        realizedPnlUsdToday: 0,
      });
      return { cleared: before, note: 'venue-side resting orders were NOT cancelled' };
    },
  },
};

/** Error carrying an HTTP-ish status so every surface can map it consistently. */
export class CommandError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = 'CommandError';
    this.status = status;
  }
}

export const COMMAND_NAMES = Object.freeze(Object.keys(COMMANDS));

/**
 * Run a command by name.
 *
 * The single entry point every surface calls. Unknown names fail loudly with
 * the list of valid ones rather than silently doing nothing.
 */
export async function runCommand({ name, args = {}, deps }) {
  const command = Object.hasOwn(COMMANDS, name) ? COMMANDS[name] : null;
  if (!command) {
    throw new CommandError(`unknown command "${name}". Known: ${COMMAND_NAMES.join(', ')}`, 404);
  }

  if (!plainObject(args)) throw new CommandError('arguments must be an object', 400);
  for (const param of command.params) {
    if (param.required && args[param.name] == null) {
      throw new CommandError(`command "${name}" requires --${param.name}`, 400);
    }
  }

  const unknown = Object.keys(args).filter((k) => !command.params.some((p) => p.name === k));
  if (unknown.length) {
    throw new CommandError(
      `command "${name}" got unknown argument(s): ${unknown.join(', ')}. Accepts: ${
        command.params.map((p) => p.name).join(', ') || '(none)'
      }`,
      400,
    );
  }

  for (const param of command.params) {
    if (!Object.hasOwn(args, param.name)) continue;
    const value = args[param.name];
    const valid = param.type === TYPE.JSON ? plainObject(value)
      : typeof value === (param.type === TYPE.BOOL ? 'boolean' : param.type) && (param.type !== TYPE.NUMBER || Number.isFinite(value));
    if (!valid) throw new CommandError(`argument "${param.name}" must have type ${param.type}`, 400);
  }

  if (name === 'setConfig') {
    const patch = configPatch(args);
    const current = await deps.configStore.getConfig();
    validateConfig({ ...current, ...patch });
    if (DISARM_FIELDS.some((key) => Object.hasOwn(patch, key) && patch[key] !== current[key])) stopEngine(deps.store);
  }
  if (name === 'kill' || name === 'disarm' || (name === 'reset' && args.confirm === true)) stopEngine(deps.store);
  if (['kill', 'disarm', 'arm', 'setConfig', 'reset'].includes(name)) {
    const manager = await deps.configStore.get(MANAGER_KEY, null);
    if (manager?.running) await deps.configStore.set(MANAGER_KEY, { ...manager, running: false, generation: manager.generation + 1 });
  }
  const stopGeneration = engineStopGeneration(deps.store);
  const operation = () => command.handler({ deps, args, stopGeneration });
  // Tick owns its per-iteration queue entry so lifecycle/limit changes can run
  // between ticks in a count=N command. Read-only commands never mutate state.
  return command.readOnly || command.unlocked || name === 'tick' ? operation() : withStoreLock(deps.store, operation);
}

/** Machine-readable description of every command — powers CLI help and API discovery. */
export function describeCommands() {
  return COMMAND_NAMES.map((name) => ({
    name,
    describe: COMMANDS[name].describe,
    readOnly: COMMANDS[name].readOnly === true,
    destructive: COMMANDS[name].destructive === true,
    params: COMMANDS[name].params.map((p) => ({
      name: p.name,
      type: p.type,
      required: p.required === true,
      describe: p.describe ?? null,
    })),
  }));
}
