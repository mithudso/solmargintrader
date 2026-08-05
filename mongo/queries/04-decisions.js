// Per-bar readouts: what every rule said about the last bar of a series.
//
//   mongosh solmargintrader mongo/queries/04-decisions.js
//
// Each document is `research.decide.build_report()` output verbatim, plus
// provenance. That is deliberate -- re-deriving a Mongo-specific shape would let
// the store and the readout disagree about what a strategy said.
//
// Read the header fields before the verdicts. A readout whose decision bar is 40
// bars old is not a current answer, and `decision_bar.stale` says so.
//
// NOT INVESTMENT ADVICE: these are mechanical rule readings on cached history.
// They are heavily correlated; counting agreement is not evidence.

print("=== the readouts, and whether each is stale ===");
printjson(
  db.decisions
    .find(
      {},
      {
        _id: 0,
        asset: 1,
        interval: 1,
        bars: 1,
        "decision_bar.utc": 1,
        "decision_bar.close": 1,
        "decision_bar.age_bars": 1,
        "decision_bar.stale": 1,
      },
    )
    .sort({ asset: 1, interval: 1 })
    .toArray(),
);

print("\n=== SOL 1d: what each strategy wants ===");
const sol = db.decisions.findOne({ asset: "SOL", interval: "1d" });
print(`  bar ${sol.decision_bar.utc}  close ${sol.decision_bar.close}`);
print(`  executes at: ${sol.execution.applies_to}`);
sol.strategies.forEach((s) =>
  print(`  ${s.key.padEnd(18)} ${s.family.padEnd(22)} ${s.action.padEnd(10)} ${s.detail}`),
);

print("\n=== the informative part: which families disagree, per coin ===");
// A tally across all 25 would read as a vote; these rules are not independent.
// Disagreement BETWEEN families is what carries information.
printjson(
  db.decisions
    .aggregate([
      { $match: { interval: "1d" } },
      { $unwind: "$strategies" },
      {
        $group: {
          _id: { asset: "$asset", family: "$strategies.family" },
          actions: { $addToSet: "$strategies.action" },
        },
      },
      { $match: { "actions.1": { $exists: true } } }, // more than one action
      { $sort: { "_id.asset": 1, "_id.family": 1 } },
    ])
    .toArray(),
);

print("\n=== any coin where a strategy currently wants to be long ===");
// The by_action index (strategies.key, strategies.action) serves this.
printjson(
  db.decisions
    .aggregate([
      { $unwind: "$strategies" },
      { $match: { "strategies.action": { $in: ["BUY", "HOLD-LONG"] } } },
      {
        $group: {
          _id: "$strategies.key",
          coins: { $push: { asset: "$asset", interval: "$interval", action: "$strategies.action" } },
        },
      },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);

print("\n=== strategies that cannot answer yet, and why ===");
// NO-DATA is a refusal, not a verdict: the strategy has not warmed up. Reporting
// HOLD for one of these would be inventing an answer.
printjson(
  db.decisions
    .aggregate([
      { $unwind: "$strategies" },
      { $match: { "strategies.action": "NO-DATA" } },
      {
        $group: {
          _id: { asset: "$asset", interval: "$interval" },
          blocked: { $push: { key: "$strategies.key", note: "$strategies.note" } },
        },
      },
    ])
    .toArray(),
);

print("\n=== signal readings across coins: agreement and disagreement ===");
printjson(
  db.decisions
    .aggregate([
      { $match: { interval: "1d" } },
      { $unwind: "$signals" },
      {
        $group: {
          _id: "$signals.key",
          bullish: { $sum: { $cond: [{ $eq: ["$signals.reading", "bullish"] }, 1, 0] } },
          bearish: { $sum: { $cond: [{ $eq: ["$signals.reading", "bearish"] }, 1, 0] } },
          neutral: { $sum: { $cond: [{ $eq: ["$signals.reading", "neutral"] }, 1, 0] } },
          unavailable: { $sum: { $cond: [{ $eq: ["$signals.reading", "n/a"] }, 1, 0] } },
        },
      },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);

print("\n=== indicators with no directional reading, which is most of them ===");
// `no-direction` is not `neutral`. ATR does not become bullish; it is a magnitude.
printjson(
  db.decisions
    .aggregate([
      { $match: { asset: "SOL", interval: "1d" } },
      { $unwind: "$indicators" },
      { $group: { _id: "$indicators.reading", indicators: { $push: "$indicators.key" } } },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);
