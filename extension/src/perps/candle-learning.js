/** Prospective close-to-close models for native Perps candles. Prices and marks
 * identify the feed; the model does not observe orders or simulated outcomes. */
import { ORACLE, makeFeatures, oracleMetrics, transitionOracle } from '../1000x/oracle-model.js';
import { TIMEFRAMES } from '../1000x/timeframes.js';
import { MARKETS } from './model.js';

const EPOCH_LIMIT = 253402300799;
export const finiteEpoch = value => Number.isFinite(value) && value >= 0 && value <= EPOCH_LIMIT;

export function paperMarketKey(venue, asset) {
  if (!Object.hasOwn(MARKETS, asset) || MARKETS[asset].venue !== venue) throw new Error('Invalid paper market.');
  return `${venue}:${asset}:paper`;
}

export function requirePaperMarket(key) {
  if (typeof key !== 'string') throw new Error('Invalid paper market key.');
  const [venue, asset] = key.split(':');
  if (paperMarketKey(venue, asset) !== key) throw new Error('Invalid paper market key.');
  return { asset, market: MARKETS[asset] };
}

/** The Perps adapter validates venue rows. At this clock boundary, use only
 * a contiguous suffix of fully closed native minutes when constructing input. */
function nativeMinuteTail(rows, cutoff) {
  if (!Array.isArray(rows)) return [];
  const tail = [];
  let expected = cutoff - 60;
  for (let i = rows.length - 1; i >= 0; i--) {
    const row = rows[i];
    if (!Number.isSafeInteger(row?.time)) return [];
    if (row.time >= cutoff) continue;
    if (row.time !== expected || row.closed === false || row.partial === true) break;
    tail.push({ ...row, closed: true });
    if (row.gapBefore) break;
    expected -= 60;
  }
  return tail.reverse();
}

function safeFeatures(rows, cutoff) {
  if (rows.length < 78) return null;
  try { return makeFeatures(rows, cutoff); }
  catch { return null; }
}

export function causalEntryFeatures(rows, epochSec) {
  if (!finiteEpoch(epochSec)) return null;
  const cutoff = Math.floor(epochSec / 60) * 60;
  return safeFeatures(nativeMinuteTail(rows, cutoff), cutoff);
}

export function prepareCandleModel(marketKey, rows, mark, nowMs) {
  const { asset, market } = requirePaperMarket(marketKey);
  if (!Number.isSafeInteger(nowMs) || !finiteEpoch(nowMs / 1000)) throw new Error('Invalid paper candle clock.');
  const cutoff = Math.floor(nowMs / 60000) * 60;
  const minutes = nativeMinuteTail(rows, cutoff);
  const age = nowMs / 1000 - mark?.time;
  const fresh = finiteEpoch(mark?.time) && Number.isFinite(mark.price) && mark.price > 0 && age >= -2 && age <= 20;
  const features = fresh ? safeFeatures(minutes, cutoff) : null;
  const eligible = features !== null;
  const status = !fresh ? 'waiting-for-fresh-mark' : !eligible ? 'waiting-for-complete-history' : 'ready';
  const feed = market.venue === 'GUM' ? 'gum-trade-ohlc:gum-mark' : `jlp-pyth-ohlc:pyth-mark:${market.feed}`;
  // Scope and cadence are explicit. These states cannot load under the 1000x
  // stream identity, even when both models see the same underlying asset.
  const source = `perps-native-1m-v1:${marketKey}:${feed}:mark-age20-v1`;
  const partitions = TIMEFRAMES.map(({ seconds: horizon }) => ({
    key: JSON.stringify([ORACLE.schema, ORACLE.model, ORACLE.features, ORACLE.target, horizon, asset, source]),
    market: asset, source, horizon,
  }));
  return { rows: minutes, cutoff, nowMs, features, eligible, status, partitions };
}

export function advanceCandlePartition(previous, prepared, partition) {
  if (!previous && !prepared.eligible) {
    return { changed: false, summary: { seconds: partition.horizon, status: prepared.status, issue: null,
      samples: 0, accuracy: null, brier: null, expired: 0 } };
  }
  const next = transitionOracle(previous, { ...prepared, ...partition });
  const { state } = next;
  const current = prepared.eligible ? state.pending.find(f => f.cutoff === prepared.cutoff) : null;
  const issue = current ? { cutoff: current.cutoff, target: current.target, probability: current.servedP,
    mode: current.mode, reference: current.reference } : null;
  const { n, accuracy, brier } = oracleMetrics(state).cumulative.served;
  return { changed: next.changed, state,
    summary: { seconds: partition.horizon, issue, samples: n, accuracy, brier, expired: state.expired,
      status: prepared.eligible ? next.feedback.status : prepared.status } };
}
