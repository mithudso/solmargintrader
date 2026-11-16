import test from 'node:test';
import assert from 'node:assert/strict';
import { decodeHistory, decodeQuote, JupiterFeed, JUPITER_ENDPOINTS, TIMEFRAMES } from '../src/1000x/feed.js';

const BASE = 1_794_830_400_000; // Explicit synthetic clock; divisible by one minute.
const MARKET = { symbol: 'SOL', feedId: 6, closed: false,
  address: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS' };
const response = (payload, status = 200) => new Response(JSON.stringify(payload), { status });
const flush = async () => { for (let i = 0; i < 30; i += 1) await Promise.resolve(); };

function history(now = BASE, count = 5, missing = []) {
  const last = Math.floor(now / 60_000) * 60 - 60;
  const t = Array.from({ length: count }, (_, i) => last - (count - i - 1) * 60)
    .filter((time) => !missing.includes(time));
  return { s: 'ok', t, o: t.map(() => 70), h: t.map(() => 72), l: t.map(() => 69), c: t.map(() => 71) };
}

function message(now = BASE, price = '7137601654', feedId = 6) {
  return { type: 'streamUpdated', subscriptionId: 1, parsed: {
    timestampUs: String(now * 1000),
    priceFeeds: [{ priceFeedId: feedId, price, exponent: -8, feedUpdateTimestamp: now * 1000 }],
  } };
}

function harness({ now = BASE + 10_000, catalog = { markets: [MARKET] }, readHistory,
  fetchImpl, WebSocketImpl } = {}) {
  let nextId = 0;
  const timers = new Map();
  const sockets = [];
  const snapshots = [];
  const requests = [];
  const state = { now };
  class Socket {
    sent = [];
    closed = false;
    constructor(url) { this.url = url; sockets.push(this); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.closed = true; }
    open() { this.onopen?.(); }
    emit(payload) { this.onmessage?.({ data: JSON.stringify(payload) }); }
    disconnect() { this.onclose?.(); }
  }
  const dependencies = {
    fetchImpl: fetchImpl ?? (async (url, options) => {
      requests.push({ url, options });
      return url === JUPITER_ENDPOINTS.markets ? response(catalog)
        : response(readHistory ? await readHistory(state.now) : history(state.now));
    }),
    WebSocketImpl: WebSocketImpl ?? Socket,
    clock: () => state.now,
    setTimeoutImpl: (callback, ms) => {
      const id = ++nextId;
      timers.set(id, { at: state.now + ms, callback });
      return id;
    },
    clearTimeoutImpl: (id) => timers.delete(id),
  };
  const feed = new JupiterFeed({ symbol: 'SOL', intervalSec: 60,
    onUpdate: (snapshot) => snapshots.push(snapshot), ...dependencies });
  return {
    feed, snapshots, sockets, requests, state, timers, dependencies,
    async advance(ms) {
      const until = state.now + ms;
      for (;;) {
        const due = [...timers.entries()].filter(([, timer]) => timer.at <= until)
          .sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        state.now = due[1].at;
        timers.delete(due[0]);
        due[1].callback();
        await flush();
      }
      state.now = until;
      await flush();
    },
  };
}

test('observed SOL Pyth shape scales integer price and microsecond timestamp', () => {
  const parsed = decodeQuote(message(BASE), { feedId: 6, nowMs: BASE + 20 });
  assert.equal(parsed.price, 71.37601654);
  assert.equal(parsed.exchangeMs, BASE);
  assert.equal(parsed.receivedMs, BASE + 20);
  assert.deepEqual(TIMEFRAMES.map((entry) => entry.seconds), [60, 900, 3600]);
});

test('quote decoding refuses wrong feed/subscription, duplicate feed IDs, unsafe values and stale/future time', () => {
  const options = { feedId: 6, nowMs: BASE };
  const invalid = [
    message(BASE, '71', 1), message(BASE + 1), message(BASE - 10_000),
    message(BASE, '9007199254740992'), message(BASE, 'NaN'), message(BASE, '0'),
    { ...message(), subscriptionId: 2 },
    { ...message(), parsed: { priceFeeds: [...message().parsed.priceFeeds, ...message().parsed.priceFeeds] } },
  ];
  const badExponent = message(); badExponent.parsed.priceFeeds[0].exponent = -13;
  invalid.push(badExponent);
  for (const payload of invalid) assert.equal(decodeQuote(payload, options), null);
});

test('history sorts UTC seconds, deduplicates identical rows and marks gaps', () => {
  const t = BASE / 1000;
  const payload = { s: 'ok', t: [t - 60, t - 180, t - 60], o: [1, 1, 1],
    h: [3, 3, 3], l: [1, 1, 1], c: [2, 2, 2], v: [0, 0, 0] };
  const candles = decodeHistory(payload, { intervalSec: 60, nowMs: BASE });
  assert.deepEqual(candles.map((candle) => candle.time), [t - 180, t - 60]);
  assert.equal(candles[1].close, 2);
  assert.equal(candles[1].gapBefore, true);
  assert.equal(candles[0].gapBefore, false);
  assert.equal(candles[1].closed, true);
  assert.equal(candles[1].volume, 0);
});

test('conflicting duplicate history rows fail closed instead of selecting an arbitrary close', () => {
  const t = BASE / 1000 - 60;
  const payload = { s: 'ok', t: [t, t], o: [1, 1], h: [3, 3], l: [1, 1], c: [2, 3] };
  assert.throws(() => decodeHistory(payload, { intervalSec: 60, nowMs: BASE }),
    /conflicting_history_duplicate/);
});

test('history missing volume stays unavailable and current bucket stays developing', () => {
  const t = BASE / 1000;
  const candles = decodeHistory({ s: 'ok', t: [t], o: [1], h: [2], l: [1], c: [2] },
    { intervalSec: 60, nowMs: BASE + 100 });
  assert.equal(candles[0].closed, false);
  assert.equal('volume' in candles[0], false);
  assert.deepEqual(decodeHistory({ s: 'no_data' }, { intervalSec: 60, nowMs: BASE }), []);
});

test('malformed column lengths, OHLC bounds, timestamp units, volume and nonfinite inputs fail closed', () => {
  const fixture = history();
  const variants = [
    { ...fixture, c: [] }, { ...fixture, h: fixture.h.map(() => 1) },
    { ...fixture, t: fixture.t.map((t) => t * 1000) },
    { ...fixture, t: fixture.t.map((t) => t + 1) },
    { ...fixture, l: fixture.l.map(() => NaN) },
    { ...fixture, v: fixture.t.map(() => -1) },
  ];
  for (const payload of variants) assert.throws(() => decodeHistory(payload,
    { intervalSec: 60, nowMs: BASE }), /invalid_history/);
});

test('start binds catalog feed identity, fetches history, and sends only the public read subscription', async () => {
  const h = harness();
  await h.feed.start();
  assert.equal(h.sockets[0].url, JUPITER_ENDPOINTS.stream);
  h.sockets[0].open();
  assert.deepEqual(h.sockets[0].sent, [{ type: 'subscribe', subscriptionId: 1,
    channel: 'fixed_rate@200ms', priceFeedIds: [6],
    properties: ['price', 'exponent', 'feedUpdateTimestamp'], formats: [], ignoreInvalidFeeds: false }]);
  h.sockets[0].emit(message(h.state.now));
  const snapshot = h.feed.getSnapshot();
  assert.equal(snapshot.status, 'live');
  assert.equal(snapshot.symbol, 'SOL');
  assert.equal(snapshot.source, 'Jupiter Pyth oracle USD');
  assert.equal(snapshot.lastHistoryMs, h.state.now);
  assert.equal(snapshot.candles.at(-1).partial, true);
  assert.equal(snapshot.candles.at(-1).closed, false);
  for (const request of h.requests) {
    assert.equal(request.options.method, 'GET');
    assert.equal(request.options.credentials, 'omit');
    assert.equal(request.options.redirect, 'error');
    assert.equal(/users|wallet|account|transaction|execute/.test(request.url), false);
  }
  const url = new URL(h.requests[1].url);
  assert.equal(url.searchParams.get('symbol'), 'SOLUSD');
  assert.equal(url.searchParams.get('resolution'), '1');
  assert.equal(Number(url.searchParams.get('to')), Math.floor(h.state.now / 1000) + 1);
  h.feed.stop();
});

test('browser platform functions receive globalThis rather than the JupiterFeed object', async () => {
  const h = harness();
  const feed = new JupiterFeed({ symbol: 'SOL', intervalSec: 60, ...h.dependencies,
    fetchImpl: function (url, options) {
      assert.equal(this, globalThis);
      return h.dependencies.fetchImpl(url, options);
    },
    setTimeoutImpl: function (callback, ms) {
      assert.equal(this, globalThis);
      return h.dependencies.setTimeoutImpl(callback, ms);
    },
    clearTimeoutImpl: function (id) {
      assert.equal(this, globalThis);
      return h.dependencies.clearTimeoutImpl(id);
    },
  });
  await feed.start();
  assert.equal(h.sockets.length, 1);
  feed.stop();
});

test('missing, duplicate, malformed and closed markets never substitute a feed', async () => {
  for (const [markets, code] of [
    [[], 'market_unavailable'], [[MARKET, MARKET], 'ambiguous_market'],
    [[{ ...MARKET, feedId: undefined }], 'invalid_market_catalog'],
    [[{ ...MARKET, closed: true }], 'market_closed'],
  ]) {
    const h = harness({ catalog: { markets } });
    await h.feed.start();
    assert.equal(h.feed.getSnapshot().error, code);
    assert.equal(h.sockets.length, 0);
    assert.equal(h.requests.length, 1);
    h.feed.stop();
  }
});

test('unsupported timeframe does no network work and snapshots cannot change feed identity', async () => {
  const h = harness();
  const feed = new JupiterFeed({ symbol: 'SOL', intervalSec: 1, ...h.dependencies });
  await feed.start();
  assert.equal(feed.getSnapshot().status, 'unsupported');
  assert.equal(h.requests.length, 0);
  assert.throws(() => { h.feed.symbol = 'BTC'; }, TypeError);
  feed.stop();
  h.feed.stop();
});

test('duplicate, older, stale, future and other-feed messages do not alter bars or freshness', async () => {
  const h = harness(); await h.feed.start(); h.sockets[0].open();
  const initial = message(h.state.now);
  h.sockets[0].emit(initial);
  const before = h.feed.getSnapshot(); const events = h.snapshots.length;
  for (const payload of [initial, message(h.state.now - 1), message(h.state.now - 10_000),
    message(h.state.now + 1), message(h.state.now, '100', 1)]) h.sockets[0].emit(payload);
  assert.equal(h.snapshots.length, events);
  assert.deepEqual(h.feed.getSnapshot(), before);
  assert.throws(() => { before.candles[0].close = 999; }, TypeError);
  h.feed.stop();
});

test('a partially observed first bar stays incomplete when the next bar arrives', async () => {
  const h = harness({ now: BASE + 59_900 });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  await h.advance(200);
  h.sockets[0].emit(message(h.state.now, '7200000000'));
  const candles = h.feed.getSnapshot().candles;
  const first = candles.find((candle) => candle.time === BASE / 1000);
  assert.equal(first.closed, false);
  assert.equal(first.partial, true);
  assert.equal(candles.at(-1).partial, false);
  assert.equal(candles.at(-1).open, 72);
  h.feed.stop();
});

test('fresh quote cannot overwrite an authoritative closed-history close', async () => {
  const h = harness({ now: BASE + 100 });
  await h.feed.start(); h.sockets[0].open();
  h.sockets[0].emit(message(BASE - 100, '7300000000'));
  assert.equal(h.feed.getSnapshot().quote.price, 73);
  assert.equal(h.feed.getSnapshot().candles.at(-1).close, 71);
  h.feed.stop();
});

test('history refresh corrects an incomplete bar and preserves explicit gaps without invented rows', async () => {
  const missing = BASE / 1000 - 120;
  const h = harness({ readHistory: (now) => history(now, 5, [missing]) });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  for (let i = 0; i < 12; i += 1) {
    await h.advance(5000);
    h.sockets[0].emit(message(h.state.now));
  }
  await flush();
  const snapshot = h.feed.getSnapshot();
  assert.equal(snapshot.candles.some((candle) => candle.time === missing), false);
  assert.equal(snapshot.candles.find((candle) => candle.time === missing + 60).gapBefore, true);
  const corrected = snapshot.candles.find((candle) => candle.time === BASE / 1000);
  assert.equal(corrected.partial, false);
  assert.equal(corrected.closed, true);
  assert.equal(corrected.close, 71);
  h.feed.stop();
});

test('received and exchange freshness both gate signals, and disconnect invalidates immediately', async () => {
  const h = harness(); await h.feed.start(); h.sockets[0].open();
  h.sockets[0].emit(message(h.state.now - 1000));
  assert.equal(h.feed.getSnapshot().status, 'live');
  await h.advance(9000);
  assert.equal(h.feed.getSnapshot().status, 'stale');
  assert.equal(h.feed.getSnapshot().error, 'stale_quote');
  h.sockets[0].disconnect();
  assert.equal(h.feed.getSnapshot().status, 'stale');
  assert.equal(h.feed.getSnapshot().error, 'stream_disconnected');
  h.feed.stop();
});

test('developing-history overlap preserves WS extrema and the newest close observed during HTTP', async () => {
  let reads = 0;
  let release;
  let requestedAt;
  const h = harness({ readHistory: (now) => {
    reads += 1;
    if (reads === 1) return history(now);
    requestedAt = now;
    return new Promise((resolve) => { release = resolve; });
  } });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  for (let i = 0; i < 6; i += 1) {
    await h.advance(5000); h.sockets[0].emit(message(h.state.now));
  }
  assert.equal(typeof release, 'function');
  for (const price of ['9000000000', '6000000000', '8000000000']) {
    h.state.now += 1; h.sockets[0].emit(message(h.state.now, price));
  }
  const payload = history(requestedAt);
  payload.t.push(BASE / 1000); payload.o.push(70); payload.h.push(73); payload.l.push(68); payload.c.push(72);
  release(payload); await flush();
  const snapshot = h.feed.getSnapshot();
  assert.equal(snapshot.candles.at(-1).open, 70);
  assert.equal(snapshot.candles.at(-1).high, 90);
  assert.equal(snapshot.candles.at(-1).low, 60);
  assert.equal(snapshot.candles.at(-1).close, 80);
  assert.equal(snapshot.candles.at(-1).closed, false);
  assert.equal(snapshot.quote.price, 80);
  h.feed.stop();
});

test('a request spanning a candle boundary cannot certify its formerly developing bar', async () => {
  let reads = 0;
  let release;
  const h = harness({ now: BASE + 29_900, readHistory: (now) => {
    reads += 1;
    if (reads === 1) return history(now);
    return new Promise((resolve) => { release = resolve; });
  } });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  for (let i = 0; i < 6; i += 1) {
    await h.advance(5000); h.sockets[0].emit(message(h.state.now));
  }
  const payload = history(h.state.now);
  payload.t.push(BASE / 1000); payload.o.push(70); payload.h.push(73); payload.l.push(68); payload.c.push(72);
  await h.advance(200);
  h.sockets[0].emit(message(h.state.now));
  release(payload); await flush();
  const bar = h.feed.getSnapshot().candles.find((candle) => candle.time === BASE / 1000);
  assert.equal(bar.closed, false);
  assert.equal(h.feed.getSnapshot().error, 'history_lagging');
  h.feed.stop();
});

test('a live-stream gap forces backfill; a refused backfill stays unavailable', async () => {
  let failHistory = false;
  const h = harness({ readHistory: (now) => {
    if (failHistory) throw new Error('untrusted provider body containing private details');
    return history(now);
  } });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  failHistory = true;
  await h.advance(6000);
  h.sockets[0].emit(message(h.state.now, '7200000000'));
  assert.equal(h.feed.getSnapshot().status, 'backfilling');
  await flush();
  assert.equal(h.feed.getSnapshot().status, 'error');
  assert.equal(h.feed.getSnapshot().error, 'history_unavailable');
  assert.equal(h.feed.getSnapshot().candles.at(-1).partial, true);
  assert.equal(JSON.stringify(h.feed.getSnapshot()).includes('private details'), false);
  h.feed.stop();
});

test('reconnect overlaps history before resubscribing and stop prevents later reconnect callbacks', async () => {
  const h = harness(); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  const first = h.sockets[0]; const delayed = first.onmessage;
  first.disconnect();
  assert.equal(first.closed, true);
  assert.equal(first.onmessage, null);
  await h.advance(500);
  assert.equal(h.sockets.length, 2);
  assert.equal(h.requests.filter((request) => request.url.startsWith(JUPITER_ENDPOINTS.history)).length, 2);
  h.sockets[1].open(); h.sockets[1].emit(message(h.state.now));
  assert.equal(h.feed.getSnapshot().status, 'live');
  h.feed.stop();
  const events = h.snapshots.length;
  delayed({ data: JSON.stringify(message(h.state.now + 1)) });
  await h.advance(120_000);
  assert.equal(h.snapshots.length, events);
  assert.equal(h.sockets.length, 2);
  assert.equal(h.sockets[1].closed, true);
  assert.equal(h.timers.size, 0);
});

test('consecutive failed connections exhaust a bounded retry budget', async () => {
  const h = harness({ WebSocketImpl: class { constructor() { throw new Error('untrusted websocket error'); } } });
  await h.feed.start();
  await h.advance(20_000);
  assert.equal(h.feed.getSnapshot().status, 'error');
  assert.equal(h.feed.getSnapshot().error, 'reconnect_exhausted');
  h.feed.stop();
});

test('subscription refusal is terminal and does not repeat a denied contract', async () => {
  const h = harness(); await h.feed.start(); h.sockets[0].open();
  h.sockets[0].emit({ type: 'subscriptionError', error: 'untrusted remote error' });
  assert.equal(h.feed.getSnapshot().error, 'subscription_refused');
  await h.advance(120_000);
  assert.equal(h.sockets.length, 1);
  h.feed.stop();
});

test('stop aborts an in-flight read; a resolved response cannot publish or open a socket', async () => {
  let release;
  let signal;
  const h = harness({ fetchImpl: async (_url, options) => {
    signal = options.signal;
    return new Promise((resolve) => { release = resolve; });
  } });
  const operation = h.feed.start();
  h.feed.stop();
  assert.equal(signal.aborted, true);
  const events = h.snapshots.length;
  release(response({ markets: [MARKET] }));
  await operation;
  assert.equal(h.snapshots.length, events);
  assert.equal(h.sockets.length, 0);
  assert.equal(h.timers.size, 0);
});
