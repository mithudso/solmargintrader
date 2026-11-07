# Leverage tiers: low, medium, high margin on SOL

Simulation only. Reproduce with `python3 -m research.leverage_tiers --asset SOL --interval 1d`
(about 6 seconds). Raw rows: `research/results/leverage_tiers_sol_1d_summary.csv`,
`research/results/leverage_tiers_sol_1d_per_strategy.csv`, `research/results/leverage_tiers_sol_1d.json`.

## Conclusion

**High leverage is ruinous. Medium leverage is nearly as bad. Low leverage does not rescue a losing signal.**
Leverage multiplies the existing result and adds carry, so it can only help a signal that already
works out of sample, and on SOL daily bars almost none do.

At 20x, 99.4% of out-of-sample paths contain at least one liquidation, the median path loses 100% of
capital, and 95% of paths end at or below 10% of starting equity. At 5x, 74% of paths are ruined.
At 2x, 21% are.

## Setup

- Series: SOL daily, 1,875 bars (2021-06-17 to 2026-08-04), the sweep's medium-horizon parameters for all 25 registered base strategies.
- Evaluation: CPCV, 8 blocks, 2 test blocks per path, 28 paths per strategy, 514 pooled paths across the 25 strategies (block 0 has no warm-up history and slow strategies lose further blocks, so fewer than 25 x 28). No parameter is fitted, so no purge applies; warm-up comes from the bars before each block (`backtester/core/cpcv.py`).
- Tiers: low 2x, medium 5x, high 20x (configurable with `--tiers a,b,c`), plus a 1x perp as the unlevered reference on the same cost model.
- Costs on every run: 6 bps open and 6 bps close fee, 2 bps slippage, hourly borrow fee on notional (1.6 bps/hr long at 50% utilization), maintenance margin 0.2%, fill at next bar open.
- Liquidation: fill at the liquidation price (or the bar open if the market gapped through it) moved 50 bps against the position, remaining collateral forfeited. The 50 bps is an assumption, not a venue constant.
- Intrabar: every held bar is checked on the 1m bars (last 30 days) or 1h bars (366 covered days) inside it when a layer covers the bar completely, with borrow fees accrued to the moment of the touch. All other bars use the daily low/high, which is never less severe. Covered days: 26 (1m), 366 (1h), of 1,875. In the 366 days where both feeds exist, the daily low was never more than 5 bps below the lowest hourly low, so the two feeds agree.
- Ruin: equity at or below 10% of the starting capital at any point on a path. Paths concatenate per-block returns as the repo's CPCV does, so ruin is per two-block path, not one continuous history.

## Results (out of sample, pooled over strategies and paths)

| Tier | Leverage | Median OOS path Sharpe | Paths with Sharpe > 0 | Liquidations per path | Paths with a liquidation | Median max drawdown | P(ruin) |
|---|---|---|---|---|---|---|---|
| 1x perp | 1x | -0.390 | 36.6% | 0.01 | 1.4% | 54.2% | 1.2% |
| Low | 2x | -0.445 | 35.8% | 0.35 | 22.0% | 81.3% | 21.0% |
| Medium | 5x | -0.487 | 31.9% | 2.34 | 71.8% | 99.5% | 73.7% |
| High | 20x | -1.571 | 8.9% | 7.11 | 99.4% | 100.0% | 95.3% |

Median compounded path return: -27.5% (1x), -62.1% (2x), -98.3% (5x), -100.0% (20x).

## What survives

Strategy-level medians (per-strategy file) show where the damage concentrates:

- Buy and hold: median Sharpe -0.07 at 1x, -0.11 at 2x, -0.88 at 5x, -1.25 at 20x. P(ruin) 18%, 57%, 100%, 100%.
- Only 4 of 25 strategies have a positive median OOS Sharpe at 1x, 5 at 2x, 3 at 5x, and 0 at 20x.
- The single standout is `hurst_switch`: median Sharpe 0.64 (1x), 0.65 (2x), 0.73 (5x) with zero liquidations, then 0.00 at 20x with a median 100% loss and 80% ruin. Treat it as one of 25 tries. Stele KNOW-596 puts the PBO of this strategy set at 0.700, so the in-sample-best selection is anti-informative, and this table picks it after seeing the outcomes.

## Why leverage cannot help here

- Break-even move is independent of leverage (Stele DOC-714, `research/LEVERAGE-ECONOMICS.md`). Leverage changes only the barrier distance and the carry drag on collateral.
- Barrier distance at entry is about 1/L minus 0.8%: roughly 49% at 2x, 19% at 5x, 4.2% at 20x. SOL moves 4% in a normal day.
- Carry alone is 19 bps of notional per day. At 20x that is 3.8% of collateral per day, so a buy-and-hold position at 20x is liquidated by carry within about 26 days even if price is flat. At 1x, carry alone exhausts collateral in about 1.4 years, which is why even the 1x perp shows liquidations.
- The base signals lose money out of sample (Stele KNOW-632: every spec strategy looked excellent in sample and lost out of sample on these 1,875 bars). Leverage compounds a negative expectation faster.

## Limits of this study

- Daily series only. Hourly SOL has two disclosed gaps and the engine refuses gapped cadence; 1h and 1m enter as intrabar layers instead.
- Intrabar layers cover about 20% of days. Elsewhere the check is the daily low/high. That is the honest limit of the cached data; daily and hourly bars hide intrabar liquidations in the flattering direction (Stele KNOW-657), so the 1x to 20x results are, if anything, optimistic for the uncovered 80%.
- Long/flat only. The wrapped strategies never short. Price-impact fees, keeper latency and priority fees are not modelled and each would worsen the numbers.
- Per-path ruin is a property of two-block concatenations of fresh-capital runs, not a single compounding history.

## Tests

`backtester/tests/test_intrabar_liquidation.py` fails if a liquidation hidden inside a daily bar is missed (hourly wick under a clean daily bar; daily low deeper than the hourly feed; close recovering after a wick), checks the adverse fill and forfeiture, the no-op case when nothing liquidates, the fallback count for uncovered bars, and a no-leak check that the tier decision ignores future bars.
