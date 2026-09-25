// Experiments: CPCV, sweeps, perturbations, geometry — and PBO.
//
//   mongosh solmargintrader mongo/queries/06-experiments-and-pbo.js
//
// Two collections:
//
//   experiments      one document per result file: kind, name, columns, and the
//                    JSON sidecar when it is a single object.
//   experiment_rows  one document per row. `section` is "result" for CSV rows and
//                    "summary" for rows that came from a LIST-shaped sidecar --
//                    `cpcv_pbo.json` holds one PBO per horizon, and burying those in
//                    a blob would hide the most queried number in the research set.
//
// **Read PBO before reading Sharpe.** Probability of Backtest Overfitting is the
// number that says whether a ranking generalises. `research/cpcv_sweep.interpret()`
// exists to catch two misreadings: a high positive-count with a high PBO ("lots of
// strategies work!"), and a low PBO with a low positive-count. High PBO means the
// in-sample winner is not predicting the out-of-sample winner — worse than random
// above ~0.5.

print("=== what experiments exist ===");
printjson(
  db.experiments
    .aggregate([
      {
        $group: {
          _id: "$kind",
          files: { $sum: 1 },
          rows: { $sum: "$row_count" },
          summary_rows: { $sum: "$summary_row_count" },
        },
      },
      { $sort: { rows: -1 } },
    ])
    .toArray(),
);

print("\n=== PBO by horizon: the headline honesty number ===");
// This query is the reason list-shaped sidecars became rows instead of a blob.
printjson(
  db.experiment_rows
    .aggregate([
      { $match: { section: "summary", pbo: { $ne: null }, horizon: { $ne: null } } },
      {
        $group: {
          _id: { horizon: "$horizon", experiment: "$experiment_id" },
          pbo: { $first: "$pbo" },
          splits: { $first: "$n_splits" },
          configs: { $first: "$n_configs" },
        },
      },
      { $sort: { pbo: -1 } },
    ])
    .toArray(),
);

print("\n=== PBO above the noise line (~0.5): worse than random ===");
// A ranking with PBO this high is anti-informative: the in-sample best tends to be
// the out-of-sample worst. Picking the top of such a list is a mistake.
printjson(
  db.experiment_rows
    .find(
      { section: "summary", pbo: { $gte: 0.5 } },
      { _id: 0, experiment_id: 1, horizon: 1, kind: 1, pbo: 1, n_configs: 1 },
    )
    .sort({ pbo: -1 })
    .toArray(),
);

print("\n=== geometry: PBO by block count, per horizon ===");
// Same measurement at several CPCV block counts. Stability across blocks is the
// point; a PBO that swings with the block count is not measuring the strategy.
printjson(
  db.experiment_rows
    .aggregate([
      { $match: { section: "summary", experiment_id: /^geometry/, blocks: { $ne: null } } },
      {
        $group: {
          _id: "$blocks",
          byExperiment: { $push: { experiment: "$experiment_id", pbo: "$pbo" } },
        },
      },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);

print("\n=== the sweep: best median Sharpe per strategy, with trade counts ===");
// `trades` matters as much as the Sharpe: a high Sharpe on 3 trades is noise, and
// the sweep's own filters exist for that reason.
printjson(
  db.experiment_rows
    .aggregate([
      { $match: { kind: "sweep", section: "result", median_sharpe: { $ne: null } } },
      {
        $group: {
          _id: "$strategy",
          bestSharpe: { $max: "$median_sharpe" },
          configs: { $sum: 1 },
          maxTrades: { $max: "$trades" },
        },
      },
      { $sort: { bestSharpe: -1 } },
      { $limit: 10 },
    ])
    .toArray(),
);

print("\n=== cross-asset: does a result on one coin transfer to another? ===");
printjson(
  db.experiment_rows
    .aggregate([
      { $match: { kind: "cross-asset", section: "result" } },
      {
        $group: {
          _id: "$experiment_id",
          rows: { $sum: 1 },
          strategies: { $addToSet: "$strategy" },
        },
      },
      { $project: { rows: 1, strategyCount: { $size: "$strategies" } } },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);

print("\n=== perturbation: how much does a small parameter change move the result? ===");
// A result that evaporates when a parameter moves one notch was a coincidence.
printjson(
  db.experiment_rows
    .aggregate([
      { $match: { kind: "perturbation", section: "result" } },
      { $group: { _id: "$experiment_id", rows: { $sum: 1 } } },
      { $sort: { _id: 1 } },
      { $limit: 8 },
    ])
    .toArray(),
);

print("\n=== every column available, per experiment kind ===");
// Useful before writing a query: the CSVs do not all carry the same fields.
printjson(
  db.experiments
    .aggregate([
      { $unwind: "$columns" },
      { $group: { _id: "$kind", columns: { $addToSet: "$columns" } } },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);
