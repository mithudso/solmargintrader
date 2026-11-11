# ZEC ensemble hypothesis catalog

Version: 1
Delta: initial runnable catalog and preregistered selection method.

The supplied `/Users/mitch/Downloads/Strategy Ensembles.md` is a hypothesis guide.
Its 848-hour sample, undefined exact settings and missing source hash do not
establish a reproducible winner. Its categorical claims are tested, not assumed.

`research/zec_ensembles.py --plan` enumerates 826 configurations per interval,
1,652 total across 1m and 1h. The catalog counts all trials, even behavioral
aliases; aliases are removed only from finalist selection using validation-target
hashes. This does not claim to exhaust every mathematically possible ensemble.

| Family | Total both intervals | Testable question |
| --- | ---: | --- |
| Canonical singles | 60 | Which of the thirty unleveraged policies survives costs on this asset and frequency? |
| Parameter sensitivities | 38 | Do shorter/longer formation windows, stronger breakout confirmations, altered calm quantiles and lower volatility targets change stability? |
| Two-member voting | 280 | Does unanimity, union, mean, strict majority or exact two-thirds confirmation improve each guide pair? |
| Three-member voting | 560 | Does a third member diversify, dilute, duplicate or suppress the first two? |
| Guide and family committees | 60 | Do the supplied guide committees and trend/flow or reversion families generalize? |
| Turnover deadbands | 28 | Do 10% and 25% incremental-exposure deadbands save enough costs to offset delayed resizing? |
| Confirmation persistence | 42 | Do two, three or five consecutive active/inactive observations reduce whipsaw? |
| Training-correlation weights | 14 | Do weights inversely proportional to absolute training signal-correlation mass reduce redundant votes? |
| Hierarchical permission | 180 | Does a component's positive long target improve each trigger, with one/two/three confirmations? |
| Gate then soft vote | 300 | Does a long-target permission gate followed by a two-signal mean outperform the ungated combination? |
| Trend/reversion routing | 90 | Does routing between trend and reversion according to a gate improve on suppressing the opposite family? |

Gate semantics are exact: `gate > 0` is permission from the component's long
allocation. `vol_regime` includes a trend condition and volatility classification;
`adx_trend` includes direction and ADX strength. Neither is a generic market-state
probability. Gate mode multiplies permission by the trigger mean. It differs from
`all`, which takes minimum allocation. Majority requires strictly more than half;
supermajority requires at least two thirds. For five members, three votes pass
majority and fail supermajority, correcting the guide's 3/5 versus 2/3 ambiguity.

The three leverage-tier wrappers and trigger-expiry strategy are recorded as
outside this unleveraged spot study. They require different execution/configured
trigger semantics; projecting them onto spot would mislabel the experiment.

## Data and allocation rules

The venue is Binance spot ZEC/USDT. USD and USDT are not treated as identical.
Missing bars are never filled. The primary minute window is the latest 180
calendar days, then the latest complete contiguous suffix if a gap exists. The
primary hourly window uses the entire latest contiguous native-hourly suffix.
These deterministic data-quality rules do not inspect strategy performance.
The long original history remains available for separate fixed historical stress.

Each member advances from its own canonical warmup. The ensemble allocates only
after the longest member warmup. This differs from the legacy Composite policy,
which first consults every member at the longest warmup. The shared builder and
cached paths use the same stated policy. Prefix tests cover stateful members.

Generic engine lookahead guards remain unchanged. The shared trusted built-in
policy path uses causal prefix views and finite-indicator windows to avoid
quadratic copying. Full-prefix Wilder RSI, EWMA variance and cumulative OBV carry
the same recurrences in state. Tests compare these to canonical prefix replay.
Volatility-target parameters denote annual volatility: the shared member converts
the registry's daily normalization to the actual bar frequency. Research and
paper workers use this same interval-aware adjustment.

## Selection and evidence

Execution is long-only spot, 1x, with assumed 10 bps taker fee and 2 bps slippage
on every incremental fill. Signals at close t fill at open t+1. Spot carries no
borrow fee. Holdings are liquidated at each historical fold end; paper sessions
keep their own account open. Costs are charged on resize differences, not a
synthetic full round trip. Fee schedules, spread and live capacity are assumptions,
not evidence of an executable edge. A doubled-cost holdout stress is reported.

Oldest 40% of each primary window supplies fitted correlation weights. The next
40% is split into three chronological validation folds. The newest 20% is reserved
for this run; other prior research may already have inspected these historical
dates. A fresh cash account starts each fold while signals retain only causal
pre-fold market context. Candidate score is median validation daily Sharpe minus
half its fold standard deviation minus twice the worst absolute fold drawdown.
Eligibility requires ten closing/downsizing outcomes across validation and at
least two folds with an outcome. Outcome count is not an independent trade count.

The ten behaviorally distinct eligible candidates with highest validation scores
are frozen before any final holdout is evaluated. There is no holdout re-ranking.
Holdout cash and buy/hold, doubled costs, common-calendar holdout comparisons,
and three earlier fixed 30-day stress windows are reported. Earlier windows start
at the 25%, 50% and 75% row positions of pre-primary source history and apply the
same latest-contiguous-suffix rule. Insufficient windows remain explicit.

Daily Sharpe supports a common return frequency, but primary 1m and 1h histories
cover different market periods. The global ranking therefore does not isolate a
causal timeframe effect. The common-calendar holdout comparison is diagnostic,
not another selection stage. Deflated Sharpe is an IID-daily heuristic with all
1,652 trials counted; it does not establish robustness under autocorrelation.
The top ten are paper research candidates even if their holdouts lose money.

## Reproduce

```bash
python research/zec_ensembles.py --data-dir /absolute/validated/data --output /absolute/study --plan
python research/zec_ensembles.py --data-dir /absolute/validated/data --output /absolute/study --workers 6
```

A study manifest binds source files, cost/window settings and all backtester core
source files. Changed bindings refuse reuse. Expensive component caches are
resumable and checksum/shape/finite checked. A process lock prevents competing
writers. Study publication refuses a code change during evaluation. No fetching,
service installation or trading occurs in the backtest command.
