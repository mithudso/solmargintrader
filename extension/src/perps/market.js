import { MARKETS } from './model.js';
import { decodeHistory, JUPITER_ENDPOINTS } from '../1000x/feed.js';

const PERPS = 'https://perps-api.jup.ag/v1/';
const GUM = 'https://api.gum.ag/app/perps/';
const PRICES = PERPS + 'pyth/fixed_rate%40200ms/prices';
const decimal = value => typeof value === 'number' ? value
  : typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : NaN;
const positive = value => Number.isFinite(value) && value > 0;

function marketFor(asset) {
  if (!Object.hasOwn(MARKETS, asset)) throw new Error('Unsupported Perps market.');
  return MARKETS[asset];
}

export async function readJson(url, signal) {
  const timeout = AbortSignal.timeout(10000);
  const response = await fetch(url, {
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    credentials: 'omit', redirect: 'error', cache: 'no-store',
  });
  if (!response.ok) throw new Error(`Public market request returned HTTP ${response.status}.`);
  return response.json();
}

export function jlpTerms(asset, payload, direction) {
  const market = marketFor(asset);
  const baseBps = decimal(payload?.openFeePercent) * 100;
  const maxImpactBps = decimal(payload?.maxPriceImpactFeePercent) * 100;
  const carryBps = decimal(direction === 1 ? payload?.longBorrowRatePercent : payload?.shortBorrowRatePercent) * 100;
  if (market.venue !== 'JLP' || !positive(baseBps) || !positive(maxImpactBps) || !(carryBps >= 0)) {
    throw new Error('JLP fee or borrow fields are unavailable.');
  }
  return { ...market, baseBps, maxImpactBps, carryBps, maintenanceBps: 20 };
}

export function gumTerms(asset, catalog, funding, now) {
  const market = marketFor(asset);
  const matches = Array.isArray(catalog) ? catalog.filter(row => row?.symbol === asset) : [];
  const row = matches[0];
  const tier = row?.riskTiers?.[0];
  const limits = row?.orderLimitConfig?.market;
  if (market.venue !== 'GUM' || matches.length !== 1 || funding?.symbol !== asset
      || !Number.isFinite(funding.rateBps1h) || !positive(funding.fundingUpdateTimestamp)
      || funding.fundingUpdateTimestamp < now - 300 || funding.fundingUpdateTimestamp > now + 5
      || ![row?.maxLeverage, row?.markPrice, row?.timestamp, row?.takerFeeBps,
        row?.makerFeeBps, row?.liquidationFeeBps, tier?.maintenanceMarginRatioBps,
        tier?.notionalCap, limits?.maxOpenOrderNotional, limits?.minOrderNotional,
        limits?.maxOpenOrderQty, row?.stepSize].every(positive)
      || row.timestamp < now - 20 || row.timestamp > now + 5) {
    throw new Error('GUM mark, funding or maintenance fields are unavailable.');
  }
  return {
    terms: { ...market, max: row.maxLeverage, baseBps: row.takerFeeBps, makerBps: row.makerFeeBps,
      maintenanceBps: tier.maintenanceMarginRatioBps, firstTierCap: tier.notionalCap,
      maxOrder: limits.maxOpenOrderNotional, minOrder: limits.minOrderNotional,
      maxQty: limits.maxOpenOrderQty, stepSize: row.stepSize, liquidationBps: row.liquidationFeeBps, carryBps: funding.rateBps1h },
    mark: { time: row.timestamp, price: row.markPrice },
  };
}

export function parseJlpPrices(asset, value, now) {
  const market = marketFor(asset);
  if (market.venue !== 'JLP' || !Array.isArray(value?.data) || value.data.length > 150) {
    throw new Error('Invalid Pyth price response.');
  }
  const byTime = new Map();
  for (const row of value.data) {
    if (row?.price_feed_id !== market.feed || !Number.isSafeInteger(row.feed_update_timestamp)
        || !Number.isSafeInteger(row.price) || !Number.isInteger(row.exponent) || Math.abs(row.exponent) > 18) continue;
    const point = { price: row.price * 10 ** row.exponent, time: row.feed_update_timestamp / 1000000 };
    if (positive(point.price) && point.time >= now - 25 && point.time <= now + 2) {
      if (byTime.has(point.time) && byTime.get(point.time).price !== point.price) throw new Error('Conflicting oracle samples.');
      byTime.set(point.time, point);
    }
  }
  const points = [...byTime.values()].sort((a, b) => a.time - b.time);
  if (!points.length || points.at(-1).time < now - 12) throw new Error('Pyth price is stale.');
  return points;
}

export function parseGumMinutes(asset, payload) {
  if (!Array.isArray(payload) || payload.length > 5000) throw new Error('Invalid GUM candle response.');
  const seen = new Map();
  for (const row of payload) {
    if (row?.s !== asset || row.i !== '1m' || !Number.isSafeInteger(row.t) || row.t % 60000
        || row.T !== row.t + 60000 || ![row.o, row.h, row.l, row.c].every(positive)
        || row.h < Math.max(row.o, row.c, row.l) || row.l > Math.min(row.o, row.c, row.h)) {
      throw new Error('Invalid GUM candle row.');
    }
    const candle = { time: row.t / 1000, open: row.o, high: row.h, low: row.l, close: row.c };
    if (seen.has(candle.time) && JSON.stringify(seen.get(candle.time)) !== JSON.stringify(candle)) {
      throw new Error('Conflicting GUM candles.');
    }
    seen.set(candle.time, candle);
  }
  return [...seen.values()].sort((a, b) => a.time - b.time);
}

export async function readMinutes(asset, from, to, signal) {
  const market = marketFor(asset);
  const query = new URLSearchParams({ from: String(from), to: String(to) });
  if (market.venue === 'JLP') {
    query.set('symbol', asset + 'USD');
    query.set('resolution', '1');
    const rows = decodeHistory(await readJson(JUPITER_ENDPOINTS.history + '?' + query, signal), {
      intervalSec: 60, nowMs: Date.now(),
    });
    return rows.filter(row => row.time >= from && row.time + 60 <= to && row.closed);
  }
  query.set('interval', '1m');
  const rows = parseGumMinutes(asset, await readJson(GUM + 'ohlcv/' + asset + '?' + query, signal));
  return rows.filter(row => row.time >= from && row.time + 60 <= to);
}

export async function readSnapshot(asset, signal) {
  const market = marketFor(asset);
  const now = Math.floor(Date.now() / 1000);
  if (market.venue === 'JLP') {
    const query = new URLSearchParams({ feedId: String(market.feed), fromMs: String((now - 11) * 1000), toMs: String((now - 1) * 1000) });
    const [pool, value] = await Promise.all([
      readJson(PERPS + 'pool-info?mint=' + market.mint, signal),
      readJson(PRICES + '?' + query, signal),
    ]);
    const points = parseJlpPrices(asset, value, now);
    return { points, mark: points.at(-1), long: jlpTerms(asset, pool, 1), short: jlpTerms(asset, pool, -1) };
  }
  const [catalog, funding] = await Promise.all([readJson(GUM + 'markets', signal), readJson(GUM + 'fundingRate/' + asset, signal)]);
  const { terms, mark } = gumTerms(asset, catalog, funding, now);
  return { points: [mark], mark, long: terms, short: terms };
}
