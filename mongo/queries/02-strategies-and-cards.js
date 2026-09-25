// Strategies and their cards.
//
//   mongosh solmargintrader mongo/queries/02-strategies-and-cards.js
//
// One document per strategy card (45). The card's own vocabulary is preserved
// rather than flattened into a boolean:
//
//   registry_key  a string for the 25 registered `Strategy` implementations,
//                 null otherwise. NOT the same as "unimplemented" -- the ladder
//                 grid is implemented and has no key because it is not a Strategy.
//   status        measured | implemented | spec-only
//   runner        backtester.cli | backtester.gridcli | backtester.paircli | null
//   registry      live code facts (params, warmup, class) for the registered 25
//
// Indexes: status_family, family, registry_key_unique (partial, string only),
// feasibility (data_available + success_likelihood).

print("=== the inventory: status by kind ===");
printjson(
  db.strategies
    .aggregate([
      { $group: { _id: { status: "$status", kind: "$kind" }, n: { $sum: 1 } } },
      { $sort: { n: -1 } },
    ])
    .toArray(),
);

print("\n=== the 25 that actually run, by family ===");
// The partial index on registry_key serves this filter: it indexes only the string
// values, so the 20 nulls cost nothing.
printjson(
  db.strategies
    .aggregate([
      { $match: { registry_key: { $type: "string" } } },
      {
        $group: {
          _id: "$registry.family",
          count: { $sum: 1 },
          keys: { $push: "$registry_key" },
        },
      },
      { $sort: { _id: 1 } },
    ])
    .toArray(),
);

print("\n=== warm-up cost: which strategies need the most history ===");
// Straight from the live constructor, not the card's prose, so it cannot drift.
printjson(
  db.strategies
    .find(
      { "registry.warmup_bars": { $gt: 0 } },
      { _id: 1, "registry.warmup_bars": 1, "registry.params": 1 },
    )
    .sort({ "registry.warmup_bars": -1 })
    .limit(8)
    .toArray(),
);

print("\n=== what could be built next: spec-only, but the data exists ===");
// The feasibility index (data_available, success_likelihood) serves this directly.
// This is the shortlist `implementable_today()` computes in code.
printjson(
  db.strategies
    .find(
      { status: "spec-only", data_available: true },
      { _id: 1, name: 1, family: 1, success_likelihood: 1, summary: 1 },
    )
    .sort({ success_likelihood: 1 })
    .toArray(),
);

print("\n=== blocked on data: what each spec-only card still needs ===");
printjson(
  db.strategies
    .aggregate([
      { $match: { status: "spec-only", data_available: false } },
      { $unwind: "$data_required" },
      { $group: { _id: "$data_required", cards: { $push: "$_id" }, n: { $sum: 1 } } },
      { $sort: { n: -1 } },
    ])
    .toArray(),
);

print("\n=== one card in full, prose included ===");
// The body is the card's own reasoning and limitations. Numbers in a card are
// checked against the code by tests; the prose is not, so read it as argument.
const card = db.strategies.findOne({ registry_key: "breakout" });
print(`${card._id}: ${card.name}  [${card.status}, ${card.family}]`);
print(`  registry: ${JSON.stringify(card.registry)}`);
print(`  presets:  ${JSON.stringify(card.presets)}`);
print(`  source:   ${card.source_path}`);
print("");
print(card.body.split("\n").slice(0, 12).join("\n"));

print("\n=== every card's provenance, so a claim can be traced to a file ===");
printjson(
  db.strategies
    .aggregate([
      { $group: { _id: "$source_sha256", cards: { $sum: 1 } } },
      { $count: "distinct_source_files" },
    ])
    .toArray(),
);
