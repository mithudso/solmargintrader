// Backtest runs: manifests, per-strategy metrics, equity curves, fills.
//
//   mongosh solmargintrader mongo/queries/05-backtests.js
//
// Three collections, split by cardinality rather than by topic:
//
//   backtest_runs   one document per run. The manifest is embedded because it is
//                   always read with the run, and the per-strategy metrics table is
//                   bounded by the strategies that ran.
//   equity_points   a time series collection. A curve is ~1,875 points per
//                   strategy; embedding four of them would be the unbounded-array
//                   antipattern and would make the curve unaggregatable.
//   trades          one document per fill.
//
// The manifest is what makes a number reproducible: costs, fill delay, seed,
// data checksum, library versions. Read it before trusting a Sharpe.

print("=== the runs on record ===");
printjson(
  db.backtest_runs
    .find({}, { _id: 1, asset: 1, interval: 1, mode: 1, "manifest.start": 1, "manifest.end": 1 })
    .toArray(),
);

print("\n=== what reproduces the run: the cost and execution settings ===");
const run = db.backtest_runs.findOne();
printjson({
  run: run._id,
  bars: run.manifest.bar_count,
  fill_delay: run.manifest.fill_delay,
  leverage: run.manifest.leverage,
  costs: run.manifest.costs,
  data_checksum: run.manifest.data_checksum,
  periods_per_year: run.manifest.periods_per_year,
  sharpe_convention: run.manifest.sharpe_convention,
});

print("\n=== per-strategy results, buy-and-hold included on purpose ===");
// A strategy that cannot beat buy-and-hold has not earned anything, so the
// baseline stays in the table rather than being filtered out of the comparison.
printjson(run.results);

print("\n=== equity: start, end and worst drawdown per curve ===");
// $setWindowFields with an unbounded preceding window gives the running peak,
// which is what a drawdown is measured against.
printjson(
  db.equity_points
    .aggregate([
      { $sort: { ts: 1 } },
      {
        $setWindowFields: {
          partitionBy: "$curve.strategy",
          sortBy: { ts: 1 },
          output: {
            peak: { $max: "$equity", window: { documents: ["unbounded", "current"] } },
          },
        },
      },
      { $addFields: { drawdown: { $divide: [{ $subtract: ["$equity", "$peak"] }, "$peak"] } } },
      {
        $group: {
          _id: "$curve.strategy",
          points: { $sum: 1 },
          first: { $first: "$equity" },
          last: { $last: "$equity" },
          maxDrawdownPct: { $min: { $multiply: ["$drawdown", 100] } },
        },
      },
      {
        $addFields: {
          totalReturnPct: {
            $multiply: [{ $subtract: [{ $divide: ["$last", "$first"] }, 1] }, 100],
          },
        },
      },
      { $sort: { totalReturnPct: -1 } },
    ])
    .toArray(),
);

print("\n=== fills per strategy, and what they cost ===");
printjson(
  db.trades
    .aggregate([
      {
        $group: {
          _id: "$strategy",
          fills: { $sum: 1 },
          fees: { $sum: "$fee" },
          slippage: { $sum: "$slippage" },
          realised: { $sum: "$realized_pnl" },
        },
      },
      { $sort: { fills: -1 } },
    ])
    .toArray(),
);

print("\n=== why a fill happened: the reason field ===");
// `liquidation` and `final` are not signals. A run with liquidations is telling
// you something the Sharpe alone will not.
printjson(
  db.trades
    .aggregate([
      { $group: { _id: { strategy: "$strategy", reason: "$reason" }, n: { $sum: 1 } } },
      { $sort: { n: -1 } },
    ])
    .toArray(),
);

print("\n=== the first and last few fills of one strategy ===");
printjson(
  db.trades
    .find({ strategy: { $exists: true } }, { _id: 0, source_path: 0, source_sha256: 0, loaded_at: 0 })
    .sort({ ts: 1 })
    .limit(3)
    .toArray(),
);
