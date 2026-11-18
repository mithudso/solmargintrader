# ZEC/USD five-minute mean reversion

The equal-weight RSI, z-score and Bollinger Band ensemble turned **$10,000 into $10,248.71** in the held-out Coinbase ZEC/USD spot simulation at 10 bps commission plus 2 bps execution allowance per fill. Cash finished at **$10,000.00** and buy-and-hold at **$9,499.66**. The ensemble had **1.32% peak-to-trough drawdown**, 28 fills and 13 sell events over **8 hours 40 minutes**. The result is a short historical observation after a broad strategy search.

See the [strategy card](ZEC-5M-MEAN-REVERSION-CARD.md) for the exact rules and machine-readable policy.

## What the strategy does

The ensemble buys into weakness and scales out as its three indicators recover. Each member maintains its own long-or-flat state. At each completed five-minute candle, one active member targets one-third of equity in ZEC, two target two-thirds, and all three target full exposure. The simulated account fills at the next bar's open. It can rebalance a fractional target even when the vote count stays the same because price moves change the current allocation.

The two price-distance rules share a 20-close moving average. The z-score uses sample standard deviation and includes equality at its boundaries. The Bollinger rule uses population standard deviation and strict price inequalities. Their signals can differ, but both respond to the same kind of price stretch. RSI adds an oscillator based on the balance of recent gains and losses. A persistent selloff can keep the signals active while ZEC continues falling. There is no separate stop-loss or maximum holding time in this policy.

## Window and selection

The batch requested November 10 20:47 through November 17 20:47 UTC in 2026. The ZEC simulation used the longest gap-free segment, **November 11 00:16 through November 12 19:46 UTC**, with 2,610 observed one-minute candles. The five-minute clock used complete bars. The full-window account ran November 11 00:20 through November 12 19:45 UTC (521 bars). Validation ran November 12 02:25–11:00 UTC (103 bars), and the held-out account ran November 12 11:05–19:45 UTC (104 bars). All end times are exclusive.

The chronological 60/20/20 design used the early bars for indicator history and training-dependent candidates. The runner ranked eligible policies on validation return after costs, requiring at least ten sell events. It kept the final test out of that ranking. Validation and test each start with fresh USD cash and use the earlier indicator history. Any remaining position is sold at the final close of each account. The catalogue contained 1,707 underlying templates, each tested with up to six filter/control modes at each cadence and fee. The full-window account overlaps selection and test.

## Fee sensitivity for the same policy

The table holds candidate `697f3b1dd4526147f43ca3d4` and its unfiltered policy fixed. Every fee row adds the same 2 bps execution allowance on traded notional. Drawdown is the observed decline from the account's equity peak.

| Commission per fill | Validation return | Test return | Test P&L on $10,000 | Test drawdown | Test costs | Test buy-and-hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 bps | +1.01% | +2.49% | +$248.71 | 1.32% | $72.90 | −5.00% |
| 15 bps | +0.88% | +2.18% | +$217.88 | 1.37% | $103.14 | −5.10% |
| 25 bps | +0.61% | +1.56% | +$156.46 | 1.47% | $163.37 | −5.29% |
| 60 bps | −0.33% | −0.56% | −$55.95 | 1.81% | $371.68 | −5.95% |

The fixed policy beat buy-and-hold by **7.49 percentage points** at the lowest fee. It still beat buy-and-hold at the highest fee, when cash did better than either position. The batch's report lists **−0.60%** for its 60 bps selection because validation selected an inverse-correlation-weighted version at that fee. The lowest-fee full-window account returned **+6.05%**, with **2.34% drawdown**, versus **−9.76%** for holding ZEC. That account adds context about the decline and covers some of the same observations as the holdout.

Sell events include partial reductions and any forced final sale. The 13 events therefore do not supply 13 independent round trips or a trade win rate. Recurring small rebalances help explain why the ensemble is sensitive to per-fill costs even at five minutes.

## What simplification and extra filters did

These comparisons use the same held-out five-minute clock and lowest fee. The individual indicators have the exact member parameters from the ensemble. The shape and harmonic rows use the same three-member policy with an added filter.

| Variant | Test return | Test drawdown | Test sell events |
| --- | ---: | ---: | ---: |
| RSI alone | +0.15% | 2.10% | 1 |
| Z-score alone | +3.92% | 1.59% | 4 |
| Bollinger reversion alone | +3.42% | 1.59% | 4 |
| Equal mean, unfiltered | +2.49% | 1.32% | 13 |
| Equal mean, causal shape filter | +2.51% | 1.32% | 14 |
| Equal mean, harmonic direction filter | +0.15% | 1.00% | 8 |
| Equal mean, positive linear-slope filter | −0.03% | 1.32% | 2 |

The z-score and Bollinger rules earned more in this holdout with four sell events apiece. The ensemble had smaller drawdown and more reductions. The 0.03 percentage-point lift from the shape filter, before rounding the rows, is small for this sample. The harmonic filter cut the return to 0.15%. These are retrospective comparisons against the same held-out window. They do not change the validation-selected policy.

## What the evidence supports

This run shows that a long-only strategy could earn money on brief rebounds while ZEC fell overall. It does not estimate a prospective hit rate, realistic fill capacity, or maximum loss across regimes. There were no observed order-book fills, spreads, partial fills or latency costs in the simulation. The cost scenarios bracket the observed sign change between 25 and 60 bps commission for this sample. Actual economics depend on the trading fee and attainable fills. Repeated selloffs, higher costs and weaker rebounds can all change the result.

## Evidence and retrieval

The source is the completed local batch under `research/my-coins-study`. The ZEC child is `markets/ZEC-USD`. It preserves the native Coinbase candles, account rows and frozen plan. The input archive stays with the local study. A fresh clone can read this report and card, and needs the original local artifacts to verify this historical result.

| Child file | SHA-256 |
| --- | --- |
| `run-plan.json.zlib` | `3741671975a84960e2fc97e8c4c1766e7a66f2c8d0efae28de5b16153c7f9a6f` |
| `selected-5m.json` | `00cd2e613d159e93747f134ed4024dbfedf8ab10fad33b666646e36b3e935065` |
| `strategies-5m.csv.gz` | `7dca905f1fe997ec4385bfda8c9c1574e3e5e96674d5dba1c0a41613ee2249bf` |

The plan records source base `284c6953640b590d49eba9c0f79cfb188b8fce3d` and binds individual source files by hash. In `strategies-5m.csv.gz`, filter by candidate ID, `mode=baseline` and the desired split and fee to find the fixed-policy rows. The benchmark IDs are `cash` and `buy_and_hold`. The singleton IDs are `dee0039e46efd365c5f6ea0d` (RSI), `4aee6542900bfaad23c1c74f` (z-score) and `b7d879144b7c11147d802536` (Bollinger). See the [launch and scripts guide](../../docs/RUNNING-TOOLS.md#inspect-or-repeat-the-zec-study) for the offline verification command and a fresh spot run.
