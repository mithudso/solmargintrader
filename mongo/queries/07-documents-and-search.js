// Reference prose: coin intelligence, research write-ups, component docs.
//
//   mongosh solmargintrader mongo/queries/07-documents-and-search.js
//
// One document per markdown file, with a full-text index on title and body. A
// server allows one text index per collection, and this is it.
//
// Caveat worth keeping in mind: prose in a strategy card is *argument*, not
// checked fact. Tests verify the numbers in a card's frontmatter against the code
// in both directions; nothing verifies the reasoning. Read accordingly.

print("=== what is loaded, by kind ===");
printjson(
  db.documents
    .aggregate([
      { $group: { _id: "$kind", docs: { $sum: 1 }, words: { $sum: "$words" } } },
      { $sort: { words: -1 } },
    ])
    .toArray(),
);

print("\n=== the coin intelligence spokes ===");
db.documents
  .find({ kind: "coin-intelligence" }, { _id: 0, slug: 1, title: 1, words: 1 })
  .sort({ slug: 1 })
  .forEach((d) => print(`  ${d.slug.padEnd(22)} ${String(d.words).padStart(6)} words  ${d.title}`));

print("\n=== full-text search: liquidity and float ===");
// $text uses the `fulltext` index. textScore is relevance, not importance.
printjson(
  db.documents
    .find(
      { $text: { $search: "float unlock concentration" } },
      { score: { $meta: "textScore" }, _id: 1, kind: 1, title: 1 },
    )
    .sort({ score: { $meta: "textScore" } })
    .limit(6)
    .toArray(),
);

print("\n=== search for a caveat: where is overfitting discussed? ===");
printjson(
  db.documents
    .find(
      { $text: { $search: "overfitting PBO survivorship" } },
      { score: { $meta: "textScore" }, _id: 1, title: 1 },
    )
    .sort({ score: { $meta: "textScore" } })
    .limit(6)
    .toArray(),
);

print("\n=== pull one document's text, first 15 lines ===");
const doc = db.documents.findOne({ kind: "coin-intelligence", slug: /^sol/ });
if (doc) {
  print(`  ${doc._id}  (${doc.source_path})`);
  print(doc.body.split("\n").slice(0, 15).join("\n"));
}

print("\n=== which coins have a spoke but no cached bars, and vice versa ===");
// A gap in either direction is worth knowing: a coin with intelligence but no data
// cannot be backtested, and a coin with data but no write-up has not been thought
// about.
const spokes = db.documents
  .find({ kind: "coin-intelligence" }, { slug: 1 })
  .toArray()
  .map((d) => d.slug.split("-")[0].toUpperCase());
const withBars = db.bars.distinct("series.asset");
printjson({
  spokes: spokes.sort(),
  cachedBars: withBars.sort(),
  spokeButNoBars: spokes.filter((s) => !withBars.includes(s)).sort(),
  barsButNoSpoke: withBars.filter((a) => !spokes.includes(a)).sort(),
});
