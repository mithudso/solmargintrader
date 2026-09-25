// Provenance, freshness and store health — run this before trusting anything else.
//
//   mongosh solmargintrader mongo/queries/08-provenance-and-health.js
//
// Every document carries `source_path`, `source_sha256` and `loaded_at`. That is
// not bookkeeping: it is what lets a number here be traced to a file, and a file to
// the run that produced it. A figure with no provenance is not a figure.
//
// Two questions this answers that nothing else does:
//   1. Is the store stale relative to the files on disk?
//   2. Do the test counts recorded here match the docs?

print("=== document counts, per collection ===");
const names = [
  "bars", "spot_prices", "equity_points", "strategies", "signals", "indicators",
  "decisions", "backtest_runs", "trades", "experiments", "experiment_rows",
  "documents", "test_results",
];
let total = 0;
names.forEach((n) => {
  const count = db[n].countDocuments();
  total += count;
  print(`  ${n.padEnd(18)} ${String(count).padStart(8)}`);
});
print(`  ${"TOTAL".padEnd(18)} ${String(total).padStart(8)}`);

print("\n=== when was the store loaded, and from how many source files ===");
printjson(
  db.strategies
    .aggregate([
      {
        $group: {
          _id: null,
          loadedAt: { $max: "$loaded_at" },
          distinctSources: { $addToSet: "$source_path" },
        },
      },
      { $project: { _id: 0, loadedAt: 1, sourceFiles: { $size: "$distinctSources" } } },
    ])
    .toArray(),
);

print("\n=== bar series: file checksum vs frame checksum ===");
// Two different checksums on purpose. `source_sha256` is the bytes on disk;
// `frame_checksum` is what `backtester.core.data.checksum_frame` computes over the
// validated frame, which is the identity a backtest or readout prints. Matching a
// number in a report to a series here means matching the frame checksum.
printjson(
  db.bars
    .aggregate([
      {
        $group: {
          _id: { asset: "$series.asset", interval: "$series.interval" },
          file: { $first: { $substrCP: ["$series.source_sha256", 0, 12] } },
          frame: { $first: { $substrCP: ["$series.frame_checksum", 0, 12] } },
          path: { $first: "$series.source_path" },
        },
      },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);

print("\n=== readout staleness: how old is each decision bar ===");
// The readout records the bar's age in bars of its own interval. 40 hourly bars
// stale and 1.7 daily bars stale are the same wall-clock gap and not the same
// problem.
printjson(
  db.decisions
    .find(
      {},
      { _id: 0, asset: 1, interval: 1, "decision_bar.age_bars": 1, "decision_bar.stale": 1 },
    )
    .sort({ "decision_bar.stale": -1, asset: 1 })
    .toArray(),
);

print("\n=== recorded test results, and the commit they came from ===");
// `ok` is observed from a real run, never assumed. Compare `count` against the
// figures in README.md / docs/TESTING.md; `scripts/check_docs.py` enforces those.
printjson(
  db.test_results
    .find({}, { _id: 0, suite: 1, count: 1, ok: 1, git_sha: 1, recorded_at: 1, command: 1 })
    .sort({ suite: 1 })
    .toArray(),
);

print("\n=== any non-finite number that slipped through? ===");
// The loader converts NaN and infinity to null, because BSON has no NaN worth
// comparing against and a query would silently mis-rank around one. `$count`
// emits nothing when nothing matches, so a healthy store prints `[]` here.
printjson(
  db.experiment_rows
    .aggregate([
      {
        $match: {
          $expr: {
            $anyElementTrue: {
              $map: {
                input: { $objectToArray: "$$ROOT" },
                as: "field",
                in: {
                  $and: [
                    { $eq: [{ $type: "$$field.v" }, "double"] },
                    { $ne: ["$$field.v", "$$field.v"] }, // NaN != NaN
                  ],
                },
              },
            },
          },
        },
      },
      { $count: "nonFiniteRows" },
    ])
    .toArray(),
);

print("\n=== index inventory: what each collection is actually indexed on ===");
names.forEach((n) => {
  const idx = db[n]
    .getIndexes()
    .map((i) => `${i.name}(${Object.keys(i.key).join(",")})${i.unique ? " UNIQUE" : ""}`);
  print(`  ${n.padEnd(18)} ${idx.join("  ")}`);
});
