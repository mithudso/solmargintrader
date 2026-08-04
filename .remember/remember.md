# Handoff — 2026-08-04

## Final state: MERGED to master

All work is on **master** (`75a68d1`). Verification on master: `verify_numbers.py` **exit 0**,
795 figures checked, **103 tests pass**, tree clean. **No remote — intentionally local.**

Master had diverged mid-session with three parallel commits (extension docs, repo bootstrap);
merged with merge commits, no conflicts, merged tree validated before each commit.

`research/results/` is now **tracked** (9 files, ~200KB). Those CSVs are the evidence for every
published figure, and `verify_numbers.py` checks the documents against them — ignoring them meant
a fresh checkout could not verify its own claims.

**A verifier bug worth knowing about:** `check_cpcv` used to return `True` when no CPCV results
were loaded, silently counting unverifiable figures as verified. Combined with the ignored
results directory, master reported success while actually failing 454 checks. Both fixed; there
is now a **preflight** that fails once with the regenerate commands rather than emitting hundreds
of per-figure mismatches. Also note: an unanchored `results/` gitignore pattern matches
`research/results/` at any depth — it is now `/results/`, anchored to the repo root.

## Where the work lives

Branch **`worktree-cpcv-and-longer-history`** in `.claude/worktrees/cpcv-and-longer-history`.
Four commits, not merged to the default branch:

| Commit | What |
|---|---|
| `84ea17d` | Initial commit: backtester, strategy research, pre-existing Jupiter extension |
| `feef1f9` | CPCV + PBO (`backtester/core/cpcv.py`), 23 tests |
| `3b74e1a` | CPCV becomes the primary ranking; single split retained as List 1b |
| `1a399d4` | ddo pass: stale counts, spec-drift note |

**103 tests pass. 495 document figures verified against results CSVs.**

## The headline result

Evaluation is now **CPCV** (8 blocks, k=2, 28 paths per configuration), not one 70/30 split.

- **PBO = 0.429 / 0.457 / 0.457** (short/medium/long). Calibrated against controls in the test
  suite: **pure noise → 0.500** (mean over 30 seeds), **genuinely ordered signal → 0.000**. SOL
  sits far closer to noise. Selecting by in-sample performance is barely better than random.
- **`buy_and_hold` ranks 1st at the medium horizon** (median path Sharpe +0.534). Nothing beat
  holding the asset.
- **All 16 short-horizon configurations have a negative median path Sharpe.**
- `zscore_20_-2`, which the single split ranked **1st**, falls to **8th** (52% of paths positive
  — a coin flip). `ma_crossover_12_48` goes 1st → 14th.
- **`obv_trend_60` is the only genuinely interesting row anywhere:** +0.774 median Sharpe, **81%
  of paths positive**, +44.6% median path return, 98 trades. First candidate for a
  parameter-perturbation check, precisely because it looks good.

## Three things worth remembering

1. **The single split was structurally doomed.** Its in-sample window ends on bar 1311 — the
   **highest close in the entire 1,875-bar series** (\$261.99). It separated the bull market from
   the bear leg to within one bar, so any long-biased strategy *had* to look great in-sample and
   terrible out-of-sample. I originally wrote "almost exactly on the top"; the fact-check showed
   that was an *under*statement.
2. **CPCV purge/embargo is degenerate here, and the code says so.** Classic CPCV purges training
   observations to protect *fitted* parameters. These strategies fit nothing. What CPCV actually
   buys is the path distribution and PBO. The real leakage vector for fixed-parameter strategies
   is **warm-up**, so `evaluate_block` warms from bars preceding each block and measures only the
   in-block region. Don't let anyone "restore" purge/embargo thinking it was missing.
3. **`zscore_20_-2` and `bb_reversion_20_2` are the same mechanism.** Identical inequality; only
   the stdev `ddof` differs (~2.6% threshold gap). They produce identical CPCV rows at the long
   horizon (+0.120, IQR 0.222) and near-identical elsewhere. Family labels are not a substitute
   for measuring pairwise signal correlation.

## Blocked, and why

**Longer daily history was not obtainable from this environment.** Coinbase's backward pagination
walked to **2021-06-17** and could make no further progress, consistent with that being its
SOL-USD listing date. Binance is geo-blocked; Kraken, OKX, Gate, KuCoin and Bybit hang on DNS.
CoinGecko's `days=max` OHLC is pro-gated and its free `market_chart` is close-only, which cannot
build OHLC bars for breakout/Keltner/stochastic/ATR strategies.

> **Know the limit of this evidence.** The 2021-06-17 floor is inferred from the pagination loop
> terminating, **not** from a direct empty response for an earlier window. I attempted that direct
> probe three times; all three were killed or timed out because outbound HTTP degraded to
> unreachable partway through the session. **Re-test before treating 2021-06-17 as a hard floor** —
> one completed request for `start=2020-04-01&end=2021-06-16` settles it either way.

CPCV absorbed the underlying need: the long horizon went from **4/16 evaluable to 16/16**,
because blocks reuse the whole series instead of one 563-bar tail.

## Open

- Branch is **unmerged** and there is **no remote**. Merge or open a PR when ready.
- `research/results/` and `data/` are gitignored; regenerate with `cpcv_sweep.py` / `sweep.py`
  and `backtester.core.fetch`.
- `/cdo` outstanding on the newer modules (indicators, signals, composite, cpcv, both sweeps).
- **Next highest-value work**, in order: (1) parameter-perturbation stability check on every
  ranked row — start with `obv_trend_60`; (2) measure pairwise signal correlation instead of
  trusting family labels; (3) re-run Lists 2 and 3 under CPCV (they are still single-split);
  (4) fetch a **peer universe** — unlocks cross-sectional momentum and cointegration, and is a
  bigger win than more SOL history; (5) deflated Sharpe accounting for the trials already run.

---

# Handoff — 2026-08-04 (second session: signals concept map + ladder grid)

Separate worktree from the CPCV work above; the two do not overlap in files.

## Where the work lives

Branch **`worktree-signals-concept-map`** in `.claude/worktrees/signals-concept-map`.
Five commits, **unmerged, no remote**, so nothing is pushed and the worktree can be
deleted with its session:

| Commit | What |
|---|---|
| `ba5b181` | `docs/trading-signals-concept-family.md` — concept map of trading signals → providers → jup.ag API/webhooks |
| `694ad1a` | `backtester/core/gridsim.py` ladder-grid simulator + extension order-envelope strictness |
| `0f117fa` | Docs for both, plus pagesource-derived evidence |
| `262bf0d` | Fix: sell slippage double-counted in grid realized P&L |
| `8a9c5f6` | Fix: cancelled orders booked as fills |

**122 Python tests, 110 JS tests, dry-run round trip closes +$0.0401, live
endpoints reachable.** All four `CLAUDE.md` gates pass.

## The one thing to know about the grid work

There are now **two different things called "grid"** and conflating them puts a
wrong number under the live strategy:

- `grid` / `GridLong` in `core/strategies/signals.py` — an **exposure staircase**
  off a rolling SMA anchor. A `Strategy`, filled at a bar boundary. Never captures
  a rung width, because it never has an order resting at a level.
- **the ladder grid** in `core/gridsim.py` — a ladder of **resting limit orders**
  with paired exits one rung above each lot. The extension's actual strategy.
  Own bar loop, own entry point (`python -m backtester.gridcli`).

`gridsim.py` is a port of `extension/src/core/grid.js` and the two must stay in
agreement — verified against the JS directly (699.1319 bps rung width on a 60–90/7
ladder, both implementations). This is now a `CLAUDE.md` non-negotiable.

## Three bugs, all found by review passes and none by tests

1. **Cancelled orders booked as fills** (Critical, pre-existing in the extension).
   `getFills()` reads orders/**history**, which holds every *terminal* order.
   With no execution gate a cancelled order took its price from `triggerPriceUsd`
   and its quantity from the intent's *planned* size, stored a fill for inventory
   the wallet never held, and marked the intent `filled`. Reproduced end to end
   before fixing; `ingestFills` now requires positive evidence of execution.
2. **Sell slippage double-counted** in the grid simulator — netted inside `gross`
   via the fill price, then subtracted again. Default slippage is 2 bps, so every
   realistic run understated P&L and corrupted win rate and profit factor.
   **All 30 tests passed with it live**, because every reconciliation test ran at
   zero cost. The lesson: an identity asserted only at zero cost is not asserted.
3. **Equity clamped where cash was refused.** `max(0.0, equity)` floored a
   carry-driven negative equity in the flattering direction while the cash guard
   raised on the same condition. Both paths now refuse.

## Still open

- **The Trigger order-list envelope remains unverified.** The strictness work made
  a wrong mapping *loud*, not correct — it still needs one real authenticated
  response to check field names against. Use
  `normaliseOrders(body, { strict: false })` to inspect one by hand.
- **No live order has ever been placed.** Unchanged.
- `docs/trading-signals-concept-family.md` carries `UNVERIFIED` tags on the Perps
  program ID, the Portfolio API host, the Prediction P&L path shape, and whether
  the SDK/API licence permits programmatic use. A background agent was verifying
  these and had not reported by session end — re-run that check before relying on
  any of them.
- **Known duplication, deliberately left:** `gridcli.py` repeats ~12 parser args
  and the data-loading block from `cli.py`. Extracting a shared helper would edit
  `cli.py`, outside this change's scope; drift risk is real but was judged smaller
  than the regression risk.
- **Skipped on advice:** a signal-ingestion webhook receiver (widens the
  money-touching surface with no real signal source to test against) and a perps
  asset/decimals registry (the executable venue is spot Trigger, so it feeds
  nothing today — the extracted data went into the concept map as evidence).

## Useful artifacts

- `pagesource` (untracked, repo root) is the rendered perps page and contains a
  ~50 KB SSR hydration payload: `perpsSettings: {v2AsDefault: true}`, the Tokens v2
  `/search` record shape (the mint is `id`, **not** `address`), and ~100 perps
  markets with decimals. All recorded in the concept map's §10.
- `jup.ag/` mirror is HTML only — no JS bundles — so it proves which pages exist,
  never what an endpoint returns.
