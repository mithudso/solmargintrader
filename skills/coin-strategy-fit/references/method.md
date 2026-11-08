# Method and evidence contract

Version: 1.0.0

This skill, the direct script and the Bots tab call `soltui.coin_fit.rank_coins`.
The offline simulations call `backtester.core.coinfit.simulate`, which reuses
`gridsim.run_grid_backtest` and `dcasim.run_dca_backtest`. The grid economics
and live-extension parity contract are unchanged. Scheduled accumulation has a
separate prefunded next-open purchase schedule; it is not the DCA safety-order bot.

## Inputs

The cache contains `ASSET_1h.csv` or, if absent, `ASSET_1m.csv` with
`timestamp,open,high,low,close,volume`. Timestamps are integral UTC epoch seconds,
ascending and unique. All OHLCV must be finite and valid. Minute aggregation
requires sixty distinct, correctly aligned minutes per UTC hour. Missing hours
are never interpolated or bridged. Explicit missing directories fail closed.

Use `--data-dir` for a particular cache. Without it the application's default
cache resolver applies. Fetching is a separate explicit Data-tab or
`backtester.core.fetch` action; neither the ranking button nor simulation fetches.
`ALL` includes every cached symbol, retaining an insufficient-data row for any
that cannot cover the common period. Quotes other than USD are unsupported.

The common endpoint is the newest completed cached hour across the group, capped
at the current completed hour. A stale or shorter candidate does not pull all
other candidates backward: it must cover that same requested window or remain
insufficient. The default total period is 180 days, bounded to 7–730 days.
Dates in the result, not the wall clock, define the historical comparison.

## Quick versus audit

| Property | Quick | Audit |
| --- | --- | --- |
| Simulation | One older development slice, at most 90 days | Three chronological development folds, newest reserved holdout, continuous whole-period account |
| Reserved newest period | Last quarter of the analysis period, at most 30 days, excluded from score | Shown separately, at ordinary and doubled costs |
| Costs | Configured fee and adverse slippage, both entry and exit | Same base costs plus doubled fees and slippage for every scenario |
| Configuration | Fixed, captured current bot settings | Same frozen settings, capital, policy and data window |
| Output | Provisional score and suitability | Ten scenario runs, equity curves, fill ledgers, costs, inventory and robustness checks |

The audit's reset windows describe repeated starting conditions. The continuous
run separately measures capital/inventory carried across the whole period.
The audit is a fixed-configuration historical stress test, not parameter
optimization or proof that a complete coin-selection rule generalizes.
Repeatedly inspecting the reserved dates can overfit them. Previous research may
already have seen them. No statistical significance or universal edge is claimed.

All rows of one comparison use the same configuration, USD funded capital, costs
and UTC period. Different bots/modes are separate comparisons. A single audited
row does not replace its quick score or reorder the quick leaderboard.

## Accounting and execution

- Orders decided at a close cannot fill before a subsequent bar. Existing engines
  prevent a same-bar entry/exit from becoming a fabricated grid/basket profit.
- Fees and adverse slippage remain in the P&L path. Interactive screening refuses
  a configuration with zero combined modeled costs. Costs are assumptions, not
  historical book-depth measurements.
- Cash plus all coin inventory forms account equity. Return uses the full funded
  account. DCA funds every planned base/safety order, with stress-fee headroom by
  default. A `--capital` override remains in the denominator, including idle cash.
- Terminal inventory is forcibly liquidated with costs. The quantity before that
  liquidation and unfinished DCA deal count remain visible; the forced exit is
  not a completed regular cycle/deal.
- Drawdown and underwater duration use the full hourly closing-equity curve,
  before display downsampling. Unknown intrabar equity paths are not reconstructed.
- The buy-and-hold baseline uses the same funded capital, next observed open and
  terminal adverse costs. Cash is a 0% baseline; idle cash interest is zero.
- Scheduled DCA divides initially available funded cash into equal portions.
  This implementation does not model income arriving later or compute an IRR.

## Declared heuristic policy

Default policy version 1:

| Criterion | Default |
| --- | --- |
| Net return | Strictly positive after costs and terminal liquidation |
| Maximum absolute drawdown | 25% |
| Grid/basket completed cycles/deals | At least 3 |
| Grid rung spacing / modeled round-trip cost | At least 3 |
| DCA exit hit fraction, including unfinished/stopped attempts | At least 70% |
| Audit positive base windows | At least 60% |
| Audit newest holdout | Positive at both ordinary and doubled costs |
| Audit continuous account | Positive, with all scenario drawdowns within limit |

These are testable research choices, not empirically established best cutoffs.
Pass overrides with `--policy policy.json`. Keys are `max_drawdown`, `min_cycles`,
`min_spacing_cost_ratio`, `min_positive_window_fraction`, `min_exit_hit_rate`,
and `score_drawdown_penalty`. Fractions use 0–1. Unknown/non-finite keys or changed
policy versions are refused; the exact returned version can be replayed.

Score = `100 × (median base-window net return − penalty × absolute worst scenario drawdown)`.
Default penalty is 0.5. Quick has one score window; audit uses its reset base
windows and the worst risk across all scenarios. Score is a transparent heuristic,
not a probability, Sharpe estimate or calibrated expected return. Suitable rows
sort first, then descending score, then symbol for deterministic ties. Poor and
missing-data rows remain in the table. No allocation or bot setting is adopted.

## Twenty-two template fields

The original template is bundled in `assets/screening-fields.csv`. Every completed
row contains all twenty-two named metrics. Some have simulated values; some are
configured assumptions; current venue/depth, historical listing continuity and
other due diligence remain unknown. Not-applicable fields are explicit.
`GOOD_FIT` describes the historical-simulation component, never a claim that all
unknown due-diligence fields passed. This distinction must appear in explanations.

The price efficiency ratio, fixed-grid-band occupancy and downside escape are
descriptive. They do not establish a profitable live strategy. Recovery p95 is
among completed DCA deals; it is not an unbiased population recovery estimate.
Exit hit fraction separately retains stopped and unfinished deals.

For scheduled DCA, a positive historical return cannot supply an ownership thesis.
Optional `--context context.json` is coin-keyed:

```json
{
  "SOL": {
    "investment_thesis": {
      "approved": true,
      "reason": "Author's supported ownership rationale and invalidation conditions",
      "source": "URL or durable artifact reference"
    }
  }
}
```

This is supplied qualitative evidence, not verification by the script. Opposite
assessments produce different evidence/context identities. Invalid per-coin
context objects fail clearly rather than crashing. Missing thesis prevents a
positive scheduled-DCA fit verdict.

## Reproducibility and limits

JSON includes the fixed configuration, capital, costs, policy, common dates,
per-coin input hash, decision-bearing context identity, all fields and scenarios.
Audit requests from the Bots tab bind the selected quick row's input hash;
changed cached history requires reranking. CSV retains dates, costs, terminal
inventory, context scope and input hash. Markdown shows reasoning and costs/
inventory; use JSON for the detailed transaction ledger and equity points.

Bulk accounts are independent. Nominal ticker count does not establish
independent risk or enough cash for simultaneous safety orders. Historical
visible depth, point-in-time eligibility, missing/delisted assets, fundamentals,
future regimes and real executable fill calibration remain outside this test.
No live order or private-account access is present.

Research foundation:
https://github.com/mithudso/crypto-grid-dca-research/blob/main/report.md
