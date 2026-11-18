import { ZEC_ADVICE_TTL_MS, ZEC_REMOTE_COMMANDS } from '../core/zec-advice.js';
import { MODE } from '../venues/index.js';
import { readMinutes, readSnapshot } from '../perps/market.js';
import { aggregateMinutes } from '../perps/strategies.js';
import { openWorkbenchStore, paperMarketKey } from '../perps/workbench-store.js';

const NATIVE_HOST = 'com.mitchhudson.solmargintrader_zec';
const ENABLED_KEY = 'zecBridgeEnabled';
const ADVISORIES_KEY = 'zecAdvisories';
const HISTORY_LIMIT = 12;
const SNAPSHOT_LIMIT = 64;
const CANDLE_SECONDS = 300;
const GUM = 'https://api.gum.ag/app/perps/';
const iso = ms => Number.isFinite(ms) && ms > 0 && ms < 8.64e15 ? new Date(ms).toISOString() : null;

async function paperState(openWorkbench, now) {
  const db = await openWorkbench();
  try {
    const account = (await db.getAccount(paperMarketKey('GUM', 'ZEC')))?.account;
    const position = account?.broker?.position;
    return {
      status: account ? 'available' : 'no-paper-account',
      observedAt: iso(now()),
      running: account ? account.running === true : null,
      lastObservationAt: iso(account?.lastPoint * 1000),
      position: position ? {
        side: position.direction === 1 ? 'long' : position.direction === -1 ? 'short' : null,
        openedAt: iso(position.openedAt * 1000),
        entryPrice: Number.isFinite(position.entry) && position.entry > 0 ? position.entry : null,
      } : null,
    };
  } finally {
    db.close();
  }
}

export function createZecAdvisory({
  configStore, runtime, now = Date.now, uuid = () => crypto.randomUUID(),
  market = readSnapshot, minutes = readMinutes, openWorkbench = openWorkbenchStore,
}) {
  let port = null;
  let connected = false;
  let issue = null;
  let flight = null;
  let serial = Promise.resolve();
  const issued = new Map();
  const enqueue = operation => {
    const next = serial.then(operation);
    serial = next.catch(() => {});
    return next;
  };

  async function state() {
    const enabled = await configStore.get(ENABLED_KEY, false) === true;
    return { enabled, connected: enabled && connected, issue: enabled ? issue : null };
  }

  function disconnect() {
    const previous = port;
    port = null;
    connected = false;
    issued.clear();
    try { previous?.disconnect(); } catch { /* Chrome already closed the port. */ }
  }

  function connect(handle) {
    if (port || !runtime.connectNative) return;
    try {
      const next = runtime.connectNative(NATIVE_HOST);
      port = next;
      issue = 'Connecting to the native host.';
      next.onDisconnect.addListener(() => {
        // Read Chrome's lastError in the listener without exporting its contents.
        void runtime.lastError;
        if (port !== next) return;
        disconnect();
        issue = 'Native host disconnected. Check its registration or another active Chrome profile.';
      });
      next.onMessage.addListener(async message => {
        if (port !== next) return;
        if (message?.ready === true) {
          connected = true;
          issue = null;
          return;
        }
        if (!connected || typeof message?.id !== 'string' || !ZEC_REMOTE_COMMANDS.includes(message.name)) return;
        const result = await handle(message.name, message.params);
        if (port !== next) return;
        try { next.postMessage({ id: message.id, result }); } catch { /* Port closed during the reply. */ }
      });
    } catch {
      issue = 'Native host could not be started.';
      disconnect();
    }
  }

  function reconnect(handle) {
    return enqueue(async () => {
      if ((await state()).enabled) connect(handle);
    });
  }

  function setEnabled(enabled, handle) {
    return enqueue(async () => {
      await configStore.set(ENABLED_KEY, enabled);
      if (enabled) connect(handle);
      else disconnect();
      return state();
    });
  }

  async function capture() {
    const closedTo = Math.floor(now() / 1000 / CANDLE_SECONDS) * CANDLE_SECONDS;
    const [mark, history, paper, grid] = await Promise.allSettled([
      Promise.resolve().then(async () => ({ ...await market('ZEC'), received: now() })),
      Promise.resolve().then(async () => ({
        rows: await minutes('ZEC', closedTo - HISTORY_LIMIT * CANDLE_SECONDS, closedTo),
        received: now(),
      })),
      paperState(openWorkbench, now),
      Promise.all([configStore.getConfig(), configStore.getRuntime()]),
    ]);
    const current = mark.value?.mark;
    const received = mark.value?.received;
    const age = received - current?.time * 1000;
    const fresh = age >= -5000 && age <= 20000 && Number.isFinite(current.price) && current.price > 0;
    const [config, gridRuntime] = grid.value ?? [];
    const capturedAt = now();
    const snapshot = {
      schema: 1, id: uuid(), capturedAt: iso(capturedAt),
      extensionId: runtime.id ?? null, extensionVersion: runtime.getManifest?.().version ?? null,
      fundedInventory: 'unavailable',
      expiresAt: iso(capturedAt + ZEC_ADVICE_TTL_MS), origin: 'chrome-extension',
      source: {
        venue: 'GUM', market: 'ZEC', endpoint: GUM + 'markets',
        status: fresh ? 'ok' : 'unavailable',
        observedAt: iso(received), providerAt: fresh ? iso(current.time * 1000) : null,
        markPrice: fresh ? current.price : null,
      },
      closedCandles: {
        endpoint: GUM + 'ohlcv/ZEC', seconds: CANDLE_SECONDS, observedAt: iso(history.value?.received),
        through: iso(closedTo * 1000),
        status: 'unavailable', rows: [],
      },
      engine: config && gridRuntime ? {
        scope: 'extension-grid', mode: Object.values(MODE).includes(config.mode) ? config.mode : null,
        armed: gridRuntime.armed === true, killSwitch: gridRuntime.killSwitch === true,
        lastTickAt: iso(gridRuntime.lastTickMs),
      } : null,
      paper: paper.value ?? { status: 'unavailable', observedAt: null, running: null, lastObservationAt: null, position: null },
    };
    if (history.status === 'fulfilled') {
      const rows = aggregateMinutes(history.value.rows, CANDLE_SECONDS)
        .map(({ time, open, high, low, close }) => ({ openedAt: iso(time * 1000), open, high, low, close }));
      snapshot.closedCandles.rows = rows;
      snapshot.closedCandles.status = rows.length === HISTORY_LIMIT ? 'ok' : rows.length ? 'partial' : 'unavailable';
    }
    return snapshot;
  }

  return {
    reconnect, setEnabled,
    snapshot() {
      if (!flight) {
        const startedPort = port;
        flight = capture().then(snapshot => {
          if (startedPort === port) {
            issued.set(snapshot.id, { capturedAt: snapshot.capturedAt, expiresAt: snapshot.expiresAt,
              marketStatus: snapshot.source.status, marketProviderAt: snapshot.source.providerAt });
            if (issued.size > SNAPSHOT_LIMIT) issued.delete(issued.keys().next().value);
          }
          return { snapshot };
        }).finally(() => { flight = null; });
      }
      return flight;
    },
    async list() {
      const [bridge, values] = await Promise.all([state(), configStore.get(ADVISORIES_KEY, [])]);
      return { bridge, advisories: values.map(value => ({ ...value, expired: now() >= Date.parse(value.expiresAt) })) };
    },
    submit(advice) {
      return enqueue(async () => {
        const source = issued.get(advice.snapshotId);
        if (!source || now() >= Date.parse(source.expiresAt)) return { error: 'Snapshot is unknown or expired. Request a new snapshot.', status: 409 };
        if (source.marketStatus !== 'ok' && advice.decision === 'PAPER_ONLY') {
          return { error: 'A current market mark is required for paper advice.', status: 422 };
        }
        const records = await configStore.get(ADVISORIES_KEY, []);
        const previous = records.find(record => record.snapshotId === advice.snapshotId);
        if (previous) {
          const same = Object.keys(advice).every(key => advice[key] === previous[key]);
          if (!same) return { error: 'Advice already exists for this snapshot.', status: 409 };
          return { advisory: previous };
        }
        const advisory = { ...advice, ...source, receivedAt: iso(now()) };
        await configStore.set(ADVISORIES_KEY, [advisory, ...records].slice(0, HISTORY_LIMIT));
        return { advisory };
      });
    },
  };
}
