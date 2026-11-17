import test from 'node:test';
import assert from 'node:assert/strict';
import { decodeHistory, decodeQuote, JupiterFeed, JUPITER_ENDPOINTS, TIMEFRAMES, CONTEXT_HISTORY_BARS } from '../src/1000x/feed.js';
import { computeIndicators, MAX_INDICATOR_LENGTH } from '../src/1000x/indicators.js';
import { panelModel } from '../src/1000x/panel-model.js';
import { oracleInput } from '../src/1000x/oracle-model.js';

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

test('a transient initial catalog failure retries, and stop cancels the pending retry', async () => {
  let calls = 0;
  const h = harness({ fetchImpl: async (url) => {
    if (url === JUPITER_ENDPOINTS.markets) {
      calls += 1;
      if (calls === 1) throw new Error('offline');
      return response({ markets: [MARKET] });
    }
    return response(history());
  } });
  await h.feed.start();
  assert.equal(h.feed.getSnapshot().error, 'public_read_failed');
  await h.advance(10_000);
  assert.equal(calls, 2);
  assert.equal(h.sockets.length, 1);
  h.feed.stop();
  await h.advance(20_000);
  assert.equal(calls, 2);

  let stoppedCalls = 0;
  const stopped = harness({ fetchImpl: async () => { stoppedCalls += 1; throw new Error('offline'); } });
  await stopped.feed.start();
  stopped.feed.stop();
  await stopped.advance(20_000);
  assert.equal(stoppedCalls, 1);
});

test('observed SOL Pyth shape scales integer price and microsecond timestamp', () => {
  const parsed = decodeQuote(message(BASE), { feedId: 6, nowMs: BASE + 20 });
  assert.equal(parsed.price, 71.37601654);
  assert.equal(parsed.exchangeMs, BASE);
  assert.equal(parsed.receivedMs, BASE + 20);
  assert.deepEqual(TIMEFRAMES.map((entry) => entry.seconds), [60, 300, 600, 900, 1200, 3600]);
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

test('seeded and retained feed history warms the longest accepted indicator periods', async () => {
  const reads = [];
  let h;
  h = harness({ now: BASE + 59_900, fetchImpl: async (url) => {
    reads.push(url);
    if (url === JUPITER_ENDPOINTS.markets) return response({ markets: [MARKET] });
    const current = Math.floor(h.state.now / 60_000) * 60;
    const from = Number(new URL(url).searchParams.get('from'));
    const payload = history(h.state.now, (current - from) / 60);
    payload.t.push(current); payload.o.push(70); payload.h.push(72); payload.l.push(69); payload.c.push(71);
    return response(payload);
  } });
  const maximum = {
    rsi: { length: MAX_INDICATOR_LENGTH }, bop: { smoothing: MAX_INDICATOR_LENGTH },
    volty: { length: MAX_INDICATOR_LENGTH },
  };
  const assertWarm = (snapshot, phase) => {
    const closed = snapshot.candles.filter((candle) => candle.closed && !candle.partial);
    const result = computeIndicators(closed, maximum);
    const required = {
      rsi: result.rsi.latest, bop: result.bop.latest,
      voltyActiveUpper: result.volty.latest?.upper, voltyActiveLower: result.volty.latest?.lower,
      voltyNextUpper: result.volty.next?.upper, voltyNextLower: result.volty.next?.lower,
    };
    const unavailable = Object.entries(required).filter(([, value]) => !Number.isFinite(value)).map(([name]) => name);
    assert.deepEqual(unavailable, [], `${phase}: ${closed.length} closed feed bars cannot warm ${MAX_INDICATOR_LENGTH}-period indicators`);
    assert.equal(closed.length, MAX_INDICATOR_LENGTH + 2);
    assert.equal(snapshot.candles.length, MAX_INDICATOR_LENGTH + 3);
    assert.equal(snapshot.candles.at(-1).closed, false);
  };
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  assertWarm(h.feed.getSnapshot(), 'seed');
  const query = new URL(reads[1]).searchParams;
  assert.equal(Number(query.get('from')), BASE / 1000 - (MAX_INDICATOR_LENGTH + 2) * 60);
  await h.advance(200);
  h.sockets[0].emit(message(h.state.now));
  assertWarm(h.feed.getSnapshot(), 'retained after rollover');
  h.feed.stop();
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

test('newer developing history wins over a cached quote when no post-request stream data arrives', async () => {
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
  for (let i = 0; i < 5; i += 1) {
    await h.advance(5000); h.sockets[0].emit(message(h.state.now, '7100000000'));
  }
  const cachedQuote = h.feed.getSnapshot().quote;
  await h.advance(5000); // Periodic refresh starts; the last stream tick is five seconds older.
  assert.equal(typeof release, 'function');
  assert.ok(cachedQuote.exchangeMs < requestedAt);
  const payload = history(requestedAt);
  payload.t.push(BASE / 1000); payload.o.push(70); payload.h.push(85); payload.l.push(65); payload.c.push(80);
  release(payload); await flush();
  const snapshot = h.feed.getSnapshot();
  const developing = snapshot.candles.at(-1);
  assert.equal(developing.close, 80, 'An older cached quote must not overwrite the newer history close');
  assert.equal(developing.high, 85);
  assert.equal(developing.low, 65);
  assert.equal(developing.closed, false);
  assert.deepEqual(snapshot.quote, cachedQuote, 'History must not pretend that a new stream quote arrived');
  assert.equal(snapshot.lastHistoryMs, h.state.now);
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

test('instant reconnect history cannot restore live before a replacement socket supplies a valid quote', async () => {
  const h = harness(); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  const first = h.sockets[0];
  const oldMessage = first.onmessage;
  const oldOpen = first.onopen;
  const oldClose = first.onclose;
  const beforeDisconnect = h.snapshots.length;
  first.disconnect();
  await h.advance(500); // The history stub resolves instantly at the first retry.
  assert.equal(h.sockets.length, 2);
  assert.equal(h.snapshots.slice(beforeDisconnect).some((snapshot) => snapshot.status === 'live'), false,
    'Fresh history must not reuse the disconnected socket quote');
  assert.equal(h.feed.getSnapshot().quote, null);
  const beforeOldCallbacks = h.snapshots.length;
  oldMessage({ data: JSON.stringify(message(h.state.now, '7200000000')) });
  oldOpen(); oldClose();
  assert.equal(h.snapshots.length, beforeOldCallbacks);
  const replacement = h.sockets[1];
  replacement.open();
  assert.notEqual(h.feed.getSnapshot().status, 'live');
  replacement.emit(message(h.state.now, '7200000000', 1));
  replacement.emit(message(h.state.now + 1, '7200000000'));
  assert.notEqual(h.feed.getSnapshot().status, 'live');
  replacement.emit(message(h.state.now, '7200000000'));
  assert.equal(h.feed.getSnapshot().status, 'live');
  assert.equal(h.feed.getSnapshot().quote.price, 72);
  oldMessage({ data: JSON.stringify(message(h.state.now, '7300000000')) });
  oldClose();
  assert.equal(h.feed.getSnapshot().quote.price, 72);
  assert.equal(replacement.closed, false);
  h.feed.stop();
});

test('replacement socket gets a full idle grace period after the old quote times out', async () => {
  const h = harness(); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  await h.advance(20_500);
  assert.equal(h.sockets.length, 2);
  const replacement = h.sockets[1];
  replacement.open();
  await h.advance(19_000);
  assert.equal(h.sockets.length, 2, 'The prior quote receipt must not time out a newly created socket');
  assert.equal(replacement.closed, false);
  assert.notEqual(h.feed.getSnapshot().status, 'live');
  h.feed.stop();
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

function requestedHistory(url, now) {
  const query = new URL(url).searchParams, step = Number(query.get('resolution')) * 60;
  const first = Number(query.get('from')), current = Math.floor(now / 1000 / step) * step;
  const t = Array.from({ length: Math.floor((current - first) / step) + 1 }, (_, i) => first + i * step);
  return { s: 'ok', t, o: t.map(() => 70), h: t.map(() => 72), l: t.map(() => 69), c: t.map(() => 71) };
}

function contextHarness({ intervalSec = 600, minuteFailure = false, read } = {}) {
  const calls = [];
  let h;
  h = harness({ fetchImpl: async (url, options) => {
    calls.push({ url, options });
    if (url === JUPITER_ENDPOINTS.markets) return response({ markets: [MARKET] });
    if (read) return read(url, options, h.state.now);
    if (minuteFailure && new URL(url).searchParams.get('resolution') === '1') return response({}, 503);
    return response(requestedHistory(url, h.state.now));
  } });
  const feed = new JupiterFeed({ symbol: 'SOL', intervalSec, withReversalContext: true, ...h.dependencies });
  return { ...h, feed, calls };
}

test('10m chart plus bounded minute context shares one catalog and one public stream', async () => {
  const h = contextHarness(); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  const snapshot = h.feed.getSnapshot();
  assert.equal(h.sockets.length, 1);
  assert.equal(h.calls.filter(call => call.url === JUPITER_ENDPOINTS.markets).length, 1);
  assert.deepEqual(h.calls.filter(call => call.url !== JUPITER_ENDPOINTS.markets).map(call => new URL(call.url).searchParams.get('resolution')).sort(), ['1', '5']);
  assert.equal(snapshot.candles.length, MAX_INDICATOR_LENGTH + 3);
  assert.equal(snapshot.minuteCandles.length, CONTEXT_HISTORY_BARS + 1);
  assert.equal(snapshot.minuteStatus, 'ready');
  assert.ok(Object.isFrozen(snapshot.minuteCandles));
  const model = panelModel(snapshot, {}, h.state.now);
  assert.equal(model.reversal.ready, true);
  for (const frame of Object.values(model.reversal.frames)) assert.notEqual(frame.shape, 'unknown', `${frame.minutes}m context did not warm`);
  h.feed.stop(); assert.equal(h.sockets[0].closed, true); assert.equal(h.timers.size, 0);
});

test('1m chart reuses its own expanded minute seed without duplicate history reads', async () => {
  const h = contextHarness({ intervalSec: 60 }); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  assert.equal(h.calls.length, 2);
  assert.equal(h.feed.getSnapshot().candles.length, CONTEXT_HISTORY_BARS + 1);
  assert.deepEqual(h.feed.getSnapshot().minuteCandles, h.feed.getSnapshot().candles);
  h.feed.stop();
});

test('chart switching keeps the one socket and healthy minute learning even when selected history fails', async () => {
  const h = contextHarness({ read: (url, options, now) => new URL(url).searchParams.get('resolution') === '60'
    ? response({}, 503) : response(requestedHistory(url, now)) });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  const before = h.feed.getSnapshot();
  await h.feed.setInterval(3600);
  const failed = h.feed.getSnapshot();
  assert.equal(failed.status, 'error'); assert.equal(failed.streamStatus, 'live'); assert.equal(failed.minuteStatus, 'ready');
  assert.equal(oracleInput(failed, h.state.now).eligible, true);
  assert.deepEqual(failed.sourceIdentity, before.sourceIdentity); assert.equal(h.sockets.length, 1); assert.equal(h.sockets[0].closed, false);
  const minuteReads = h.calls.filter(c => new URL(c.url).searchParams.get('resolution') === '1').length;
  await h.feed.setInterval(60);
  const selectedMinute = h.feed.getSnapshot();
  assert.equal(selectedMinute.status, 'live'); assert.deepEqual(selectedMinute.minuteCandles, selectedMinute.candles);
  assert.equal(h.calls.filter(c => new URL(c.url).searchParams.get('resolution') === '1').length, minuteReads + 1);
  assert.equal(h.calls.filter(c => c.url === JUPITER_ENDPOINTS.markets).length, 1); assert.equal(h.sockets.length, 1);
  h.feed.stop();
});

test('chart loading preserves shared eligibility and an aborted obsolete chart response cannot replace the new selection', async () => {
  let delayed;
  const h = contextHarness({ read: (url, options, now) => new URL(url).searchParams.get('resolution') === '60'
    ? new Promise(resolve => { delayed = { url, options, now, resolve }; }) : response(requestedHistory(url, now)) });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  const old = h.feed.setInterval(3600); await flush(); assert.ok(delayed);
  assert.equal(h.feed.getSnapshot().status, 'backfilling'); assert.equal(oracleInput(h.feed.getSnapshot(), h.state.now).eligible, true);
  await h.feed.setInterval(300); assert.equal(delayed.options.signal.aborted, true);
  const selected = h.feed.getSnapshot();
  delayed.resolve(response(requestedHistory(delayed.url, delayed.now))); await old; await flush();
  assert.deepEqual(h.feed.getSnapshot(), selected); assert.equal(selected.intervalSec, 300);
  assert.equal(h.sockets.length, 1); assert.throws(() => h.feed.setInterval(7), /unsupported_timeframe/); h.feed.stop();
});

test('invalid shared minute history withholds all horizons while an independent selected chart remains readable', async () => {
  let failMinutes = false;
  const h = contextHarness({ read: (url, options, now) => failMinutes && new URL(url).searchParams.get('resolution') === '1'
    ? response({}, 503) : response(requestedHistory(url, now)) });
  await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now)); failMinutes = true;
  await h.feed.setInterval(3600); const snapshot = h.feed.getSnapshot();
  assert.equal(snapshot.status, 'live'); assert.equal(snapshot.minuteStatus, 'unavailable');
  for (const t of TIMEFRAMES) assert.equal(oracleInput(snapshot, h.state.now, t.seconds).eligible, false);
  h.feed.stop();
});

test('a failed minute history read leaves chart readings independent and reversal support unavailable', async () => {
  const h = contextHarness({ minuteFailure: true }); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  const snapshot = h.feed.getSnapshot(), model = panelModel(snapshot, {}, h.state.now);
  assert.equal(snapshot.status, 'live'); assert.equal(model.signalEligible, true);
  assert.equal(snapshot.minuteStatus, 'unavailable');
  assert.equal(model.reversal.ready, false); assert.equal(model.reversal.heuristic, null); assert.equal(model.reversal.momentum.ready, false);
  h.feed.stop();
});

test('reconnect invalidates minute context and fresh history cannot restore it without a replacement quote', async () => {
  const h = contextHarness(); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
  assert.equal(panelModel(h.feed.getSnapshot(), {}, h.state.now).reversal.ready, true);
  h.sockets[0].disconnect();
  assert.equal(h.feed.getSnapshot().minuteStatus, 'unavailable');
  await h.advance(500);
  assert.equal(h.sockets.length, 2); h.sockets[1].open();
  const waiting = panelModel(h.feed.getSnapshot(), {}, h.state.now);
  assert.equal(waiting.reversal.ready, false); assert.equal(waiting.reversal.heuristic, null);
  h.sockets[1].emit(message(h.state.now));
  assert.equal(panelModel(h.feed.getSnapshot(), {}, h.state.now).reversal.ready, true);
  h.feed.stop();
});

test('stop aborts both history reads and ignores both late responses without opening a stream', async () => {
  const pending = [];
  const h = contextHarness({ read: (url, options, now) => new Promise(resolve => pending.push({ url, options, now, resolve })) });
  const start = h.feed.start(); await flush(); assert.equal(pending.length, 2);
  h.feed.stop();
  assert.ok(pending.every(read => read.options.signal.aborted));
  for (const read of pending) read.resolve(response(requestedHistory(read.url, read.now)));
  await start;
  assert.equal(h.sockets.length, 0); assert.equal(h.feed.getSnapshot().error, 'feed_stopped');
  assert.equal(h.feed.getSnapshot().minuteCandles.length, 0);
});

test('minute overlap retains post-request ticks but never replays an older cached close over newer history', async () => {
  for (const postRequestTick of [false, true]) {
    let minuteReads = 0, pending;
    const h = contextHarness({ read: (url, options, now) => {
      if (new URL(url).searchParams.get('resolution') !== '1' || ++minuteReads === 1) return response(requestedHistory(url, now));
      return new Promise(resolve => { pending = { url, now, resolve }; });
    } });
    await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
    for (let i = 0; i < 5; i++) { await h.advance(5000); h.sockets[0].emit(message(h.state.now, '7100000000')); }
    await h.advance(5000); assert.ok(pending);
    if (postRequestTick) { h.state.now += 1; h.sockets[0].emit(message(h.state.now, '9000000000')); }
    const payload = requestedHistory(pending.url, pending.now);
    payload.h[payload.h.length - 1] = 85; payload.c[payload.c.length - 1] = 80;
    pending.resolve(response(payload)); await flush();
    const snapshot = h.feed.getSnapshot(), last = snapshot.minuteCandles.at(-1);
    assert.equal(last.close, postRequestTick ? 90 : 80);
    assert.equal(last.high, postRequestTick ? 90 : 85);
    assert.equal(snapshot.quote.price, postRequestTick ? 90 : 71);
    h.feed.stop();
  }
});

test('10m/20m charts resample supported5m history and refuse a missing constituent close', async () => {
  for (const intervalSec of [600, 1200]) {
    const h = contextHarness({ intervalSec }); await h.feed.start(); h.sockets[0].open(); h.sockets[0].emit(message(h.state.now));
    const snapshot = h.feed.getSnapshot();
    assert.equal(snapshot.historyIntervalSec, 300);
    assert.equal(snapshot.candles.filter(candle => candle.closed).length, MAX_INDICATOR_LENGTH + 2);
    assert.ok(snapshot.candles.every(candle => candle.time % intervalSec === 0));
    assert.ok(h.calls.filter(call => call.url !== JUPITER_ENDPOINTS.markets).every(call => ['1', '5'].includes(new URL(call.url).searchParams.get('resolution'))));
    assert.equal(panelModel(snapshot, {}, h.state.now).signalEligible, true);
    h.feed.stop();
    const missing = contextHarness({ intervalSec, read: (url, options, now) => {
      const payload = requestedHistory(url, now);
      if (new URL(url).searchParams.get('resolution') === '5') {
        const required = Math.floor(now / 1000 / intervalSec) * intervalSec - 300;
        const index = payload.t.indexOf(required);
        for (const field of ['t', 'o', 'h', 'l', 'c']) payload[field].splice(index, 1);
      }
      return response(payload);
    } });
    await missing.feed.start(); missing.sockets[0].open(); missing.sockets[0].emit(message(missing.state.now));
    const incomplete = missing.feed.getSnapshot();
    assert.notEqual(incomplete.status, 'live');
    assert.equal(panelModel(incomplete, {}, missing.state.now).signalEligible, false);
    assert.equal(incomplete.candles.some(candle => candle.time === Math.floor(missing.state.now / 1000 / intervalSec) * intervalSec - intervalSec), false);
    missing.feed.stop();
  }
});
