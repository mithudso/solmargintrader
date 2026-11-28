/**
 * Pure parts of the market recorder: reading the public catalogs, shaping rows
 * and naming files. No clock, network or disk here; tools/market-recorder.mjs
 * does the I/O.
 *
 * Every row is one JSON object on one line. `r` is always the local receive
 * time in milliseconds; a venue's own time, where it gives one, is kept beside
 * it under its own key so the two clocks are never mixed.
 */

export const ENDPOINTS = Object.freeze({
  yoloMarkets: 'https://yolo-api.jup.ag/markets',
  oracleStream: 'wss://perps-api.jup.ag/v1/pyth/stream',
  gumMarkets: 'https://api.gum.ag/app/perps/markets',
  gumFunding: 'https://api.gum.ag/app/perps/fundingRate/',
  poolInfo: 'https://perps-api.jup.ag/v1/pool-info?mint=',
  coinbaseProducts: 'https://api.exchange.coinbase.com/products',
  coinbaseStream: 'wss://ws-feed.exchange.coinbase.com',
});

// The three Perps markets priced by the oracle, with the oracle feed and the pool mint of each.
export const JLP_MARKETS = Object.freeze({
  SOL: { feedId: 6, mint: 'So11111111111111111111111111111111111111112' },
  ETH: { feedId: 2, mint: '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs' },
  BTC: { feedId: 1, mint: '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh' },
});

export const STREAMS = Object.freeze(['oracle', 'perps-book', 'perps-funding', '1000x-market', 'perps-pool', 'coinbase-book', 'coinbase-trades', 'coinbase-depth']);

const COIN = /^[A-Z0-9]{1,16}$/;
const DIGITS = /^\d{1,24}$/;
const finite = value => typeof value === 'number' && Number.isFinite(value);
/** A venue number given as a number or a plain decimal string; anything else is null. */
export function decimal(value) {
  if (finite(value)) return value;
  return typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : null;
}
const positive = value => { const n = decimal(value); return n !== null && n > 0 ? n : null; };
const flag = value => typeof value === 'boolean' ? value : null;

/** A coin symbol that is safe as a folder name, or null. The catalogs are remote input. */
export const safeCoin = symbol => typeof symbol === 'string' && COIN.test(symbol) ? symbol : null;

/**
 * The 1000x catalog: every listed market with its oracle feed, open interest
 * and volume. A market that is closed for the weekend is still listed.
 */
export function parseYoloMarkets(payload) {
  // The catalog is an object with a `markets` list.
  const rows = payload?.markets;
  if (!Array.isArray(rows)) throw new Error('The 1000x catalog had no market list.');
  const seen = new Set(), out = [];
  for (const row of rows) {
    const coin = safeCoin(row?.symbol);
    if (!coin || seen.has(coin) || !Number.isSafeInteger(row.feedId) || row.feedId <= 0) continue;
    seen.add(coin);
    // A flag the catalog did not send is unknown, not "open".
    out.push({ coin, feedId: row.feedId, closed: flag(row.closed), closeOnly: flag(row.closeOnly),
      longOi: decimal(row.longOi), shortOi: decimal(row.shortOi), volume24h: decimal(row.volume24h), totalVolume: decimal(row.totalVolume) });
  }
  if (!out.length) throw new Error('The 1000x catalog listed no usable market.');
  return out;
}

/**
 * The Perps order-book markets: top of book, mark and index price, last trade,
 * open interest and 24 hour volume for every listed coin, in one read.
 */
export function parseGumMarkets(payload) {
  if (!Array.isArray(payload)) throw new Error('The Perps market list was not a list.');
  const seen = new Set(), out = [];
  for (const row of payload) {
    const coin = safeCoin(row?.symbol);
    if (!coin || seen.has(coin)) continue;
    seen.add(coin);
    out.push({ coin, status: typeof row.status === 'string' ? row.status.slice(0, 24) : null, venueTime: decimal(row.timestamp), updatedMs: decimal(row.lastUpdatedMs),
      bid: positive(row.bestBid), ask: positive(row.bestAsk), mid: positive(row.midPrice), mark: positive(row.markPrice), index: positive(row.indexPrice),
      last: positive(row.lastTradePrice), openInterest: decimal(row.openInterest), openInterestBase: decimal(row.openInterestBase), volume24h: decimal(row.volume24h),
      maxLeverage: decimal(row.maxLeverage) });
  }
  if (!out.length) throw new Error('The Perps market list had no usable market.');
  return out;
}

/** One funding read for a Perps order-book market, or null when it is not for that coin. */
export function parseFunding(coin, payload) {
  if (payload?.symbol !== coin) return null;
  const row = { rateBps1h: decimal(payload.rateBps1h), fundingRate: decimal(payload.fundingRate), predictedFundingRate: decimal(payload.predictedFundingRate),
    intervalSeconds: decimal(payload.fundingIntervalSeconds), nextCollection: decimal(payload.nextFundingCollectionTime), venueTime: decimal(payload.fundingUpdateTimestamp) };
  return row.rateBps1h === null && row.fundingRate === null ? null : row;
}

/** One pool read for an oracle-priced Perps market: fees, borrow rates and how much of the pool is in use. */
export function parsePool(payload) {
  const row = { openFeePercent: decimal(payload?.openFeePercent), maxPriceImpactFeePercent: decimal(payload?.maxPriceImpactFeePercent),
    longBorrowRatePercent: decimal(payload?.longBorrowRatePercent), shortBorrowRatePercent: decimal(payload?.shortBorrowRatePercent),
    longUtilizationPercent: decimal(payload?.longUtilizationPercent), shortUtilizationPercent: decimal(payload?.shortUtilizationPercent),
    longAvailableLiquidity: decimal(payload?.longAvailableLiquidity), shortAvailableLiquidity: decimal(payload?.shortAvailableLiquidity) };
  return Object.values(row).every(value => value === null) ? null : row;
}

/** Which oracle feed belongs to which coin: the 1000x catalog's, plus the oracle-priced Perps markets. */
export function feedMap(yoloMarkets) {
  const map = new Map(Object.entries(JLP_MARKETS).map(([coin, market]) => [market.feedId, coin]));
  for (const market of yoloMarkets) if (!map.has(market.feedId)) map.set(market.feedId, market.coin);
  return map;
}

/** The subscription the oracle stream expects for these feeds. */
export function oracleSubscription(feedIds) {
  return { type: 'subscribe', subscriptionId: 1, channel: 'fixed_rate@200ms', priceFeedIds: [...feedIds].sort((a, b) => a - b),
    properties: ['price', 'exponent', 'feedUpdateTimestamp'], formats: [], ignoreInvalidFeeds: true };
}

/**
 * The oracle ticks in one stream frame, as { coin, key, row }. `row` has the
 * shape the scalp study reads: a coin, p price, e the oracle's own time in
 * milliseconds, r the receive time. `key` is the oracle time, for dropping a
 * frame that repeats the last tick.
 */
export function oracleTicks(frame, feeds, receivedMs) {
  if (frame?.type !== 'streamUpdated' || !Array.isArray(frame.parsed?.priceFeeds)) return [];
  const out = [];
  for (const feed of frame.parsed.priceFeeds) {
    const coin = feeds.get(feed?.priceFeedId);
    if (!coin || typeof feed.price !== 'string' || !DIGITS.test(feed.price) || !Number.isInteger(feed.exponent) || feed.exponent > 0 || feed.exponent < -18
        || !Number.isSafeInteger(feed.feedUpdateTimestamp) || feed.feedUpdateTimestamp <= 0) continue;
    // Read as one decimal literal, which is exact; multiplying by a power of ten is not.
    const price = Number(`${feed.price}e${feed.exponent}`);
    if (!(price > 0) || !Number.isFinite(price)) continue;
    out.push({ coin, key: feed.feedUpdateTimestamp, row: { a: coin, p: price, e: feed.feedUpdateTimestamp / 1000, r: receivedMs } });
  }
  return out;
}

/* ---------------------------------------------------------------- Coinbase -- */

// Jupiter's prices are an oracle's, with no order book and no trades of their own. Coinbase's public
// book and trades for the same coins are recorded beside them: in the study its book moved a second
// or two before the oracle did.
const MAX_LEVELS = 200_000;
/** How far from the middle the recorded depth reaches, in basis points. */
export const DEPTH_BPS = Object.freeze([5, 25]);

/** The recorded coins Coinbase has an open USD market for, as [{ coin, product }]. */
export function parseCoinbaseProducts(payload, coins) {
  if (!Array.isArray(payload)) throw new Error('The Coinbase product list was not a list.');
  const wanted = new Set(coins), out = [];
  for (const row of payload) {
    const coin = safeCoin(row?.base_currency);
    if (!coin || !wanted.has(coin) || row.id !== `${coin}-USD` || row.status !== 'online' || row.trading_disabled === true) continue;
    wanted.delete(coin);
    out.push({ coin, product: row.id });
  }
  return out.sort((a, b) => a.coin.localeCompare(b.coin));
}

/** The subscription for those products: the batched book, every trade, and a heartbeat that shows the stream is alive. */
export const coinbaseSubscription = products => ({ type: 'subscribe', product_ids: [...products].sort(), channels: ['level2_batch', 'matches', 'heartbeat'] });

/**
 * One product's order book, kept from the stream's snapshot and its changes,
 * for the best bid and ask and the size resting near them. Prices and sizes
 * are checked on the way in: a level that is not a positive price and a
 * non-negative size is refused, and the book is then rebuilt from a new snapshot.
 */
export class TopOfBook {
  #bids = new Map(); #asks = new Map(); #bestBid = null; #bestAsk = null;

  static #level(price, size) {
    const p = decimal(price), q = decimal(size);
    if (p === null || !(p > 0) || q === null || q < 0) throw new Error('A Coinbase book level was not a price and a size.');
    return [p, q];
  }
  #rescan(bids) {
    let best = null;
    for (const price of (bids ? this.#bids : this.#asks).keys()) if (best === null || (bids ? price > best : price < best)) best = price;
    if (bids) this.#bestBid = best; else this.#bestAsk = best;
  }

  load(bids, asks) {
    if (!Array.isArray(bids) || !Array.isArray(asks) || bids.length > MAX_LEVELS || asks.length > MAX_LEVELS) throw new Error('A Coinbase book snapshot was not two lists of levels.');
    this.#bids = new Map(); this.#asks = new Map();
    for (const [side, rows] of [[this.#bids, bids], [this.#asks, asks]]) {
      for (const row of rows) {
        if (!Array.isArray(row) || row.length < 2) throw new Error('A Coinbase book level was not a price and a size.');
        const [price, size] = TopOfBook.#level(row[0], row[1]);
        if (size > 0) side.set(price, size);
      }
    }
    this.#rescan(true); this.#rescan(false);
  }

  /** One change from the stream: the new size resting at a price, zero when the level is gone. */
  change(side, price, size) {
    if (side !== 'buy' && side !== 'sell') throw new Error('A Coinbase book change had no side.');
    const bids = side === 'buy', levels = bids ? this.#bids : this.#asks, [p, q] = TopOfBook.#level(price, size), best = bids ? this.#bestBid : this.#bestAsk;
    if (q === 0) {
      levels.delete(p);
      // Only losing the best level means looking for the next one.
      if (p === best) this.#rescan(bids);
      return;
    }
    levels.set(p, q);
    if (levels.size > MAX_LEVELS) throw new Error('A Coinbase book grew past its limit.');
    if (best === null || (bids ? p > best : p < best)) { if (bids) this.#bestBid = p; else this.#bestAsk = p; }
  }

  /** Best bid and ask with their sizes, or null while a side is empty or the book is crossed. */
  top() {
    const bid = this.#bestBid, ask = this.#bestAsk;
    if (bid === null || ask === null || !(bid < ask)) return null;
    return { bid, ask, bidSize: this.#bids.get(bid), askSize: this.#asks.get(ask) };
  }

  /** Size resting within `bps` basis points of the middle on each side, or null with no usable top. */
  depth(bps) {
    const top = this.top();
    if (!top) return null;
    const mid = (top.bid + top.ask) / 2, floor = mid * (1 - bps / 1e4), ceiling = mid * (1 + bps / 1e4);
    let bid = 0, ask = 0;
    for (const [price, size] of this.#bids) if (price >= floor) bid += size;
    for (const [price, size] of this.#asks) if (price <= ceiling) ask += size;
    return { bid, ask };
  }

  get levels() { return this.#bids.size + this.#asks.size; }
}

const venueMs = text => { const ms = typeof text === 'string' ? Date.parse(text) : NaN; return Number.isFinite(ms) ? ms : null; };

/**
 * The rows one Coinbase stream message gives, as [{ coin, stream, row }].
 * `state` is { products: Map(product -> coin), books: Map(product -> TopOfBook),
 * tops: Map(product -> last written top), trades: Map(product -> last trade id) }
 * and is updated in place. A book row is given only when the best bid, the best
 * ask or a size at them changed; a trade only once. `t` is Coinbase's own time.
 * Throws when the message cannot be trusted, and the caller then starts the
 * stream again from a new snapshot.
 */
export function coinbaseRows(message, state, receivedMs) {
  const type = message?.type;
  if (type === 'error') throw new Error(`Coinbase refused the stream: ${String(message.message ?? '').slice(0, 80)}`);
  const coin = state.products.get(message?.product_id);
  if (!coin) return [];
  const product = message.product_id, t = venueMs(message.time);
  if (type === 'match') {
    const price = positive(message.price), size = positive(message.size);
    // A trade is written once: after a reconnect the stream may repeat the last one.
    if (price === null || size === null || !Number.isSafeInteger(message.trade_id) || message.trade_id <= (state.trades.get(product) ?? 0)) return [];
    state.trades.set(product, message.trade_id);
    return [{ coin, stream: 'coinbase-trades', row: { r: receivedMs, t, price, size, side: message.side === 'buy' || message.side === 'sell' ? message.side : null, tradeId: message.trade_id } }];
  }
  if (type === 'last_match') {
    // The trade before the subscription began: remembered so it is not written when it comes again, never recorded as new.
    if (Number.isSafeInteger(message.trade_id)) state.trades.set(product, Math.max(message.trade_id, state.trades.get(product) ?? 0));
    return [];
  }
  if (type === 'snapshot') {
    const book = new TopOfBook();
    book.load(message.bids, message.asks);
    state.books.set(product, book);
  } else if (type === 'l2update') {
    const book = state.books.get(product);
    // Changes before the snapshot belong to a book we do not have.
    if (!book) return [];
    if (!Array.isArray(message.changes)) throw new Error('A Coinbase book update had no changes.');
    for (const change of message.changes) {
      if (!Array.isArray(change) || change.length < 3) throw new Error('A Coinbase book change was malformed.');
      book.change(change[0], change[1], change[2]);
    }
  } else return [];
  const top = state.books.get(product).top();
  if (!top) return [];
  const last = state.tops.get(product);
  if (last && last.bid === top.bid && last.ask === top.ask && last.bidSize === top.bidSize && last.askSize === top.askSize) return [];
  state.tops.set(product, top);
  return [{ coin, stream: 'coinbase-book', row: { r: receivedMs, t, ...top } }];
}

/** The depth rows for every product with a usable book: size resting within each of DEPTH_BPS of the middle. */
export function coinbaseDepth(state, receivedMs) {
  const out = [];
  for (const [product, book] of state.books) {
    const coin = state.products.get(product), top = book.top();
    if (!coin || !top) continue;
    const row = { r: receivedMs, bid: top.bid, ask: top.ask };
    for (const bps of DEPTH_BPS) { const depth = book.depth(bps); row[`bid${bps}`] = depth.bid; row[`ask${bps}`] = depth.ask; }
    out.push({ coin, row });
  }
  return out;
}

// Clock fields move on every read whether or not the market did. They are recorded, but they do not make a row new.
const CLOCK_FIELDS = new Set(['r', 'venueTime', 'updatedMs']);
/** Whether a polled snapshot differs from the last one written, in anything but its clock fields. */
export function changed(previous, row) {
  if (!previous) return true;
  for (const key of Object.keys(row)) if (!CLOCK_FIELDS.has(key) && previous[key] !== row[key]) return true;
  return false;
}

const two = value => String(value).padStart(2, '0');
/** UTC day and hour of a time, as { day: 'YYYY-MM-DD', hour: 'YYYYMMDDTHH' }. */
export function hourOf(ms) {
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) throw new RangeError('Not a time.');
  const y = date.getUTCFullYear(), m = two(date.getUTCMonth() + 1), d = two(date.getUTCDate());
  return { day: `${y}-${m}-${d}`, hour: `${y}${m}${d}T${two(date.getUTCHours())}` };
}

/** The first millisecond of an hour named like 20261128T10 (the name hourOf gives it). */
export function hourStart(hour) {
  const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})$/.exec(hour);
  if (!m) throw new RangeError('Not an hour name.');
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]));
}

/** Where a row goes, relative to the output folder: <COIN>/<stream>/<day>/<COIN>-<stream>-<hour>.jsonl */
export function relativePath(coin, stream, ms) {
  if (!safeCoin(coin)) throw new RangeError('Not a coin symbol.');
  if (!STREAMS.includes(stream)) throw new RangeError('Not a recorder stream.');
  const { day, hour } = hourOf(ms);
  return `${coin}/${stream}/${day}/${coin}-${stream}-${hour}.jsonl`;
}

/** Wait before the next try after `failures` in a row: half a second doubling to a minute. */
export const backoffMs = failures => Math.min(60_000, 500 * 2 ** Math.max(0, Math.min(failures, 10) - 1));

// An hour between reads is already far more than any of these needs; a typo of many zeros should be refused, not obeyed.
const MAX_EVERY_S = 3600;
const OPTION_NAMES = new Map([['--out', 'out'], ['--minutes', 'minutes'], ['--book-every', 'bookEvery'], ['--catalog-every', 'catalogEvery'],
  ['--funding-every', 'fundingEvery'], ['--pool-every', 'poolEvery'], ['--keep-hours', 'keepHours']]);
/** A short-lived copy keeps at most a day: the hourly sweep that drops old hours looks at the last two days. */
const MAX_KEEP_HOURS = 24;

/** Command-line options. Every interval is in seconds; `--minutes 0` records until stopped. */
export function parseArgs(argv, defaults = { out: '/Volumes/dasdata/CoinTradingData', minutes: 0, bookEvery: 2, catalogEvery: 15, fundingEvery: 60, poolEvery: 30, gzip: true,
  keepHours: 0 }) {
  const out = { ...defaults };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--no-gzip') { out.gzip = false; continue; }
    if (arg === '--help' || arg === '-h') { out.help = true; continue; }
    const key = OPTION_NAMES.get(arg);
    if (!key || i + 1 >= argv.length) throw new RangeError(`Unknown or incomplete option ${arg}.`);
    const value = argv[++i];
    if (key === 'out') { if (!value.startsWith('/')) throw new RangeError('--out must be an absolute folder.'); out.out = value.replace(/\/+$/, '') || '/'; continue; }
    const number = value.trim() === '' ? NaN : Number(value);
    if (key === 'minutes') { if (!Number.isFinite(number) || number < 0) throw new RangeError('--minutes needs a number of minutes, 0 or more.'); }
    else if (key === 'keepHours') {
      if (!Number.isInteger(number) || number < 1 || number > MAX_KEEP_HOURS) throw new RangeError(`--keep-hours needs a whole number of hours from 1 to ${MAX_KEEP_HOURS}.`);
    }
    else if (!Number.isFinite(number) || number < 1 || number > MAX_EVERY_S) throw new RangeError(`${arg} needs a number of seconds from 1 to ${MAX_EVERY_S}.`);
    out[key] = number;
  }
  return out;
}

export const USAGE = `Record every Jupiter 1000x and Perps market to one folder per coin.

  node tools/market-recorder.mjs [--out /Volumes/dasdata/CoinTradingData] [--minutes 0]
       [--book-every 2] [--catalog-every 15] [--funding-every 60] [--pool-every 30] [--no-gzip]
       [--keep-hours N]

--minutes 0 (the default) records until stopped. The -every options are seconds between reads.

--keep-hours N (1 to 24) makes the folder a short-lived copy: compressed hours that ended more
than N hours ago are deleted. It is for a second machine whose rows fill gaps in the main
recording (tools/market-recorder-fill.mjs). It starts only in an empty folder, which it marks
(_recorder/standby), or in one it marked before; a marked folder never starts without it.

Public reads only: no wallet, no key, nothing sent to a venue but the two stream subscriptions.
The output folder must already exist. If it goes away, or stops being the same disk, the
recorder stops with an error instead of writing somewhere else; start it again when the disk is back.

  <COIN>/oracle/         oracle price ticks, about two a second (1000x markets and SOL, ETH, BTC Perps)
  <COIN>/perps-book/     Perps order-book markets: best bid and ask, mark, index, last trade, open interest, 24 h volume
  <COIN>/perps-funding/  Perps funding rate
  <COIN>/1000x-market/   1000x open interest long and short, 24 h volume, open or closed
  <COIN>/perps-pool/     SOL, ETH, BTC Perps pool: fees, borrow rates, utilization
  <COIN>/coinbase-book/  Coinbase best bid and ask with their sizes, a row each time one changes (coins Coinbase lists in USD)
  <COIN>/coinbase-trades/ every Coinbase trade: price, size, side
  <COIN>/coinbase-depth/ Coinbase size resting within 5 and 25 basis points of the middle, once a second
  _recorder/             status.json, rewritten every ten seconds; events.jsonl; and lock, which names the
                         one recorder writing here (a second one is refused)

Files are one per hour (UTC), JSON lines, gzipped within seconds of the hour ending. A polled
stream writes a row when something changed, and one at the start of every hour.`;
