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

import { tick } from './engine.js';
import { planGrid, gridLevels, capitalRequirement, rungWidthBps, expectedRoundTripUsd } from './grid.js';
import { DEFAULT_LIMITS, dayKey } from './risk.js';
import { snapshot, equityCurve, maxDrawdown, fillsToCsv } from './pnl.js';
import { INTENT_STATUS } from '../storage/store.js';
import { MODE, leverageFeasibility } from '../venues/index.js';
import { createSessionKey } from '../wallet/signer.js';

/** Argument types the surfaces know how to coerce. */
export const TYPE = { STRING: 'string', NUMBER: 'number', BOOL: 'bool', JSON: 'json' };

/**
 * @typedef {object} Deps
 * @property {object} store        Store | MemoryStore | FileStore
 * @property {object} configStore  ConfigStore
 * @property {function} buildVenue () => venue, already wired with signer + key
 * @property {function} [clock]
 * @property {function} [log]
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

/* ---------------------------------------------------------------- registry -- */

export const COMMANDS = {
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
      const resting = (await deps.store.allIntents())
        .filter((i) => i.status === INTENT_STATUS.RESTING)
        .map((i) => i.intentKey);
      const { intents, skipped } = planGrid({
        config,
        price,
        openIntentKeys: resting,
        openLots: pnl.openLots,
      });
      return { price, intents, skipped, restingCount: resting.length };
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
      { name: 'slippageBps', type: TYPE.NUMBER },
      { name: 'leverage', type: TYPE.NUMBER },
      { name: 'marginSource', type: TYPE.STRING },
      { name: 'tickSeconds', type: TYPE.NUMBER },
      { name: 'userPubkey', type: TYPE.STRING },
      { name: 'baseMint', type: TYPE.STRING },
      { name: 'quoteMint', type: TYPE.STRING },
    ],
    async handler({ deps, args }) {
      const { patch, ...flat } = args;
      const merged = { ...(patch ?? {}), ...flat };
      if (Object.keys(merged).length === 0) {
        throw new CommandError('nothing to set — pass --patch or a named field', 400);
      }
      if (merged.mode && !Object.values(MODE).includes(merged.mode)) {
        throw new CommandError(`mode must be one of ${Object.values(MODE).join(', ')}`, 400);
      }
      return { config: await deps.configStore.setConfig(merged) };
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

  /* ---- lifecycle ---- */

  arm: {
    describe: 'Allow the engine to place orders. Live modes require confirmLive.',
    params: [
      { name: 'confirmLive', type: TYPE.BOOL, describe: 'Required to arm any non-dry-run mode.' },
    ],
    async handler({ deps, args }) {
      const config = await deps.configStore.getConfig();
      const runtime = await deps.configStore.getRuntime();
      if (runtime.killSwitch) {
        throw new CommandError('kill switch is engaged — clearKill first', 409);
      }
      if (config.mode !== MODE.DRY_RUN && !args.confirmLive) {
        throw new CommandError(
          `mode is "${config.mode}" and will spend real funds — re-run with confirmLive`,
          412,
        );
      }
      return { runtime: await deps.configStore.setRuntime({ armed: true }) };
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
      const count = Math.max(1, Math.min(50, args.count ?? 1));
      const limits = { ...DEFAULT_LIMITS, ...(await deps.configStore.get('limits', {})) };
      const results = [];
      for (let i = 0; i < count; i++) {
        const venue = await deps.buildVenue();
        const result = await tick({
          venue,
          store: deps.store,
          configStore: deps.configStore,
          limits,
          clock: deps.clock,
          log: deps.log,
        });
        results.push({ ...result, pnl: result.pnl ? summarisePnl(result.pnl) : null });
      }
      await deps.configStore.set('lastTick', results.at(-1));
      return count === 1 ? results[0] : { ticks: results };
    },
  },

  cancelOrder: {
    describe: 'Cancel one resting order on the venue and mark its intent cancelled.',
    params: [{ name: 'venueOrderId', type: TYPE.STRING, required: true }],
    async handler({ deps, args }) {
      const venue = await deps.buildVenue();
      const result = await venue.cancelOrder({ venueOrderId: args.venueOrderId });
      const intent = (await deps.store.allIntents()).find(
        (i) => i.venueOrderId === args.venueOrderId,
      );
      if (intent) {
        await deps.store.updateIntent(intent.intentKey, { status: INTENT_STATUS.CANCELLED });
      }
      return { result, intentKey: intent?.intentKey ?? null };
    },
  },

  /* ---- destructive ---- */

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
  const command = COMMANDS[name];
  if (!command) {
    throw new CommandError(`unknown command "${name}". Known: ${COMMAND_NAMES.join(', ')}`, 404);
  }

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

  return command.handler({ deps, args });
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
