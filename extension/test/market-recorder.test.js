import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DEPTH_BPS, ENDPOINTS, JLP_MARKETS, STREAMS, TopOfBook, USAGE, backoffMs, changed, coinbaseDepth, coinbaseRows, coinbaseSubscription, decimal, feedMap,
  hourOf, oracleSubscription, oracleTicks, parseArgs, parseCoinbaseProducts, parseFunding, parseGumMarkets, parsePool, parseYoloMarkets, relativePath,
  safeCoin } from '../tools/lib/market-recorder.mjs';

const TOOL = fileURLToPath(new URL('../tools/market-recorder.mjs', import.meta.url));

test('only public read endpoints, and every stream has a folder name', () => {
  for (const url of Object.values(ENDPOINTS)) assert.match(url, /^(https|wss):\/\/(yolo-api\.jup\.ag|perps-api\.jup\.ag|api\.gum\.ag|api\.exchange\.coinbase\.com|ws-feed\.exchange\.coinbase\.com)(\/|$)/);
  assert.deepEqual(STREAMS, ['oracle', 'perps-book', 'perps-funding', '1000x-market', 'perps-pool', 'coinbase-book', 'coinbase-trades', 'coinbase-depth']);
  for (const stream of STREAMS) assert.ok(USAGE.includes(`<COIN>/${stream}/`), `${stream} is described in the usage text`);
});

test('a coin symbol from a catalog is used as a folder name only when it is plain', () => {
  for (const good of ['BTC', 'SKHYNIX', 'A1']) assert.equal(safeCoin(good), good);
  for (const bad of ['', 'btc', '../ETC', 'A/B', 'A B', 'X'.repeat(17), null, 7, undefined, '_recorder', 'BTC\n']) assert.equal(safeCoin(bad), null, JSON.stringify(bad));
});

test('Coinbase is read only for recorded coins it has an open USD market for', () => {
  const products = parseCoinbaseProducts([
    { id: 'ZEC-USD', base_currency: 'ZEC', status: 'online', trading_disabled: false }, { id: 'BTC-USD', base_currency: 'BTC', status: 'online' },
    { id: 'BTC-EUR', base_currency: 'BTC', status: 'online' }, { id: 'ANT-USD', base_currency: 'ANT', status: 'delisted', trading_disabled: true },
    { id: 'JUP-USD', base_currency: 'JUP', status: 'online', trading_disabled: true }, { id: 'DOGE-USD', base_currency: 'DOGE', status: 'online' },
    { id: 'BTC-USD', base_currency: 'BTC', status: 'online' }, { id: '../x-USD', base_currency: '../x', status: 'online' }, null,
  ], ['BTC', 'ZEC', 'ANT', 'JUP', 'XAU']);
  assert.deepEqual(products, [{ coin: 'BTC', product: 'BTC-USD' }, { coin: 'ZEC', product: 'ZEC-USD' }]);
  assert.deepEqual(parseCoinbaseProducts([], ['BTC']), []);
  assert.throws(() => parseCoinbaseProducts({}, ['BTC']), /product list/);
  assert.deepEqual(coinbaseSubscription(['ZEC-USD', 'BTC-USD']), { type: 'subscribe', product_ids: ['BTC-USD', 'ZEC-USD'], channels: ['level2_batch', 'matches', 'heartbeat'] });
});

test('the book keeps the best bid and ask through every kind of change', () => {
  const book = new TopOfBook();
  assert.equal(book.top(), null);
  book.load([['100.5', '2'], ['100', '1'], ['99', '0']], [['101', '3'], ['102', '1']]);
  assert.deepEqual(book.top(), { bid: 100.5, ask: 101, bidSize: 2, askSize: 3 });
  assert.equal(book.levels, 4, 'a level with no size is not a level');
  book.change('buy', '100.50000000', '5');
  assert.deepEqual(book.top().bidSize, 5, 'the same price written another way is the same level');
  book.change('buy', '100.5', '0');
  assert.deepEqual(book.top(), { bid: 100, ask: 101, bidSize: 1, askSize: 3 }, 'losing the best level finds the next');
  book.change('sell', '100.2', '4');
  assert.deepEqual(book.top(), { bid: 100, ask: 100.2, bidSize: 1, askSize: 4 });
  book.change('sell', '105', '0');
  book.change('buy', '100.3', '1');
  assert.equal(book.top(), null, 'a crossed book has no usable top');
  book.change('buy', '100.3', '0');
  // Size within 30 bp of the middle (100.1): bids from 99.7997, asks to 100.4003.
  assert.deepEqual(book.depth(30), { bid: 1, ask: 4 });
  assert.deepEqual(book.depth(200), { bid: 1, ask: 8 });
  for (const bad of [['hold', '1', '1'], ['buy', '-1', '1'], ['buy', '1', '-1'], ['buy', 'x', '1'], ['sell', '1', null]]) assert.throws(() => book.change(...bad), /Coinbase book/);
  assert.throws(() => book.load('x', []), /snapshot/);
  assert.throws(() => book.load([['1']], []), /level/);
  book.load([], [['5', '1']]);
  assert.equal(book.top(), null); assert.equal(book.depth(5), null);
});

test('Coinbase messages become book rows when the top changes and trade rows once per trade', () => {
  const state = { products: new Map([['BTC-USD', 'BTC']]), books: new Map(), tops: new Map(), trades: new Map() };
  const at = '2026-11-28T10:00:00.123456Z', ms = Date.parse(at);
  assert.deepEqual(coinbaseRows({ type: 'l2update', product_id: 'BTC-USD', time: at, changes: [['buy', '1', '1']] }, state, 5), [], 'changes before the snapshot belong to no book');
  let rows = coinbaseRows({ type: 'snapshot', product_id: 'BTC-USD', time: at, bids: [['100', '1']], asks: [['101', '2']] }, state, 5);
  assert.deepEqual(rows, [{ coin: 'BTC', stream: 'coinbase-book', row: { r: 5, t: ms, bid: 100, ask: 101, bidSize: 1, askSize: 2 } }]);
  assert.deepEqual(coinbaseRows({ type: 'l2update', product_id: 'BTC-USD', time: at, changes: [['buy', '99', '7'], ['sell', '103', '1']] }, state, 6), [], 'a change away from the top writes nothing');
  rows = coinbaseRows({ type: 'l2update', product_id: 'BTC-USD', time: at, changes: [['buy', '100', '3']] }, state, 7);
  assert.deepEqual(rows[0].row, { r: 7, t: ms, bid: 100, ask: 101, bidSize: 3, askSize: 2 });
  // Trades: the one before the subscription is remembered, not recorded; a repeat is dropped.
  assert.deepEqual(coinbaseRows({ type: 'last_match', product_id: 'BTC-USD', trade_id: 10, price: '100', size: '1', side: 'buy', time: at }, state, 8), []);
  assert.deepEqual(coinbaseRows({ type: 'match', product_id: 'BTC-USD', trade_id: 10, price: '100', size: '1', side: 'buy', time: at }, state, 8), []);
  rows = coinbaseRows({ type: 'match', product_id: 'BTC-USD', trade_id: 11, price: '100.5', size: '0.25', side: 'sell', time: at }, state, 9);
  assert.deepEqual(rows, [{ coin: 'BTC', stream: 'coinbase-trades', row: { r: 9, t: ms, price: 100.5, size: 0.25, side: 'sell', tradeId: 11 } }]);
  assert.deepEqual(coinbaseRows({ type: 'match', product_id: 'BTC-USD', trade_id: 11, price: '100.5', size: '0.25', side: 'sell', time: at }, state, 9), []);
  for (const bad of [{ type: 'match', product_id: 'BTC-USD', trade_id: 12, price: '0', size: '1' }, { type: 'match', product_id: 'BTC-USD', trade_id: 12.5, price: '1', size: '1' }]) assert.deepEqual(coinbaseRows(bad, state, 9), []);
  // Other products, heartbeats and acknowledgements write nothing; a refusal or a malformed book is an error.
  for (const quiet of [{ type: 'heartbeat', product_id: 'BTC-USD' }, { type: 'subscriptions' }, { type: 'match', product_id: 'ETH-USD', trade_id: 1, price: '1', size: '1' }, null]) assert.deepEqual(coinbaseRows(quiet, state, 9), []);
  assert.throws(() => coinbaseRows({ type: 'error', message: 'rate limited' }, state, 9), /refused the stream: rate limited/);
  assert.throws(() => coinbaseRows({ type: 'l2update', product_id: 'BTC-USD', changes: 'x' }, state, 9), /no changes/);
  assert.throws(() => coinbaseRows({ type: 'l2update', product_id: 'BTC-USD', changes: [['buy', 'x', '1']] }, state, 9), /level/);
  // Depth: one row per product with a usable top, with the size near the middle on each side.
  assert.deepEqual(DEPTH_BPS, [5, 25]);
  const depth = coinbaseDepth(state, 20);
  assert.deepEqual(depth.map(row => row.coin), ['BTC']);
  assert.deepEqual(Object.keys(depth[0].row), ['r', 'bid', 'ask', 'bid5', 'ask5', 'bid25', 'ask25']);
});

test('venue numbers are read as numbers or plain decimal strings, and nothing else', () => {
  assert.deepEqual([decimal(1.5), decimal('0.06'), decimal('-3'), decimal('10000000.00')], [1.5, 0.06, -3, 10000000]);
  for (const bad of ['', '1e5', '0x10', ' 1', '1,000', NaN, Infinity, null, undefined, {}, [], true]) assert.equal(decimal(bad), null, String(bad));
});

test('the 1000x catalog lists every market with its feed, open interest and volume', () => {
  const markets = parseYoloMarkets({ markets: [
    { symbol: 'BTC', feedId: 1, longOi: '65493645000', shortOi: '124217204800', volume24h: '104187359.2896', totalVolume: '11456890534.07', closed: false, closeOnly: false },
    { symbol: 'XAU', feedId: 346, closed: true, closeOnly: true, longOi: '0', shortOi: '0' },
    { symbol: 'BTC', feedId: 9 }, { symbol: '../x', feedId: 2 }, { symbol: 'NOFEED' }, { symbol: 'BAD', feedId: -1 }, { symbol: 'FRAC', feedId: 1.5 }, null,
  ] });
  assert.deepEqual(markets.map(market => [market.coin, market.feedId, market.closed, market.closeOnly]), [['BTC', 1, false, false], ['XAU', 346, true, true]]);
  assert.deepEqual([markets[0].longOi, markets[0].shortOi, markets[0].volume24h], [65493645000, 124217204800, 104187359.2896]);
  assert.equal(markets[1].volume24h, null, 'a missing figure is null, never zero');
  for (const bad of [null, [], {}, { markets: {} }, { markets: [] }, { markets: [{ symbol: 'x' }] }]) assert.throws(() => parseYoloMarkets(bad), /catalog/);
});

test('the Perps market list gives the top of the book, mark, last trade, open interest and volume per coin', () => {
  const markets = parseGumMarkets([
    { symbol: 'ZEC', status: 'active', timestamp: 1795862208, lastUpdatedMs: 1115, bestBid: 727.5, bestAsk: 727.9, midPrice: 727.7, markPrice: 727.64, indexPrice: 727.6,
      lastTradePrice: 727.1, openInterest: 45812.6, openInterestBase: 63, volume24h: 39587.28, maxLeverage: 50 },
    { symbol: 'ANT', bestBid: 0, bestAsk: -1, markPrice: '91.34' }, { symbol: 'ZEC', bestBid: 1 }, { symbol: 'bad' }, null,
  ]);
  assert.deepEqual(markets.map(market => market.coin), ['ZEC', 'ANT']);
  assert.deepEqual(markets[0], { coin: 'ZEC', status: 'active', venueTime: 1795862208, updatedMs: 1115, bid: 727.5, ask: 727.9, mid: 727.7, mark: 727.64, index: 727.6,
    last: 727.1, openInterest: 45812.6, openInterestBase: 63, volume24h: 39587.28, maxLeverage: 50 });
  // A price that is zero, negative or missing is null: it must never be read as a price.
  assert.deepEqual([markets[1].bid, markets[1].ask, markets[1].mark, markets[1].last, markets[1].status], [null, null, 91.34, null, null]);
  for (const bad of [null, {}, [], [{ symbol: 'x' }]]) assert.throws(() => parseGumMarkets(bad), /Perps market list/);
});

test('a funding or pool read is kept only when it is for that coin and says something', () => {
  const funding = parseFunding('ZEC', { symbol: 'ZEC', rateBps1h: 0.125, fundingRate: '0.0001', predictedFundingRate: '0.0001', fundingIntervalSeconds: 28800,
    nextFundingCollectionTime: 1795881600, fundingUpdateTimestamp: 1795861981 });
  assert.deepEqual(funding, { rateBps1h: 0.125, fundingRate: 0.0001, predictedFundingRate: 0.0001, intervalSeconds: 28800, nextCollection: 1795881600, venueTime: 1795861981 });
  assert.equal(parseFunding('ZEC', { symbol: 'BTC', rateBps1h: 1 }), null);
  assert.equal(parseFunding('ZEC', { symbol: 'ZEC' }), null);
  assert.equal(parseFunding('ZEC', null), null);
  const pool = parsePool({ longBorrowRatePercent: '0.0015', shortBorrowRatePercent: '0.0007', longUtilizationPercent: '10.19', shortUtilizationPercent: '66.77',
    openFeePercent: '0.06', maxPriceImpactFeePercent: '0.94', longAvailableLiquidity: '10000000.00', shortAvailableLiquidity: '10000000.00', maxRequestExecutionSec: '45' });
  assert.deepEqual([pool.longBorrowRatePercent, pool.shortUtilizationPercent, pool.openFeePercent, pool.longAvailableLiquidity], [0.0015, 66.77, 0.06, 10000000]);
  assert.equal(Object.hasOwn(pool, 'maxRequestExecutionSec'), false);
  assert.equal(parsePool({}), null); assert.equal(parsePool(null), null);
});

test('each oracle feed maps to one coin, and the subscription asks for all of them', () => {
  const feeds = feedMap([{ coin: 'ZEC', feedId: 66 }, { coin: 'XAU', feedId: 346 }, { coin: 'BTC', feedId: 1 }, { coin: 'OTHER', feedId: 6 }]);
  assert.deepEqual([...feeds].sort((a, b) => a[0] - b[0]), [[1, 'BTC'], [2, 'ETH'], [6, 'SOL'], [66, 'ZEC'], [346, 'XAU']]);
  assert.deepEqual(Object.keys(JLP_MARKETS), ['SOL', 'ETH', 'BTC']);
  const subscription = oracleSubscription(feeds.keys());
  assert.deepEqual(subscription.priceFeedIds, [1, 2, 6, 66, 346]);
  assert.deepEqual([subscription.type, subscription.channel, subscription.properties], ['subscribe', 'fixed_rate@200ms', ['price', 'exponent', 'feedUpdateTimestamp']]);
  // A market that is shut for the weekend must not cost the stream its other feeds.
  assert.equal(subscription.ignoreInvalidFeeds, true);
});

test('an oracle frame becomes one tick per known feed, in the shape the scalp study reads', () => {
  const feeds = new Map([[1, 'BTC'], [66, 'ZEC']]);
  const frame = { type: 'streamUpdated', parsed: { priceFeeds: [
    { priceFeedId: 1, price: '5916195750274', exponent: -8, feedUpdateTimestamp: 1795862253200000 },
    { priceFeedId: 66, price: '72764581227', exponent: -8, feedUpdateTimestamp: 1795862253200000 },
    { priceFeedId: 999, price: '1', exponent: 0, feedUpdateTimestamp: 1 },
    { priceFeedId: 1, price: '-5', exponent: -8, feedUpdateTimestamp: 2 }, { priceFeedId: 1, price: 5, exponent: -8, feedUpdateTimestamp: 2 },
    { priceFeedId: 1, price: '5', exponent: 2, feedUpdateTimestamp: 2 }, { priceFeedId: 1, price: '5', exponent: -8.5, feedUpdateTimestamp: 2 },
    { priceFeedId: 1, price: '5', exponent: -8, feedUpdateTimestamp: 0 }, { priceFeedId: 1, price: '0', exponent: -8, feedUpdateTimestamp: 2 }, null,
  ] } };
  const ticks = oracleTicks(frame, feeds, 1795862253423);
  assert.deepEqual(ticks.map(tick => [tick.coin, tick.key]), [['BTC', 1795862253200000], ['ZEC', 1795862253200000]]);
  // e is the oracle's own time in milliseconds, r the receive time: two clocks, two fields.
  assert.deepEqual(ticks[0].row, { a: 'BTC', p: 5916195750274 * 10 ** -8, e: 1795862253200, r: 1795862253423 });
  assert.ok(Math.abs(ticks[1].row.p - 727.64581227) < 1e-9);
  for (const other of [null, {}, { type: 'subscribed' }, { type: 'streamUpdated' }, { type: 'streamUpdated', parsed: { priceFeeds: 'x' } }]) assert.deepEqual(oracleTicks(other, feeds, 1), []);
});

test('a polled snapshot is written only when something other than the receive time changed', () => {
  const row = { r: 1, bid: 10, ask: 11, status: 'active', last: null };
  assert.equal(changed(undefined, row), true);
  assert.equal(changed(row, { ...row, r: 2 }), false);
  assert.equal(changed(row, { ...row, r: 2, ask: 12 }), true);
  assert.equal(changed(row, { ...row, last: 10.5 }), true);
  assert.equal(changed(row, { ...row, status: 'paused' }), true);
});

test('files are one per coin, stream and UTC hour', () => {
  const ms = Date.UTC(2026, 10, 28, 23, 59, 59, 999);
  assert.deepEqual(hourOf(ms), { day: '2026-11-28', hour: '20261128T23' });
  assert.deepEqual(hourOf(ms + 1), { day: '2026-11-29', hour: '20261129T00' });
  assert.equal(relativePath('ZEC', 'oracle', ms), 'ZEC/oracle/2026-11-28/ZEC-oracle-20261128T23.jsonl');
  assert.equal(relativePath('BTC', '1000x-market', Date.UTC(2027, 0, 5, 4)), 'BTC/1000x-market/2027-01-05/BTC-1000x-market-20270105T04.jsonl');
  assert.throws(() => relativePath('../x', 'oracle', ms), RangeError);
  assert.throws(() => relativePath('BTC', 'trades', ms), RangeError);
  assert.throws(() => relativePath('BTC', 'oracle', NaN), RangeError);
});

test('retries wait from half a second up to a minute', () => {
  assert.deepEqual([0, 1, 2, 3, 8, 50].map(backoffMs), [500, 500, 1000, 2000, 60_000, 60_000]);
});

test('options: an absolute folder, intervals of a second or more, and a clear refusal otherwise', () => {
  const defaults = parseArgs([]);
  assert.deepEqual(defaults, { out: '/Volumes/dasdata/CoinTradingData', minutes: 0, bookEvery: 2, catalogEvery: 15, fundingEvery: 60, poolEvery: 30, gzip: true, keepHours: 0 });
  assert.equal(parseArgs(['--keep-hours', '3']).keepHours, 3);
  for (const bad of ['0', '2.5', '25', 'few', '-1']) assert.throws(() => parseArgs(['--keep-hours', bad]), RangeError, bad);
  assert.deepEqual(parseArgs(['--out', '/data/x/', '--minutes', '90', '--book-every', '5', '--no-gzip']),
    { ...defaults, out: '/data/x', minutes: 90, bookEvery: 5, gzip: false });
  assert.equal(parseArgs(['--help']).help, true);
  for (const bad of [['--out', 'relative'], ['--out'], ['--book-every', '0'], ['--book-every', '0.5'], ['--minutes', '-1'], ['--minutes', 'soon'], ['--pool-every', 'Infinity'], ['--what', '1']]) {
    assert.throws(() => parseArgs(bad), RangeError, bad.join(' '));
  }
});

/** Run the tool and collect its exit code and output. */
function run(args, timeoutMs = 15_000) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [TOOL, ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', err = '';
    child.stdout.on('data', chunk => { out += chunk; });
    child.stderr.on('data', chunk => { err += chunk; });
    const timer = setTimeout(() => { child.kill('SIGKILL'); reject(new Error(`timed out: ${out}${err}`)); }, timeoutMs);
    child.on('close', code => { clearTimeout(timer); resolve({ code, out, err }); });
  });
}

test('the tool refuses a missing output folder and unknown options before it opens any connection', async () => {
  const missing = await run(['--out', join(tmpdir(), 'market-recorder-no-such-folder', 'x')]);
  assert.equal(missing.code, 2);
  assert.match(missing.err, /does not exist\. Mount the disk or create the folder/);
  const unknown = await run(['--speed', '9']);
  assert.equal(unknown.code, 2);
  assert.match(unknown.err, /Unknown or incomplete option --speed\.[\s\S]*Public reads only/);
  const help = await run(['--help']);
  assert.equal(help.code, 0);
  assert.match(help.out, /one folder per coin/);
  // Nothing was created for the refused runs.
  const folder = mkdtempSync(join(tmpdir(), 'market-recorder-'));
  try {
    const refused = await run(['--out', folder, '--book-every', '0']);
    assert.equal(refused.code, 2);
    assert.deepEqual(readdirSync(folder), []);
  } finally { rmSync(folder, { recursive: true, force: true }); }
});

test('the recorder sources read only the listed endpoints, with no credential, no environment and no write method', () => {
  const RUN = fileURLToPath(new URL('../tools/lib/market-recorder-run.mjs', import.meta.url));
  for (const path of [TOOL, RUN]) {
    const source = readFileSync(path, 'utf8');
    assert.equal(/method\s*:/i.test(source) || /['"`](POST|PUT|DELETE|PATCH)['"`]/i.test(source), false, `${path}: no request method is set, so every request is a GET`);
    assert.equal(/Authorization|Bearer|api[-_]?key|secret|keypair|process\.env|headers\s*:/i.test(source), false, `${path}: no credential, header or environment read`);
    assert.equal([...source.matchAll(/https?:\/\/|wss?:\/\//g)].length, 0, `${path}: every address comes from ENDPOINTS`);
  }
  const tool = readFileSync(TOOL, 'utf8');
  assert.match(tool, /credentials: 'omit', redirect: 'error'/);
  // The hang watchdog is running before the tool first looks at the output folder: a dead network disk can hang that look.
  const watching = tool.indexOf('await watchdog.ready'), looking = tool.indexOf('existsSync(options.out)');
  assert.ok(watching > 0 && looking > watching);
});

/* ---------------------------------------------------------------- the run -- */

import { chmodSync, createWriteStream, existsSync, mkdirSync, utimesSync, writeFileSync } from 'node:fs';
import { hostname } from 'node:os';
import { gunzipSync, gzipSync } from 'node:zlib';
import { Recorder, STREAM_SILENCE_MS, STREAM_STEADY_MS, WATCH_EVERY_MS, bootedAt, endsMidLine } from '../tools/lib/market-recorder-run.mjs';

const T0 = Date.UTC(2026, 10, 28, 10, 0, 5);
const HOUR = 3_600_000;

/** A recorder on a temporary folder with a hand-moved clock, hand-run timers, a scripted network and a fake socket. */
function harness({ minutes = 0, gzip = true, at = T0, keepHours = 0, openFile } = {}) {
  const out = mkdtempSync(join(tmpdir(), 'market-recorder-run-'));
  // `sockets` are the oracle's; Coinbase's are kept apart, and there are none unless a test lists products.
  const state = { now: at, timers: [], seq: 0, sockets: [], coinbase: [], products: [], calls: [], exits: [], logs: [], fail: new Set(),
    yolo: { markets: [{ symbol: 'BTC', feedId: 1, closed: false, closeOnly: false, longOi: '10', shortOi: '20', volume24h: '5', totalVolume: '50' },
      { symbol: 'ZEC', feedId: 66, closed: false, closeOnly: false, longOi: '1', shortOi: '2', volume24h: '3', totalVolume: '4' }] },
    gum: [{ symbol: 'ZEC', status: 'active', timestamp: 100, lastUpdatedMs: 900, bestBid: 727.5, bestAsk: 727.9, midPrice: 727.7, markPrice: 727.6, indexPrice: 727.6,
      lastTradePrice: 727.1, openInterest: 10, openInterestBase: 1, volume24h: 9, maxLeverage: 50 },
    { symbol: 'ANT', status: 'active', timestamp: 100, lastUpdatedMs: 900, bestBid: 91.3, bestAsk: 91.4, midPrice: 91.35, markPrice: 91.34, indexPrice: 91.34,
      lastTradePrice: 91.3, openInterest: 5, openInterestBase: 1, volume24h: 2, maxLeverage: 20 }] };
  class FakeSocket {
    constructor(url) { this.url = url; this.sent = []; this.closed = false; (url === ENDPOINTS.oracleStream ? state.sockets : state.coinbase).push(this); }
    say(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
    send(text) { this.sent.push(JSON.parse(text)); }
    close() { this.closed = true; }
    tick(feedId, price, micros) { this.onmessage?.({ data: JSON.stringify({ type: 'streamUpdated', parsed: { priceFeeds: [{ priceFeedId: feedId, price, exponent: -8, feedUpdateTimestamp: micros }] } }) }); }
  }
  const fetchJson = async url => {
    state.calls.push(url);
    if ([...state.fail].some(part => url.includes(part))) throw new Error('HTTP 429');
    if (url === ENDPOINTS.yoloMarkets) return structuredClone(state.yolo);
    if (url === ENDPOINTS.gumMarkets) return structuredClone(state.gum);
    if (url.startsWith(ENDPOINTS.gumFunding)) return { symbol: decodeURIComponent(url.slice(ENDPOINTS.gumFunding.length)), rateBps1h: 0.125, fundingRate: '0.0001', fundingUpdateTimestamp: Math.floor(state.now / 1000) };
    if (url.startsWith(ENDPOINTS.poolInfo)) return { openFeePercent: '0.06', longBorrowRatePercent: '0.0015', shortBorrowRatePercent: '0.0007' };
    if (url === ENDPOINTS.coinbaseProducts) return structuredClone(state.products);
    throw new Error(`unexpected address ${url}`);
  };
  const recorder = new Recorder({ options: { ...parseArgs(['--out', out]), minutes, gzip, keepHours }, fetchJson, WebSocket: FakeSocket, now: () => state.now,
    ...(openFile ? { openFile } : {}),
    setTimer: (fn, ms) => { const timer = { fn, at: state.now + ms, id: ++state.seq }; state.timers.push(timer); return timer; },
    clearTimer: timer => { const i = state.timers.indexOf(timer); if (i >= 0) state.timers.splice(i, 1); },
    exit: code => state.exits.push(code), log: text => state.logs.push(text) });
  /** Let pending reads, stream writes and the compress queue run. */
  const settle = async () => { for (let i = 0; i < 6; i++) { await new Promise(resolve => setImmediate(resolve)); await recorder.compressed; } };
  /** Move the clock, running every timer that falls due on the way, in order. */
  const advance = async ms => {
    const end = state.now + ms;
    // Reads already under way finish, and schedule their next turn, before the clock moves.
    await settle();
    for (;;) {
      state.timers.sort((a, b) => a.at - b.at || a.id - b.id);
      const next = state.timers[0];
      if (!next || next.at > end) break;
      state.timers.shift(); state.now = next.at; next.fn();
      await settle();
    }
    state.now = end;
    await settle();
  };
  const file = (coin, stream, ms = state.now) => join(out, relativePath(coin, stream, ms));
  /** The rows of an hour's file, whether it is still plain or already compressed. */
  const rows = (coin, stream, ms = state.now) => {
    const path = file(coin, stream, ms);
    const text = existsSync(`${path}.gz`) ? gunzipSync(readFileSync(`${path}.gz`)).toString() : existsSync(path) ? readFileSync(path, 'utf8') : '';
    return text.split('\n').filter(Boolean).map(line => JSON.parse(line));
  };
  const socket = () => state.sockets.at(-1);
  /** Wait for the run to end: closing files takes real time, and how long depends on the disk. */
  const ended = async () => { for (let i = 0; i < 2000 && !state.exits.length; i++) await new Promise(resolve => setTimeout(resolve, 5)); };
  // Retried: a run that is still ending may write its last file while the folder is being removed, and a failure
  // here would hide the assertion that failed before it.
  const cleanup = () => rmSync(out, { recursive: true, force: true, maxRetries: 10, retryDelay: 50 });
  /** Wait for something the recorder does on its own, in real time: its sweeps read folders off the main thread. */
  const until = async check => { for (let i = 0; i < 1000 && !check(); i++) { await new Promise(resolve => setTimeout(resolve, 5)); await recorder.compressed; } return check(); };
  return { out, state, recorder, settle, advance, file, rows, socket, ended, cleanup, until };
}

test('rows land in one file per coin, stream and hour, and a poll that changed nothing writes nothing', async () => {
  const h = harness();
  try {
    h.recorder.start();
    await h.settle();
    assert.equal(h.state.sockets.length, 1);
    assert.deepEqual(h.socket().sent, [], 'nothing is sent before the stream is open');
    h.socket().onopen();
    assert.deepEqual(h.socket().sent[0].priceFeedIds, [1, 2, 6, 66]);
    h.socket().tick(1, '5916195750274', 1795862253200000);
    h.socket().tick(1, '5916195750274', 1795862253200000);
    h.socket().tick(66, '72764581227', 1795862253200000);
    // Six seconds: three more book polls (every 2 s) in which only the venue's clock fields move.
    h.state.gum.forEach(row => { row.timestamp += 5; row.lastUpdatedMs = 1; });
    await h.advance(6000);
    await h.recorder.stop('test');
    assert.deepEqual(h.state.exits, [0]);
    assert.deepEqual(h.rows('BTC', 'oracle').map(row => [row.a, row.p, row.e]), [['BTC', 59161.95750274, 1795862253200]], 'a repeated tick is written once');
    assert.equal(h.rows('ZEC', 'oracle').length, 1);
    assert.equal(h.rows('ZEC', 'perps-book').length, 1, 'clock fields alone do not make a new row');
    assert.deepEqual(h.rows('ANT', 'perps-book').map(row => [row.bid, row.ask, row.last, row.venueTime]), [[91.3, 91.4, 91.3, 100]]);
    assert.deepEqual(h.rows('BTC', '1000x-market').map(row => [row.closed, row.longOi, row.shortOi, row.volume24h]), [[false, 10, 20, 5]]);
    assert.equal(h.rows('ZEC', 'perps-funding')[0].rateBps1h, 0.125);
    assert.equal(h.rows('SOL', 'perps-pool')[0].longBorrowRatePercent, 0.0015);
    const status = JSON.parse(readFileSync(join(h.out, '_recorder', 'status.json'), 'utf8'));
    assert.deepEqual(status.coins, ['ANT', 'BTC', 'ETH', 'SOL', 'ZEC']);
    assert.equal(status.rows.oracle, 2);
    assert.equal(status.reason, 'test');
    assert.ok(status.lastReadOkAt['perps-book']);
  } finally { h.cleanup(); }
});

test('a changed book is written, and a price that is missing stays missing', async () => {
  const h = harness();
  try {
    h.recorder.start();
    await h.settle();
    h.state.gum[0].bestBid = 727.6;
    h.state.gum[1].lastTradePrice = 0;
    await h.advance(2000);
    await h.recorder.stop('test');
    assert.deepEqual(h.rows('ZEC', 'perps-book').map(row => row.bid), [727.5, 727.6]);
    assert.deepEqual(h.rows('ANT', 'perps-book').map(row => row.last), [91.3, null]);
  } finally { h.cleanup(); }
});

test('when the hour ends every file is closed and compressed, and the new hour opens with a full row', async () => {
  const h = harness({ at: Date.UTC(2026, 10, 28, 10, 59, 40) });
  try {
    h.recorder.start();
    await h.settle();
    h.socket().tick(1, '5916195750274', 1);
    const before = h.state.now;
    await h.advance(40_000);
    h.socket().tick(1, '5916195750275', 2);
    await h.settle();
    // Nothing about the ZEC book changed, yet the 11:00 file has its state.
    assert.equal(existsSync(`${h.file('ZEC', 'perps-book', before)}.gz`), true, 'the 10:00 file was compressed');
    assert.equal(existsSync(h.file('ZEC', 'perps-book', before)), false, 'and its plain copy removed');
    assert.equal(h.rows('ZEC', 'perps-book', before).length, 1);
    await h.recorder.stop('test');
    assert.equal(h.rows('ZEC', 'perps-book').length, 1);
    assert.equal(h.rows('BTC', '1000x-market').length, 1);
    assert.deepEqual([h.rows('BTC', 'oracle', before).length, h.rows('BTC', 'oracle').length], [1, 1]);
    assert.equal(h.file('BTC', 'oracle').endsWith('BTC-oracle-20261128T11.jsonl'), true);
  } finally { h.cleanup(); }
});

test('a clock that steps backwards cannot reopen an hour, and a compressed hour is added to, never replaced', async () => {
  const h = harness({ at: Date.UTC(2026, 10, 28, 10, 59, 58) });
  try {
    // An earlier run already compressed part of the 10:00 hour.
    const tenFile = h.file('BTC', 'oracle');
    mkdirSync(join(tenFile, '..'), { recursive: true });
    writeFileSync(`${tenFile}.gz`, gzipSync('{"a":"BTC","p":1,"e":1,"r":1}\n'));
    h.recorder.start();
    await h.settle();
    h.socket().tick(1, '200000000', 2);
    await h.advance(5000);
    h.socket().tick(1, '300000000', 3);
    await h.settle();
    h.state.now -= 10_000;
    h.socket().tick(1, '400000000', 4);
    await h.settle();
    await h.recorder.stop('test');
    assert.deepEqual(h.rows('BTC', 'oracle', Date.UTC(2026, 10, 28, 10, 30)).map(row => row.p), [1, 2], 'both parts of the 10:00 hour are in its file');
    assert.deepEqual(h.rows('BTC', 'oracle', Date.UTC(2026, 10, 28, 11, 0, 3)).map(row => row.p), [3, 4], 'the late tick stayed in the open hour');
  } finally { h.cleanup(); }
});

test('a restart appends to the hour in progress and starts a clean line after a row cut off by a crash', async () => {
  const h = harness();
  try {
    const path = h.file('BTC', 'oracle');
    mkdirSync(join(path, '..'), { recursive: true });
    writeFileSync(path, '{"a":"BTC","p":1,"e":1,"r":1}\n{"a":"BTC","p":2,"e"');
    assert.equal(endsMidLine(path), true);
    h.recorder.start();
    await h.settle();
    h.socket().tick(1, '300000000', 3);
    await h.recorder.stop('test');
    const lines = readFileSync(path, 'utf8').split('\n').filter(Boolean);
    assert.deepEqual(lines.map(line => { try { return JSON.parse(line).p; } catch { return 'cut'; } }), [1, 'cut', 3]);
    assert.equal(endsMidLine(path), false);
    assert.equal(endsMidLine(join(h.out, 'absent')), false);
  } finally { h.cleanup(); }
});

test('files left plain by an earlier run are compressed at the start, except the hour in progress', async () => {
  const h = harness();
  try {
    const old = h.file('ZEC', 'oracle', T0 - 3 * HOUR), current = h.file('ZEC', 'oracle');
    for (const path of [old, current]) { mkdirSync(join(path, '..'), { recursive: true }); writeFileSync(path, '{"a":"ZEC","p":1,"e":1,"r":1}\n'); }
    writeFileSync(join(old, '..', 'notes.txt'), 'not ours');
    h.recorder.start();
    await h.settle();
    await h.recorder.sweep();
    assert.equal(existsSync(`${old}.gz`), true);
    assert.equal(existsSync(old), false);
    assert.equal(existsSync(current), true, 'the hour in progress stays plain');
    assert.equal(existsSync(`${current}.gz`), false);
    assert.equal(existsSync(join(old, '..', 'notes.txt')), true);
    assert.deepEqual(h.rows('ZEC', 'oracle', T0 - 3 * HOUR).map(row => row.p), [1]);
    await h.recorder.stop('test');
  } finally { h.cleanup(); }
});

test('one market whose read fails does not cost the others their rows', async () => {
  const h = harness();
  try {
    h.state.fail.add('fundingRate/ZEC');
    h.recorder.start();
    // Funding waits three seconds for the book's first read to name the coins.
    await h.advance(3500);
    assert.equal(h.state.calls.filter(url => url.includes('fundingRate/')).length, 2, 'both coins were tried');
    assert.equal(h.recorder.status().failuresInARow['perps-funding'], 0, 'the read as a whole succeeded');
    // Every funding read failing is a failure of the reader, and the other readers carry on.
    h.state.fail.add('fundingRate/');
    await h.advance(61_000);
    assert.ok(h.recorder.status().failuresInARow['perps-funding'] >= 1);
    assert.equal(h.recorder.status().failuresInARow['perps-book'], 0);
    await h.recorder.stop('test');
    assert.equal(h.rows('ANT', 'perps-funding').length, 1);
    assert.equal(h.rows('ZEC', 'perps-funding').length, 0);
    const events = readFileSync(join(h.out, '_recorder', 'events.jsonl'), 'utf8');
    assert.match(events, /"type":"coins-skipped","failed":1,"of":2/);
    assert.match(events, /"type":"read-failed","name":"perps-funding"/);
  } finally { h.cleanup(); }
});

test('a silent stream is replaced, a lost one is retried once at a time, and a new market list resubscribes', async () => {
  const h = harness();
  try {
    h.recorder.start();
    await h.settle();
    const first = h.socket();
    // Frames that repeat the last tick still show the stream is alive.
    first.tick(1, '100000000', 7);
    for (let i = 0; i < 4; i++) { await h.advance(WATCH_EVERY_MS); first.tick(1, '100000000', 7); }
    assert.equal(h.state.sockets.length, 1, 'repeated frames are not silence');
    await h.advance(STREAM_SILENCE_MS + WATCH_EVERY_MS);
    assert.equal(h.state.sockets.length, 2, 'silence replaced the socket');
    assert.equal(first.closed, true);
    // A frame arriving late on the replaced socket is ignored.
    first.tick(1, '900000000', 8);
    const second = h.socket();
    second.onclose();
    // While the retry waits, the catalog poll (every 15 s) must not open a second socket.
    assert.equal(h.state.sockets.length, 2);
    await h.advance(600);
    assert.equal(h.state.sockets.length, 3, 'one retry');
    h.state.yolo.markets.push({ symbol: 'HYPE', feedId: 110, closed: false, closeOnly: false });
    await h.advance(15_000);
    assert.equal(h.state.sockets.length, 4, 'the changed list opened a new socket');
    h.socket().onopen();
    assert.deepEqual(h.socket().sent[0].priceFeedIds, [1, 2, 6, 66, 110]);
    assert.equal(h.state.sockets.filter(socket => !socket.closed).length, 2, 'the lost socket was never closed by us; every replaced one was');
    await h.recorder.stop('test');
    assert.deepEqual(h.rows('BTC', 'oracle').map(row => row.p), [1]);
  } finally { h.cleanup(); }
});

test('if the folder goes away the run stops with an error and writes nothing in its place', async () => {
  const h = harness();
  try {
    h.recorder.start();
    await h.settle();
    // The recorder is still opening its first files while the folder is taken away, as on a real disk: retried until it is gone.
    rmSync(h.out, { recursive: true, force: true, maxRetries: 20, retryDelay: 25 });
    h.state.gum[0].bestBid = 1;
    // Within one look (ten seconds) the missing folder is noticed, whatever the open files report.
    await h.advance(WATCH_EVERY_MS);
    await h.ended();
    assert.equal(h.recorder.stopping, true);
    assert.equal(h.recorder.exitCode, 1);
    assert.deepEqual(h.state.exits, [1]);
    assert.equal(existsSync(h.out), false, 'the folder was not created again');
    // Either the look every ten seconds finds the folder gone, or a file still being opened fails first.
    assert.match(h.state.logs.join(' '), /Write failed \((ENODISK|ENOENT)\)/);
  } finally { h.cleanup(); }
});

test('the time limit ends the run cleanly, and a fault nobody caught ends it with an error', async () => {
  const timed = harness({ minutes: 1 });
  try {
    timed.recorder.start();
    await timed.advance(70_000);
    await timed.ended();
    assert.deepEqual(timed.state.exits, [0]);
    assert.equal(timed.state.timers.length, 0, 'no timer is left running');
    assert.equal(timed.socket().closed, true);
  } finally { timed.cleanup(); }
  const faulty = harness();
  try {
    faulty.recorder.start();
    await faulty.settle();
    faulty.recorder.fault(new Error('boom'));
    await faulty.ended();
    assert.deepEqual(faulty.state.exits, [1]);
    assert.match(readFileSync(join(faulty.out, '_recorder', 'events.jsonl'), 'utf8'), /"type":"fault","reason":"boom"/);
  } finally { faulty.cleanup(); }
});

test('Coinbase is recorded beside Jupiter: the book when its top changes, every trade once, depth each second', async () => {
  const h = harness();
  try {
    h.state.products = [{ id: 'ZEC-USD', base_currency: 'ZEC', status: 'online' }, { id: 'ANT-USD', base_currency: 'ANT', status: 'delisted' }, { id: 'DOGE-USD', base_currency: 'DOGE', status: 'online' }];
    h.recorder.start();
    await h.advance(5500);
    assert.equal(h.state.coinbase.length, 1, 'one Coinbase socket, opened once the coins were known');
    const feed = h.state.coinbase[0], at = new Date(h.state.now).toISOString();
    assert.equal(feed.url, ENDPOINTS.coinbaseStream);
    feed.onopen();
    assert.deepEqual(feed.sent, [{ type: 'subscribe', product_ids: ['ZEC-USD'], channels: ['level2_batch', 'matches', 'heartbeat'] }]);
    feed.say({ type: 'snapshot', product_id: 'ZEC-USD', time: at, bids: [['727.5', '2']], asks: [['727.9', '1']] });
    feed.say({ type: 'l2update', product_id: 'ZEC-USD', time: at, changes: [['buy', '727.6', '4']] });
    feed.say({ type: 'l2update', product_id: 'ZEC-USD', time: at, changes: [['buy', '700', '9']] });
    feed.say({ type: 'match', product_id: 'ZEC-USD', trade_id: 7, price: '727.9', size: '0.5', side: 'sell', time: at });
    feed.say({ type: 'match', product_id: 'ZEC-USD', trade_id: 7, price: '727.9', size: '0.5', side: 'sell', time: at });
    await h.advance(2100);
    assert.deepEqual(h.recorder.status().coinbase.products, ['ZEC-USD']);
    assert.equal(h.recorder.status().coinbase.booksInStep, 1);
    // A message that cannot be trusted starts the stream again, and the book waits for a new snapshot.
    feed.say({ type: 'l2update', product_id: 'ZEC-USD', time: at, changes: [['buy', 'oops', '1']] });
    await h.settle();
    assert.equal(feed.closed, true);
    assert.equal(h.state.coinbase.length, 1, 'the new attempt waits its turn');
    await h.advance(600);
    assert.equal(h.state.coinbase.length, 2);
    assert.equal(h.recorder.status().coinbase.booksInStep, 0);
    h.state.coinbase[1].say({ type: 'l2update', product_id: 'ZEC-USD', time: at, changes: [['buy', '727.7', '1']] });
    await h.recorder.stop('test');
    assert.deepEqual(h.rows('ZEC', 'coinbase-book').map(row => [row.bid, row.ask, row.bidSize, row.askSize]), [[727.5, 727.9, 2, 1], [727.6, 727.9, 4, 1]]);
    assert.equal(h.rows('ZEC', 'coinbase-book')[0].t, Date.parse(at));
    assert.deepEqual(h.rows('ZEC', 'coinbase-trades').map(row => [row.price, row.size, row.side, row.tradeId]), [[727.9, 0.5, 'sell', 7]]);
    const depth = h.rows('ZEC', 'coinbase-depth');
    assert.equal(depth.length, 1, 'an unchanged book writes its depth once');
    assert.deepEqual([depth[0].bid, depth[0].ask, depth[0].bid5, depth[0].ask5, depth[0].bid25], [727.6, 727.9, 6, 1, 6]);
    assert.equal(h.state.sockets.length, 1, 'the oracle stream was not disturbed');
  } finally { h.cleanup(); }
});

test('a stream that answers every opening with a refusal is retried slowly, not in a loop', async () => {
  const h = harness();
  try {
    h.state.products = [{ id: 'ZEC-USD', base_currency: 'ZEC', status: 'online' }];
    h.recorder.start();
    await h.advance(5500);
    assert.equal(h.state.coinbase.length, 1);
    // Each attempt is refused at once. The waits grow: 0.5 s, 1 s, 2 s, 4 s ...
    const refuse = () => h.state.coinbase.at(-1).say({ type: 'error', message: 'rate limited' });
    refuse(); await h.settle();
    assert.equal(h.state.coinbase.length, 1, 'no new socket in the same instant');
    await h.advance(500); assert.equal(h.state.coinbase.length, 2);
    refuse(); await h.advance(500); assert.equal(h.state.coinbase.length, 2, 'the second wait is longer');
    await h.advance(500); assert.equal(h.state.coinbase.length, 3);
    refuse(); await h.advance(1900); assert.equal(h.state.coinbase.length, 3);
    await h.advance(200); assert.equal(h.state.coinbase.length, 4);
    // A stream that opens, answers and then fails is still failing: one good frame does not start the waits over.
    const good = () => h.state.coinbase.at(-1).say({ type: 'snapshot', product_id: 'ZEC-USD', bids: [['1', '1']], asks: [['2', '1']] });
    h.state.coinbase.at(-1).say({ type: 'subscriptions', channels: [] });
    good(); refuse();
    await h.advance(3900); assert.equal(h.state.coinbase.length, 4, 'the fourth wait is four seconds');
    await h.advance(200); assert.equal(h.state.coinbase.length, 5);
    // Only frames that keep coming for half a minute end the run of failures.
    good(); await h.advance(STREAM_STEADY_MS / 2); good(); await h.advance(STREAM_STEADY_MS / 2); good();
    refuse(); await h.advance(500);
    assert.equal(h.state.coinbase.length, 6, 'back to the shortest wait');
    assert.equal(h.state.coinbase.slice(0, -1).every(socket => socket.closed), true, 'every replaced socket was closed');
    const restarts = readFileSync(join(h.out, '_recorder', 'events.jsonl'), 'utf8').split('\n').filter(line => line.includes('stream-restart'));
    assert.ok(restarts.length <= 4, 'a run of failures is noted, not logged once per attempt forever');
    await h.recorder.stop('test');
  } finally { h.cleanup(); }
});

test('a crash in the middle of compressing an hour can neither lose it nor double it', async () => {
  const h = harness();
  try {
    const row = n => `{"a":"ZEC","p":${n},"e":${n},"r":${n}}\n`;
    const at = hours => T0 - hours * HOUR;
    const place = (ms, suffix, text) => { const path = h.file('ZEC', 'oracle', ms); mkdirSync(join(path, '..'), { recursive: true }); writeFileSync(path + suffix, text); return path; };
    // Died after finishing the compressed copy and before removing the plain file: both hold the same rows.
    const both = place(at(5), '', row(1)); place(at(5), '.gz.ready', gzipSync(row(1)));
    // Died after removing the plain file and before publishing: only the finished copy is left.
    const readyOnly = place(at(4), '.gz.ready', gzipSync(row(2)));
    // The same, for an hour that already had a published part.
    const second = place(at(3), '.gz', gzipSync(row(3))); place(at(3), '.gz.ready', gzipSync(row(4)));
    // Died while still compressing: a half-written temporary copy beside the plain file.
    const half = place(at(2), '', row(5)); place(at(2), '.gz.tmp', 'garbage');
    // Died while joining a new part to a published one: the joined file may be half written, and the part is still there to add.
    const torn = place(at(8), '.gz', gzipSync(row(6))); place(at(8), '.gz.ready', gzipSync(row(7))); place(at(8), '.gz.merge', gzipSync(row(6)).subarray(0, 9));
    // Died after the joined file was complete and the part removed, before it took the published name.
    const joined = place(at(7), '.gz', gzipSync(row(8))); place(at(7), '.gz.merge', Buffer.concat([gzipSync(row(8)), gzipSync(row(9))]));
    h.recorder.start();
    await h.settle();
    await h.recorder.sweep();
    assert.deepEqual(h.rows('ZEC', 'oracle', at(5)).map(r => r.p), [1], 'not doubled');
    assert.deepEqual(h.rows('ZEC', 'oracle', at(4)).map(r => r.p), [2], 'not lost');
    assert.deepEqual(h.rows('ZEC', 'oracle', at(3)).map(r => r.p), [3, 4], 'added to, in order');
    assert.deepEqual(h.rows('ZEC', 'oracle', at(2)).map(r => r.p), [5]);
    assert.deepEqual(h.rows('ZEC', 'oracle', at(8)).map(r => r.p), [6, 7], 'the half-joined file was made again, once');
    assert.deepEqual(h.rows('ZEC', 'oracle', at(7)).map(r => r.p), [8, 9], 'the finished join was kept, not added to again');
    // A second pass finds nothing left to do and changes nothing.
    await h.recorder.sweep();
    assert.deepEqual(h.rows('ZEC', 'oracle', at(8)).map(r => r.p), [6, 7]);
    for (const path of [both, readyOnly, second, half, torn, joined]) {
      assert.equal(existsSync(`${path}.gz`), true, path);
      for (const left of ['', '.gz.ready', '.gz.tmp', '.gz.merge']) assert.equal(existsSync(path + left), false, `${path}${left} was cleaned up`);
    }
    assert.equal(h.recorder.status().compressFailed, 0);
    await h.recorder.stop('test');
  } finally { h.cleanup(); }
});

test('rows piling up for a disk that has stopped taking them end the run before memory does', async () => {
  const h = harness();
  const small = new Recorder({ options: { ...parseArgs(['--out', h.out]), gzip: true }, fetchJson: async () => { throw new Error('offline'); },
    WebSocket: class { close() {} }, now: () => h.state.now, setTimer: () => ({}), clearTimer: () => {}, exit: code => h.state.exits.push(code),
    log: text => h.state.logs.push(text), maxBufferedBytes: 0 });
  try {
    small.start();
    assert.equal(small.status().bufferedBytes, 0);
    // The events file is not a market file; with nothing buffered the look passes.
    small.watch();
    assert.equal(small.stopping, false);
    await small.stop('test');
    assert.deepEqual(h.state.exits, [0]);
  } finally { h.cleanup(); }
  const g = harness();
  const stalled = new Recorder({ options: { ...parseArgs(['--out', g.out]), gzip: true },
    fetchJson: async url => url === ENDPOINTS.gumMarkets ? structuredClone(g.state.gum) : (() => { throw new Error('offline'); })(),
    WebSocket: class { close() {} }, now: () => g.state.now, setTimer: () => ({}), clearTimer: () => {}, exit: code => g.state.exits.push(code),
    log: text => g.state.logs.push(text), maxBufferedBytes: 0 });
  try {
    stalled.start();
    // The book read resolves and writes its rows without the event loop turning, so the disk cannot have taken them yet:
    // a file is opened, and its rows flushed, only on a later turn.
    for (let i = 0; i < 50 && stalled.status().bufferedBytes === 0; i++) await Promise.resolve();
    assert.ok(stalled.status().bufferedBytes > 0, 'rows are waiting for the disk');
    stalled.watch();
    assert.equal(stalled.exitCode, 1);
    assert.match(g.state.logs.join(' '), /Write failed \(EBACKLOG\)/);
    await g.ended();
    assert.deepEqual(g.state.exits, [1]);
  } finally { g.cleanup(); }
});

test('one recorder per folder: a second is refused, and a lock left by a dead process is replaced', async () => {
  const h = harness();
  try {
    h.recorder.start();
    const lock = join(h.out, '_recorder', 'lock');
    assert.deepEqual([JSON.parse(readFileSync(lock, 'utf8')).pid, JSON.parse(readFileSync(lock, 'utf8')).host], [process.pid, hostname()]);
    await h.recorder.stop('test');
    assert.equal(existsSync(lock), false, 'a clean stop releases the lock');
    // A lock held by a live process on this machine (the test runner's parent) refuses the start.
    writeFileSync(lock, JSON.stringify({ pid: process.ppid, host: hostname() }));
    const second = new Recorder({ options: parseArgs(['--out', h.out]), fetchJson: async () => ({}), WebSocket: class {}, exit: () => {} });
    assert.throws(() => second.start(), error => error.code === 'ELOCKED' && /Another recorder is already writing to this folder/.test(error.message));
    assert.equal(JSON.parse(readFileSync(lock, 'utf8')).pid, process.ppid, 'the live lock was left alone');
    // The same with this start of the machine written in it, as the recorder writes it.
    writeFileSync(lock, JSON.stringify({ pid: process.ppid, host: hostname(), boot: bootedAt() }));
    assert.throws(() => new Recorder({ options: parseArgs(['--out', h.out]), fetchJson: async () => ({}), WebSocket: class {}, exit: () => {} }).start(), error => error.code === 'ELOCKED');
    // Another machine's lock is live only while that machine keeps its status file fresh.
    const status = join(h.out, '_recorder', 'status.json');
    writeFileSync(lock, JSON.stringify({ pid: 1, host: 'another-machine' }));
    writeFileSync(status, '{}');
    assert.throws(() => new Recorder({ options: parseArgs(['--out', h.out]), fetchJson: async () => ({}), WebSocket: class {}, exit: () => {} }).start(), /another-machine/);
    const foreign = JSON.stringify({ pid: 1, host: 'another-machine' });
    // Replaced: a dead process's lock; an unreadable one; a live process number from before this machine last started
    // (the number was handed to another program); a number that names a group of processes, not one; another machine's
    // once its status file has gone stale.
    for (const stale of [JSON.stringify({ pid: 2 ** 22 + 12345, host: hostname() }), 'not json',
      JSON.stringify({ pid: process.ppid, host: hostname(), boot: bootedAt() - 3600 }), JSON.stringify({ pid: 0, host: hostname() }),
      JSON.stringify({ pid: -1, host: hostname() }), foreign]) {
      writeFileSync(lock, stale);
      if (stale === foreign) { const old = new Date(Date.now() - 120_000); utimesSync(status, old, old); }
      const exits = [];
      const third = new Recorder({ options: parseArgs(['--out', h.out]), fetchJson: async () => { throw new Error('offline'); }, WebSocket: class { close() {} },
        setTimer: () => ({}), clearTimer: () => {}, exit: code => exits.push(code) });
      third.start();
      assert.equal(JSON.parse(readFileSync(lock, 'utf8')).pid, process.pid, stale);
      // Worked out from two clocks read a moment apart: it may round to the second either side.
      assert.ok(Math.abs(JSON.parse(readFileSync(lock, 'utf8')).boot - bootedAt()) <= 1, stale);
      await third.stop('test');
      assert.deepEqual(exits, [0]);
    }
    // The tool itself says so and exits with 3, before it reads anything from a venue.
    writeFileSync(lock, JSON.stringify({ pid: process.pid, host: hostname(), boot: bootedAt() }));
    const refused = await run(['--out', h.out]);
    assert.equal(refused.code, 3);
    assert.match(refused.err, /Another recorder is already writing to this folder/);
    assert.equal(JSON.parse(readFileSync(lock, 'utf8')).pid, process.pid, 'the live lock was left alone');
  } finally { h.cleanup(); }
});

test('with compression off the hour files stay plain, and a file still being closed is left to finish', async () => {
  const plain = harness({ gzip: false, at: Date.UTC(2026, 10, 28, 10, 59, 40) });
  try {
    plain.recorder.start();
    await plain.settle();
    plain.socket().tick(1, '100000000', 1);
    const before = plain.state.now;
    await plain.advance(40_000);
    await plain.recorder.sweep();
    await plain.recorder.stop('test');
    assert.equal(existsSync(plain.file('BTC', 'oracle', before)), true);
    assert.equal(existsSync(`${plain.file('BTC', 'oracle', before)}.gz`), false);
    assert.deepEqual(plain.rows('BTC', 'oracle', before).map(row => row.p), [1]);
  } finally { plain.cleanup(); }
  // A file whose last rows are still on their way to the disk: the test holds its close open.
  const held = [];
  const h = harness({ at: Date.UTC(2026, 10, 28, 10, 59, 40), openFile: path => {
    const stream = createWriteStream(path, { flags: 'a' }), end = stream.end.bind(stream);
    stream.end = done => { held.push(() => end(done)); return stream; };
    return stream;
  } });
  try {
    h.recorder.start();
    await h.settle();
    for (let i = 1; i <= 200; i++) h.socket().tick(1, `${i}00000000`, i);
    const before = h.state.now, ten = h.file('BTC', 'oracle', before);
    // The hour ends and the next tick closes the 10:00 file. Until that close is through, a sweep must leave the file alone.
    h.state.now += 40_000;
    h.socket().tick(1, '900000000000', 999);
    assert.equal(held.length, 1, 'the close is waiting');
    await h.recorder.sweep();
    await h.settle();
    assert.equal(existsSync(ten), true, 'still plain: it was not compressed while closing');
    assert.equal(existsSync(`${ten}.gz`), false);
    held.splice(0).forEach(release => release());
    await h.settle();
    assert.equal(existsSync(ten), false);
    assert.equal(h.rows('BTC', 'oracle', before).length, 200, 'no row of the closing file was lost or doubled');
    assert.equal(h.recorder.status().compressFailed, 0);
    await Promise.all([h.recorder.stop('test'), (async () => { for (let i = 0; i < 50; i++) { held.splice(0).forEach(release => release()); await new Promise(resolve => setTimeout(resolve, 5)); } })()]);
  } finally { h.cleanup(); }
});

test('a sweep leaves alone a file that is still open, and a finished copy that still has its plain file', async () => {
  const h = harness({ at: Date.UTC(2026, 10, 28, 10, 59, 40) });
  try {
    h.recorder.start();
    await h.settle();
    h.socket().tick(1, '100000000', 1);
    await h.settle();
    const ten = h.file('BTC', 'oracle');
    // The hour has just ended, and nothing has closed the file yet: no row came, and the ten-second look has not run.
    h.state.now += 40_000;
    await h.recorder.sweep();
    assert.equal(existsSync(ten), true, 'an open file is not compressed under the recorder');
    assert.equal(existsSync(`${ten}.gz`), false);
    // The hour in progress, with a finished copy beside its plain file (a run died before removing the plain one).
    // The copy repeats the plain file's rows, so it must not be published.
    const now = h.file('ZEC', 'oracle');
    mkdirSync(join(now, '..'), { recursive: true });
    writeFileSync(now, '{"a":"ZEC","p":1,"e":1,"r":1}\n');
    writeFileSync(`${now}.gz.ready`, gzipSync('{"a":"ZEC","p":1,"e":1,"r":1}\n'));
    await h.recorder.sweep();
    assert.equal(existsSync(`${now}.gz`), false, 'not published beside its plain file');
    assert.equal(existsSync(now), true);
    // When the hour ends the plain file is compressed afresh, and the hour holds its row once.
    await h.advance(HOUR);
    await h.recorder.sweep();
    assert.deepEqual(h.rows('ZEC', 'oracle', h.state.now - HOUR).map(row => row.p), [1]);
    assert.equal(existsSync(`${now}.gz.ready`), false);
    assert.equal(existsSync(ten), false, 'the open file was closed and compressed by the ten-second look');
    assert.deepEqual(h.rows('BTC', 'oracle', Date.UTC(2026, 10, 28, 10, 59, 50)).map(row => row.p), [1]);
    await h.recorder.stop('test');
  } finally { h.cleanup(); }
});

test('a finished copy that was never published is published before its hour gets a new file', async () => {
  const h = harness();
  try {
    // A crash after the plain file was removed, then a clock set back into the same hour: only the finished copy is there.
    const path = h.file('BTC', 'oracle');
    mkdirSync(join(path, '..'), { recursive: true });
    writeFileSync(`${path}.gz.ready`, gzipSync('{"a":"BTC","p":1,"e":1,"r":1}\n'));
    h.recorder.start();
    h.socket()?.tick(1, '200000000', 2);
    await h.settle();
    h.socket().tick(1, '200000000', 2);
    await h.settle();
    assert.equal(existsSync(`${path}.gz`), true, 'published when the hour was opened');
    assert.equal(existsSync(`${path}.gz.ready`), false);
    await h.advance(HOUR);
    assert.deepEqual(h.rows('BTC', 'oracle', T0).map(row => row.p), [1, 2], 'the earlier rows were kept, and the new ones added after them');
    await h.recorder.stop('test');
  } finally { h.cleanup(); }
});

test('a folder that cannot be read is passed over, the others are swept, and the full pass is made again', async t => {
  if (process.getuid?.() === 0) return t.skip('the superuser can read any folder');
  const h = harness();
  const locked = join(h.out, 'BTC', 'oracle');
  try {
    const old = ms => { const path = h.file(ms.coin, 'oracle', T0 - 5 * 24 * HOUR); mkdirSync(join(path, '..'), { recursive: true }); writeFileSync(path, '{"r":1}\n'); return path; };
    const shut = old({ coin: 'BTC' }), fine = old({ coin: 'ZEC' });
    chmodSync(locked, 0o000);
    h.recorder.start();
    assert.equal(await h.until(() => existsSync(`${fine}.gz`)), true, 'the folders that could be read were swept');
    assert.equal(await h.until(() => /"type":"sweep-skipped","folders":1/.test(readFileSync(join(h.out, '_recorder', 'events.jsonl'), 'utf8'))), true);
    chmodSync(locked, 0o755);
    assert.deepEqual([existsSync(shut), existsSync(`${shut}.gz`)], [true, false], 'the folder that could not be read was left as it was');
    // Five days old is outside what the hourly pass looks at: only a second full pass can reach it.
    await h.advance(HOUR + 1000);
    assert.equal(await h.until(() => existsSync(`${shut}.gz`)), true, 'the next pass looked at every folder again');
    assert.equal(existsSync(shut), false);
    await h.recorder.stop('test');
  } finally { try { chmodSync(locked, 0o755); } catch { /* already removed */ } h.cleanup(); }
});

test('a short-lived copy deletes compressed hours older than it keeps, and can never be an archive by mistake', async () => {
  const h = harness({ keepHours: 2 });
  try {
    h.recorder.start();
    const marker = JSON.parse(readFileSync(join(h.out, '_recorder', 'standby'), 'utf8'));
    assert.deepEqual([marker.host, marker.keepHours], [hostname(), 2]);
    // The pass the recorder makes by itself at the start is over before the old hours below are put there,
    // so each pass that follows is one the test asked for.
    assert.equal(await h.until(() => h.recorder.status().lastReadOkAt.sweep !== null), true);
    const place = (hoursAgo, suffix = '.gz') => {
      const path = h.file('ZEC', 'oracle', T0 - hoursAgo * HOUR) + suffix;
      mkdirSync(join(path, '..'), { recursive: true });
      writeFileSync(path, suffix === '.gz' ? gzipSync('{"r":1}\n') : '{"r":1}\n');
      return path;
    };
    // T0 is 10:00:05. The 07:00 hour ended two hours and five seconds ago; the 08:00 hour one hour and five seconds ago.
    const dayAgo = place(30), justOver = place(3), within = place(2), last = place(1);
    const stranger = join(justOver, '..', 'notes.txt'), unfinished = place(8, '');
    writeFileSync(stranger, 'not ours');
    await h.recorder.sweep();
    assert.deepEqual([dayAgo, justOver, within, last].map(path => existsSync(path)), [false, false, true, true], 'only hours that ended more than two hours ago went');
    assert.equal(existsSync(join(dayAgo, '..')), false, 'a day left empty is removed');
    assert.equal(existsSync(stranger), true, 'a file that is not an hour of this recorder is never deleted');
    // An old hour that had not been compressed yet is finished first, never deleted as it stands; a later pass drops the result.
    assert.deepEqual([existsSync(unfinished), existsSync(`${unfinished}.gz`)], [false, true]);
    assert.deepEqual([h.recorder.status().keepHours, h.recorder.status().hourFilesDropped, h.recorder.status().compressFailed], [2, 2, 0]);
    await h.recorder.sweep();
    assert.equal(existsSync(`${unfinished}.gz`), false);
    assert.equal(h.recorder.status().hourFilesDropped, 3);
    await h.recorder.stop('test');
    // The marked folder does not start without --keep-hours.
    const plain = new Recorder({ options: parseArgs(['--out', h.out]), fetchJson: async () => ({}), WebSocket: class {}, exit: () => {} });
    assert.throws(() => plain.start(), error => error.code === 'ESTANDBY' && /short-lived copy/.test(error.message));
    assert.equal(existsSync(join(h.out, '_recorder', 'lock')), false, 'the refused start released the lock');
  } finally { h.cleanup(); }
  // A folder that already holds a recording is never turned into one that deletes.
  const archive = harness();
  try {
    const kept = archive.file('ZEC', 'oracle', T0 - 30 * HOUR);
    mkdirSync(join(kept, '..'), { recursive: true });
    writeFileSync(`${kept}.gz`, gzipSync('{"r":1}\n'));
    const wrong = new Recorder({ options: { ...parseArgs(['--out', archive.out]), keepHours: 1 }, fetchJson: async () => ({}), WebSocket: class {}, exit: () => {} });
    assert.throws(() => wrong.start(), error => error.code === 'ESTANDBY' && /already holds a recording/.test(error.message));
    assert.equal(existsSync(`${kept}.gz`), true);
    assert.equal(existsSync(join(archive.out, '_recorder', 'standby')), false);
    // An archive never deletes, however old its hours.
    archive.recorder.start();
    await archive.settle();
    await archive.recorder.sweep();
    assert.equal(existsSync(`${kept}.gz`), true);
    assert.equal('keepHours' in archive.recorder.status(), false);
    await archive.recorder.stop('test');
    const refused = await run(['--out', archive.out, '--keep-hours', '2']);
    assert.equal(refused.code, 2);
    assert.match(refused.err, /already holds a recording/);
  } finally { archive.cleanup(); }
});

test('a read that fails is tried again soon, however rarely it is normally made, and the hourly sweep looks only at recent days', async () => {
  const h = harness();
  try {
    h.state.products = [{ id: 'ZEC-USD', base_currency: 'ZEC', status: 'online' }];
    h.state.fail.add('/products');
    const old = h.file('ZEC', 'oracle', T0 - 5 * 24 * HOUR);
    h.recorder.start();
    // The product list is read every ten minutes. Its first read (after five seconds) fails, and is tried again in five more.
    await h.advance(5500);
    assert.equal(h.recorder.status().failuresInARow['coinbase-products'], 1);
    h.state.fail.clear();
    await h.advance(5000);
    assert.equal(h.recorder.status().failuresInARow['coinbase-products'], 0);
    assert.equal(h.state.coinbase.length, 1, 'Coinbase is being read within seconds of the failure, not ten minutes later');
    assert.equal(h.recorder.status().coinbase.connected, false, 'a socket that has not opened yet is not connected');
    h.state.coinbase[0].onopen();
    assert.equal(h.recorder.status().coinbase.connected, true);
    // A plain file from five days ago that appears later is left for the next start: the hourly pass reads only the last two days.
    mkdirSync(join(old, '..'), { recursive: true });
    writeFileSync(old, '{"a":"ZEC","p":1,"e":1,"r":1}\n');
    const recent = h.file('ZEC', 'oracle', h.state.now - 30 * HOUR);
    mkdirSync(join(recent, '..'), { recursive: true });
    writeFileSync(recent, '{"a":"ZEC","p":2,"e":2,"r":2}\n');
    h.state.sockets.forEach(socket => { socket.onmessage = null; });
    assert.equal(await h.recorder.sweep({ full: false }), true);
    assert.equal(existsSync(`${recent}.gz`), true);
    assert.equal(existsSync(old), true, 'older than the hourly pass looks');
    await h.recorder.sweep();
    assert.equal(existsSync(`${old}.gz`), true, 'the full pass takes it');
    await h.recorder.stop('test');
  } finally { h.cleanup(); }
});

test('a process whose event loop has stopped is killed, and one that is merely idle is not', async () => {
  const RUN = fileURLToPath(new URL('../tools/lib/market-recorder-run.mjs', import.meta.url));
  // The watcher waits a full second without a beat: a busy test machine can starve an idle child for less.
  const script = body => `import { startWatchdog } from ${JSON.stringify(RUN)}; startWatchdog({ beatMs: 20, checkMs: 100, stalledChecks: 10 }); ${body}`;
  const runScript = body => new Promise(resolve => {
    const child = spawn(process.execPath, ['--input-type=module', '-e', script(body)], { stdio: 'ignore' });
    const timer = setTimeout(() => child.kill('SIGTERM'), 10_000);
    child.on('close', (code, signal) => { clearTimeout(timer); resolve({ code, signal }); });
  });
  // A blocked loop cannot beat, so the watcher's own thread ends the process. (The watcher needs a
  // few turns of the loop to start, which a recorder that has just opened its files always gives it.)
  assert.deepEqual(await runScript('setTimeout(() => { for (;;) {} }, 300);'), { code: null, signal: 'SIGKILL' });
  // An idle but healthy process keeps beating and ends in its own time.
  assert.deepEqual(await runScript('setTimeout(() => process.exit(0), 1500);'), { code: 0, signal: null });
});

test('while a Jupiter catalog has not answered, the Coinbase list is read again soon, a few times, then at its usual pace', async () => {
  const h = harness();
  try {
    h.state.products = [{ id: 'BTC-USD', base_currency: 'BTC', status: 'online' }, { id: 'ZEC-USD', base_currency: 'ZEC', status: 'online' }];
    h.state.fail.add('yolo');
    const reads = () => h.state.calls.filter(url => url === ENDPOINTS.coinbaseProducts).length;
    h.recorder.start();
    await h.advance(5500);
    assert.equal(reads(), 1);
    // Only the pool's coins are known so far, and Coinbase is recorded for those at once.
    assert.deepEqual(h.recorder.status().coinbase.products, ['BTC-USD', 'ZEC-USD']);
    await h.advance(15_000);
    assert.equal(reads(), 2, 'fifteen seconds later, not ten minutes');
    await h.advance(8 * 15_000);
    assert.equal(reads(), 9, 'eight early reads at most');
    await h.advance(300_000);
    assert.equal(reads(), 9, 'then the usual ten minutes');
    await h.advance(310_000);
    assert.equal(reads(), 10);
    await h.recorder.stop('test');
  } finally { h.cleanup(); }
});
