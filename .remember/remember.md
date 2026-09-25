
---

## Auto re-centring in `planGrid` — shipped opt-in, and measured to do almost nothing

Commits `724bedf` + `a90455a`. `recentreDecision()` moves the ladder to 0.85x–1.15x of price
(`tools/dryrun.js`'s convention, deliberately not a second one). **Off by default.**

**The refusals are the feature.** It may only act when nothing rests and no lot is open:

- an open lot's exit is recomputed from the *current* levels, so re-centring down while holding
  inventory can place that lot's sell **below its own entry** — the zero-spread bug, except it now
  realizes a loss. The guard **counts** lots rather than summing `baseQty`, so a NaN cannot read as
  flat (`pnl.js` already drops fully-matched lots, so counting is safe).
- `tick()` has **no cancel step** (`cancelOrder` is manual only), so a moved ladder would strand
  real orders at abandoned levels.

### Three traps paid for here — do not re-learn

1. **Persist moved bounds BEFORE placing anything.** `planGrid` is pure, so an uncommitted
   re-centre vanishes: the next tick sees the new orders resting, refuses to re-centre, falls back
   to the **old** bounds and places a **second ladder** at the levels just abandoned — capital on
   two ladders at once. Reproduced with a failing test first, then fixed in `engine.js`.
2. **`stubVenue` returns `[]` from `getOpenOrders`, so nothing it places ever stays resting** — it
   hides every bug that only appears on the *second* tick. Use `echoVenue` (`test/core.test.js`) or
   `recordingVenue` (`tools/measure-recentre.js`) for anything multi-tick.
3. **`setConfig`'s `--patch` hatch makes a new config field settable but undiscoverable.** Without a
   named param no surface shows it, and since every test builds config via `ConfigStore` directly, a
   green suite is consistent with a flag nobody can reach. Test through `runCommand`.

### Do not quote +7.5% for this feature

From `extension/`: `node tools/measure-recentre.js --csv ../data/SOL_1d.csv` drives the real
`tick()` bar by bar. (`data/` is a gitignored fetch cache that exists only in the main checkout, so
that relative path does not resolve from inside a worktree — pass an absolute path there.)

| | ladder moved | bars outside ladder |
| --- | --- | --- |
| `autoRecentre=false` | 0x | 1637/1875 (**87.3%**) |
| `autoRecentre=true` | **1x**, on bar 1 | 1745/1875 (**93.1%**) |

The **+7.5% median** came from a simulator moving the ladder *unconditionally* every block. The
shipped gate fires **once in 1,875 bars** and on this path made placement **worse** — one
inception-time move locked the ladder onto 2021's $39.25. Corrected in `extension/README.md` and
`backtester/strategy_cards/ladder_grid.md`, which both previously called re-centring "what made it
profitable". Value is *not* return: a grid armed today starts near today's price. At $74.03 the
stock 60–90 band already contains price, so it returns `price-inside-ladder` and does nothing.

Making the ladder actually **track** the market needs a cancel path in `tick()` — a change to the
order lifecycle, deliberately not attempted. **No live order has ever been placed.**

### Handoff-file hazard, learned the hard way

`.remember/remember.md` is **tracked and cumulative across sessions**. Writing it with a whole-file
Write from a worktree clobbers every prior section in the main checkout's working tree. Append a new
`---` section instead; recover a clobber with `git restore .remember/remember.md`.

---

# The doc-drift gate, and how to keep it green — 2026-08-05

`scripts/check_docs.py` now fails the build when the docs disagree with the repo. It
exists because four files claimed 250 backtester tests for several commits while the
suite had grown past 450, and nothing caught it.

What it checks:

- **Every `N tests` claim** in `README.md`, `CLAUDE.md`, `docs/TESTING.md` and
  `docs/ARCHITECTURE.md`, against the suites. Counts come from `git ls-tree -r HEAD`,
  so **staged-but-uncommitted tests do not fail anyone else's checkout** — the failure
  lands on the commit that adds them, which is where it belongs.
- The `N tests total` figure against the sum. A hand-summed total is exactly the number
  that goes stale while the per-suite figures beside it stay right.
- Every path in `docs/high_signal_file_index.json` and every backtick-quoted path in
  `docs/codebase-overview.md`.
- That the overview has a section per component. Adding a component means adding it to
  the tuple in `check_components_covered()` **and** giving it an overview section.

Two traps in the checker itself, both paid for:

- The count regex needs `N tests` **adjacent**. `# 20 mongo tests` was silently
  unverifiable; write `# 20 tests` and let the line's other words name the suite.
- `docs/high_signal_file_index.json` is **generated** by `scripts/build_doc_index.py`
  from the overview's tables. Do not hand-edit it. Line counts come from `HEAD`, and a
  path is excluded only when it is ignored *and* untracked — both so the same commit
  produces a byte-identical file in every clone.

So after adding tests: update the count where the docs quote it, run
`python3 scripts/build_doc_index.py`, then `python3 scripts/check_docs.py`.

New in this session: `mongo/` is a fifth component (see `mongo/README.md`) and is
covered by the gate like the rest.
