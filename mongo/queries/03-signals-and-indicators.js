// Signals and indicators — the two layers beneath the strategies.
//
//   mongosh solmargintrader mongo/queries/03-signals-and-indicators.js
//
// These are small reference collections (15 and 20 documents). They exist so a
// reader can answer "what does this rule actually compare?" without opening
// research/decide.py, and so the readouts in `decisions` can be joined to their
// definitions.

print("=== the 15 stateless one-bar rules ===");
db.signals
  .find({}, { _id: 1, rule: 1, tracks_strategy: 1 })
  .sort({ _id: 1 })
  .forEach((s) => {
    const tracked = s.tracks_strategy ? `  [mirrors ${s.tracks_strategy}]` : "";
    print(`  ${s._id.padEnd(20)} ${s.rule}${tracked}`);
  });

print("\n=== the three rules pinned to a strategy's own defaults ===");
// These take their periods from the registered strategy so the two cannot drift.
// A signal row claiming a 90-bar ROC while `ts_momentum` trades 60 shipped once.
printjson(
  db.signals
    .aggregate([
      { $match: { tracks_strategy: { $ne: null } } },
      {
        $lookup: {
          from: "strategies",
          localField: "tracks_strategy",
          foreignField: "registry_key",
          as: "strategy",
        },
      },
      { $unwind: "$strategy" },
      {
        $project: {
          _id: 1,
          rule: 1,
          strategy: "$strategy.registry_key",
          live_params: "$strategy.registry.params",
        },
      },
    ])
    .toArray(),
);

print("\n=== indicators that are reported, and what each covers ===");
db.indicators
  .find({ reported: true }, { _id: 1, sources: 1 })
  .sort({ _id: 1 })
  .forEach((i) => print(`  ${i._id.padEnd(26)} ${i.sources.join(", ")}`));

print("\n=== indicators deliberately NOT reported, with the reason ===");
// Helpers and series-returning variants have nothing to show for one bar. The
// list is explicit so a newly added indicator cannot be silently omitted.
db.indicators
  .find({ reported: false }, { _id: 1, skip_reason: 1 })
  .sort({ _id: 1 })
  .forEach((i) => print(`  ${i._id.padEnd(26)} ${i.skip_reason}`));

print("\n=== coverage check: every core.indicators function is accounted for ===");
printjson(
  db.indicators
    .aggregate([
      { $unwind: "$sources" },
      { $group: { _id: "$reported", functions: { $addToSet: "$sources" } } },
      { $project: { _id: 1, count: { $size: "$functions" }, functions: 1 } },
      { $sort: { _id: -1 } },
    ])
    .toArray(),
);
