// Coins and price history.
//
//   mongosh solmargintrader mongo/queries/01-coins-and-bars.js
//
// `bars` is a native time series collection: `ts` is the time field and `series`
// the metaField, so every query below should filter on `series.*` and a time range.
// MongoDB creates the meta+time index itself; there are no user indexes to add.

print("=== which series are loaded, and how stale is each ===");
// Group by the metaField. `$max: "$ts"` on a time series collection is the cheap
// direction -- the bucket catalogue already knows each bucket's time range.
printjson(
  db.bars
    .aggregate([
      {
        $group: {
          _id: { asset: "$series.asset", interval: "$series.interval" },
          bars: { $sum: 1 },
          first: { $min: "$ts" },
          last: { $max: "$ts" },
          checksum: { $first: "$series.frame_checksum" },
        },
      },
      { $sort: { "_id.asset": 1, "_id.interval": 1 } },
    ])
    .toArray(),
);

print("\n=== the last 5 SOL daily bars ===");
// Filtering the metaField first, then sorting on time, is the access pattern time
// series collections are built for.
printjson(
  db.bars
    .find(
      { "series.asset": "SOL", "series.interval": "1d" },
      { _id: 0, ts: 1, open: 1, high: 1, low: 1, close: 1, volume: 1 },
    )
    .sort({ ts: -1 })
    .limit(5)
    .toArray(),
);

print("\n=== 30-day return and realised range, per coin ===");
// A $group over a time-bounded $match is the shape MongoDB 8's block processing
// accelerates, so this stays fast as history grows.
const cutoff = new Date(Date.now() - 30 * 24 * 3600 * 1000);
printjson(
  db.bars
    .aggregate([
      { $match: { "series.interval": "1d", ts: { $gte: cutoff } } },
      { $sort: { ts: 1 } },
      {
        $group: {
          _id: "$series.asset",
          bars: { $sum: 1 },
          firstClose: { $first: "$close" },
          lastClose: { $last: "$close" },
          lowest: { $min: "$low" },
          highest: { $max: "$high" },
        },
      },
      {
        $addFields: {
          returnPct: {
            $multiply: [{ $subtract: [{ $divide: ["$lastClose", "$firstClose"] }, 1] }, 100],
          },
          rangePct: {
            $multiply: [{ $divide: [{ $subtract: ["$highest", "$lowest"] }, "$lowest" ] }, 100],
          },
        },
      },
      { $sort: { returnPct: -1 } },
    ])
    .toArray(),
);

print("\n=== biggest single-day drops, all coins ===");
// $setWindowFields is how you reach the previous bar without pulling the series
// into the client. Partition by the series, order by time.
printjson(
  db.bars
    .aggregate([
      { $match: { "series.interval": "1d" } },
      {
        $setWindowFields: {
          partitionBy: "$series.asset",
          sortBy: { ts: 1 },
          output: { prevClose: { $shift: { output: "$close", by: -1, default: null } } },
        },
      },
      { $match: { prevClose: { $ne: null } } },
      {
        $addFields: {
          changePct: {
            $multiply: [{ $subtract: [{ $divide: ["$close", "$prevClose"] }, 1] }, 100],
          },
        },
      },
      { $sort: { changePct: 1 } },
      { $limit: 5 },
      { $project: { _id: 0, asset: "$series.asset", ts: 1, prevClose: 1, close: 1, changePct: 1 } },
    ])
    .toArray(),
);

print("\n=== the JLP spot snapshot, which is NOT a bar series ===");
// Deliberately a separate collection: different columns, no OHLCV, irregular.
// `research/decide.py` refuses to read it as bars; see docs/known-issues.md.
printjson(db.spot_prices.find({}, { _id: 0, loaded_at: 0 }).toArray());
