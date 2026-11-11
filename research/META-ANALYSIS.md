# Trading research synthesis and prospective investment plan

Version: 1.2.0. Evidence cutoff: 2026-11-11. Status: retrospective follow-ups, tiny live validation and installed paper-cohort acceptance complete; future economic evidence remains unqualified. /dr semantic review passed; skill publication is withheld by the owning hub structural gate.

## Decision

Keep new autonomous strategy capital in cash while the frozen paper
comparison runs. The candidate to challenge is unlevered hourly ZEC Bollinger-band
(BB) breakout, with a 40-bar window and bands at 2.5 standard deviations. Compare
it with cash, passive ZEC, a training-volatility-scaled initial ZEC/cash holding
and a fixed BTC/ETH passive allocation. This is a test candidate, not a validated
investment recommendation.

At the actual taker fee, the examined-history replay returns +4.53% for BB,
+129.64% for passive ZEC and +62.14% for the training-scaled ZEC/cash control.
The scaled control also has a smaller maximum drawdown than BB. The replay
window and costs are specified in the follow-up results below. These reused
dates cannot establish a future winner. The evidence does not identify a
strategy that maximizes future profit.

The authenticated Coinbase API observation on 2026-11-11 at 17:07:59 UTC shows
50 bps maker and 90 bps taker commission per side. One basis point (bp) is 0.01%;
these rates are 0.50% and 0.90% on each buy or sell, before execution drag.
The fee observation is retained in
[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/authenticated-fees.json](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/authenticated-fees.json).
Coinbase One does not establish an API fee waiver. Maker-rate simulations require
separate fill, queue and adverse-selection evidence. The primary prospective
scenario uses the taker rate plus adverse execution costs.

This recommendation concerns new strategy capital. It does not direct a sale of
the owner's existing holdings or modify another strategy's accounts.

## One consolidated evidence file

The current complete machine-readable consolidation is:

[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/run-v4/all-trials.json](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/run-v4/all-trials.json)

Its exact source inventory is:

[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/run-v4/inventory.json](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/run-v4/inventory.json)

The file retains 171 distinct source artifacts: the original 146 family artifacts
and 25 additional follow-up, operational and methodology artifacts. It includes
22,913 configuration records and 1,652 ensemble configurations, together with
the other studies below. These are source and configuration counts, not
independent-study counts. Original records, SHA256, units, provenance,
diagnostic/report roles, insufficient cells and invalid-source exclusions remain
visible. The companion JSON preserves complete numerical payloads rather than
replacing unfavorable rows with selected headlines.

The preserved 146-artifact baseline reviewed by the original DDO run is
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/run-v2/all-trials.json
and its sibling inventory. Later receipts do not alter that fixed baseline.

CSV values retain their original strings. A return fraction of 0.25 means 25%;
`return_pct=25` means 25% over its stated period; `monthly_pct=25` means 25% per
month; and 25 bps means 0.25%. They are different quantities. Nonfinite values remain
explicitly tagged. A CPCV median path return is not a continuously investable
portfolio return. No grand average return or random-effects estimate is computed
across these incompatible and dependent experiments.

## Trial-family results

The consolidation supplies exact source hashes and complete underlying payloads.
Returns below retain each study's original period and cost assumptions. No
common-period conversion is applied here, so the returns are not directly
comparable across rows. DD means maximum drawdown;
OOS means out of sample. CPCV is combinatorial purged cross-validation, PBO is
probability of backtest overfitting, and DSR is the deflated Sharpe ratio statistic.
These diagnostics address selection risk; they do not turn reused prices into
independent observations. Long/flat means holding the coin or cash, without a
short position or borrowed capital.

| Family | Available evidence and denominator | Result and qualification | Principal source |
|---|---|---|---|
| Initial SOL strategy survey | 953 single-split rows | Historical 70/30 splits; some triples selected after inspecting OOS singles. Exploratory. | [/Users/mitch/dev/solmargintrader/research/results/sweep_results.csv](/Users/mitch/dev/solmargintrader/research/results/sweep_results.csv) |
| SOL CPCV | 75 single and 1,046 combination summaries | Daily singles PBO 0.70. Paths and selected combinations reuse prices. Historical prose's 1,287 configuration census differs from current 1,121 rows. | [/Users/mitch/dev/solmargintrader/research/results/cpcv_results.csv](/Users/mitch/dev/solmargintrader/research/results/cpcv_results.csv); [/Users/mitch/dev/solmargintrader/research/results/cpcv_combos_results.csv](/Users/mitch/dev/solmargintrader/research/results/cpcv_combos_results.csv) |
| Cross-asset transfer | Fixed defaults across SOL/BTC/ETH/DOGE/ZEC | All 10 off-SOL top-five Sharpe deltas negative. Simpler directional mechanisms travel better than the selected SOL leaderboard. | [/Users/mitch/dev/solmargintrader/research/results/cpcv_top5_sol_doge_zec_1d.csv](/Users/mitch/dev/solmargintrader/research/results/cpcv_top5_sol_doge_zec_1d.csv) |
| Geometry, perturbation and redundancy | 175 geometry rows per window; parameter neighborhoods and signal correlations | Diagnostics of preceding trials, not independent profitable replications. Correlated votes do not create independent information. | `/Users/mitch/dev/solmargintrader/research/results/geometry_*`; `/Users/mitch/dev/solmargintrader/research/results/perturb_*`; `/Users/mitch/dev/solmargintrader/research/results/signal_redundancy_*` |
| Nine-coin monthly walk-forward | Historical report; raw directory unavailable | Report says 48/54 beat hold in sample, 4/54 walk-forward, 54/54 decayed; grids trail hold 9/9. Lower evidence tier because the raw ledger cannot be rechecked here. | [/Users/mitch/dev/solmargintrader/research/SWEEP-9COIN.md](/Users/mitch/dev/solmargintrader/research/SWEEP-9COIN.md) |
| Corrected resting-grid review | Static SOL ladder plus 8 reset blocks | Account return +32.10% versus hold +88.10%; worst reset block -34.92%. Reset blocks are not a continuous recentering policy. | [/Users/mitch/dev/solmargintrader/research/results/grid_review_20261107.json](/Users/mitch/dev/solmargintrader/research/results/grid_review_20261107.json) |
| Fixed later grid holdout | 94 daily bars; unchanged configuration | Grid +0.83%, hold +21.60%; two round trips and 80 bars above the ladder. Idle capital matters more than fee sensitivity here. | [/Users/mitch/dev/solmargintrader/research/results/grid_holdout_20261107.json](/Users/mitch/dev/solmargintrader/research/results/grid_holdout_20261107.json) |
| Leverage tiers | 25 strategies, 1x/2x/5x/20x, dependent paths | Median path returns -27.5% / -62.1% / -98.3% / -100%, respectively; 20x has liquidation in 99.4% of paths. Perpetual carry is not spot. | [/Users/mitch/dev/solmargintrader/research/results/leverage_tiers_sol_1d_summary.csv](/Users/mitch/dev/solmargintrader/research/results/leverage_tiers_sol_1d_summary.csv) |
| Trigger discovery | 13,510 daily and 30,720 hourly hypotheses | Zero triggers meet all declared reliability gates. The 600 saved selected rows are not the full hypothesis denominator. | [/Users/mitch/dev/solmargintrader/research/results/triggers_sol_1d.json](/Users/mitch/dev/solmargintrader/research/results/triggers_sol_1d.json); [/Users/mitch/dev/solmargintrader/research/results/triggers_sol_1h.json](/Users/mitch/dev/solmargintrader/research/results/triggers_sol_1h.json) |
| Costed trigger trades | 20 selected trigger/tier cells | Exploratory trades share the trigger-discovery history. Neither relabeling nor a second table creates fresh validation. | [/Users/mitch/dev/solmargintrader/research/results/trigger_backtest_sol_1d.csv](/Users/mitch/dev/solmargintrader/research/results/trigger_backtest_sol_1d.csv) |
| Ratio rotation | 144 rows: 72 long-only and 72 neutral | Momentum is stronger than reversion; selected long-only momentum still trails matched ZEC holding and fails its DSR threshold. Short/neutral books do not transport directly to Coinbase spot. | [/Users/mitch/dev/solmargintrader/research/results/rotation_5coin_1d.csv](/Users/mitch/dev/solmargintrader/research/results/rotation_5coin_1d.csv) |
| Minute common-calendar survey | 200 rows; five profitable | Two positive rows are passive; three are selected VWAP-reversion cells. This was a full-sample preliminary search. | [/Users/mitch/dev/solmargintrader/research/results/minute_sweep_x1_common.csv](/Users/mitch/dev/solmargintrader/research/results/minute_sweep_x1_common.csv) |
| Compound defaults | 300 configurations across ten coins | All 5x defaults lose essentially all their OOS stake. Directional hit rate does not establish signed gross expectancy or net profit. | [/Users/mitch/dev/solmargintrader/research/results/compound-10coin-fullhistory-2026-11-07.json](/Users/mitch/dev/solmargintrader/research/results/compound-10coin-fullhistory-2026-11-07.json) |
| Compound frontier | 1,227 trials per coin plus related searches | Sparse slow momentum has selected positive results, but tuning, short exposure, variable windows and drawdowns prevent direct spot promotion. | [/Users/mitch/dev/solmargintrader/research/results/frontier-2026-11-07.json](/Users/mitch/dev/solmargintrader/research/results/frontier-2026-11-07.json) |
| Paired DSO corrections | 544 variant evaluations, 272 signed pairs, 34 strategies | Zero accuracy improvement. Correcting annualization/sizing reduces some reported returns; accounting fixes are not alpha. | [/Users/mitch/dev/solmargintrader/research/strategy_experiment/results/comparison.csv](/Users/mitch/dev/solmargintrader/research/strategy_experiment/results/comparison.csv) |
| Auxiliary DCA/pairs/triangle | 12 mechanism/dataset rows | DCA loses on all four listed datasets; pairs have zero trades; the small triangle gain is inadequate evidence. | [/Users/mitch/dev/solmargintrader/research/strategy_experiment/results/auxiliary.json](/Users/mitch/dev/solmargintrader/research/strategy_experiment/results/auxiliary.json) |
| Validated configuration sweep | 22,913 complete; 15,271 evaluable; 7,642 insufficient; zero failures | Broad CPCV selection. Merge each row's execution_profile and setting_overrides with manifest defaults. Do not infer spot/zero-fee economics from its base 2x settings. | [/Users/mitch/.local/share/solmargintrader/research/strategy-config-sweep-validated-20261110/results.jsonl](/Users/mitch/.local/share/solmargintrader/research/strategy-config-sweep-validated-20261110/results.jsonl) |
| ZEC ensembles | 1,652 IDs; 1,592 eligible; 1,084 distinct eligible validation behaviors | At 10 bps commission + 2 bps execution per side, validation-selected hourly BB40/2.5 reserved test +282.64%, hold +266.52%; DD -21.64% versus -56.02%. Doubled-cost +241%. Selected DSR rounds 0; recent diagnostic -7.63% versus hold -23.21%. | [/Users/mitch/.local/share/solmargintrader/research/zec-ensembles-20261110/study-validated/top10.json](/Users/mitch/.local/share/solmargintrader/research/zec-ensembles-20261110/study-validated/top10.json) |
| Original Volty | 250 settings; 25 walk-forward folds | All five first-half-selected fixed winners lose later halves. Daily adaptive +22.69% versus passive +1,783.71% on those dates. | [/Users/mitch/dev/solmargintrader/research/results/volty_zec_20261110_walk_forward.csv](/Users/mitch/dev/solmargintrader/research/results/volty_zec_20261110_walk_forward.csv) |
| Exact-chart Volty sensitivity | Six scenarios; already examined later history | Gross +391.87%, but net -99.98% with declared GUM costs over 9,433 closed trades. Alternative paths and extra delay also fail. Synthetic shorts are not Coinbase spot. | [/Users/mitch/dev/solmargintrader/research/results/volty_predictive_20261111.json](/Users/mitch/dev/solmargintrader/research/results/volty_predictive_20261111.json) |
| Shape-aware spot | 2,520 cells; eight coins; three frequencies | At zero commission +2 bps, hourly routing beats fixed 5/8 and holding 6/8. Every hourly router loses with zero commission and 25 bps execution drag per side. Date ranges differ by frequency. | [/Users/mitch/dev/solmargintrader/research/results/shape_spot_20261111_summary.csv](/Users/mitch/dev/solmargintrader/research/results/shape_spot_20261111_summary.csv) |
| ZEC wavelengths | 50 spectral tests; 116 forecasts | No corrected spectral rejection. 5m forecasts win 6/29 with 4.54 times persistence MSE. Local spacing is descriptive. | [/Users/mitch/dev/solmargintrader/research/results/zec_cycles_20261111_spectral_tests.csv](/Users/mitch/dev/solmargintrader/research/results/zec_cycles_20261111_spectral_tests.csv) |
| Coinbase50 factorial | 128 portfolios; 300 clock tests; 17 complete grid assets | Zero +2 bps: unfiltered 1.19%, selection 1.90%, full combination -0.48%, selected hold 20.04%. No multiplicity-adjusted grid advantage. Time-of-day effects appear in activity measures, but do not establish directional timing. | [/Users/mitch/dev/solmargintrader/research/results/coinbase50_20261111_summary.json](/Users/mitch/dev/solmargintrader/research/results/coinbase50_20261111_summary.json) |
| Market-data quality | 31 sampled missing-minute runs | 26 contained trades; adjacent existing bars can also be wrong. Missing candles cannot be treated as invented quiet bars. | [/Users/mitch/dev/solmargintrader/research/CANDLE-GAP-AUDIT.md](/Users/mitch/dev/solmargintrader/research/CANDLE-GAP-AUDIT.md) |

Research on nonlinear lead-lag, five-minute execution and strategy cards is
retained as methodological or capability evidence. It is not a measured profitable
strategy. The archived LP manager remains disabled; an old narrative about
profitability does not override its unprofitable operational history.

## Dependence and unavailable evidence

The data reuse structure prevents a conventional statistical meta-analysis of
independent effect sizes. Multiple policies share assets, timestamps, costs and
engine versions. Cost scenarios are stress tests; bootstrap draws and CPCV paths
are resamples, not additional investment trials. Distinct configuration IDs can
produce identical behavior. Cross-asset files can repeat the same rows.

The old nine-coin raw directory
/Users/mitch/Downloads/sol-backtest-data is absent. Its report remains visible
with a lower evidence classification. The invalid-epoch configuration sweep,
prevalidation ensemble run, initial gapped DSO comparison and retired first Volty
forward cohort do not count as independent confirmation of their repaired runs.

All retrospective follow-ups preserve unsealed reservations in
/Users/mitch/.config/soltui/experiments/experiments.sqlite3. The common Coinbase
follow-up has an exclusive end of 2026-11-08 19:00 UTC. Previously viewed data can answer
accounting and mechanism questions, but cannot become newly unseen OOS evidence.

## Patterns across families

**Exposure and regime explain much of the leaderboard.** Rotation partly tilts
toward the same ZEC appreciation that grid exits fail to retain. A selected
indicator's drawdown reduction can result from time spent in cash. Compare it
with a passive allocation whose scale is frozen from training, as well as fully
invested holding. Hindsight average-exposure matching is descriptive only.

**Costs, idle capital and absent gross expectancy are different failure modes.**
Minute Volty loses through turnover even at much lower costs than this account's
API tier. A static grid can lag through missed rallies despite few fills.
Compound hit rates near 52% can coexist with negligible signed expectancy. A fee
waiver cannot fix the last two mechanisms.

**Search depth exceeds independent information.** Counting 22,913 configurations,
44,230 trigger hypotheses, correlated votes and reused historical splits as
independent confirmations creates false precision. The strongest ensemble
challenger is one simple rule, and the full five-factor grid stack underperforms
selection alone. Adding another optimized layer needs a new prospective question.

**Engineering validity and economic validity are distinct.** DSO corrections,
verified source citations, software tests and process health improve confidence
in what a program does. They do not establish profitable fills. Missing candles,
blocked prospective decisions and fee-tier mismatches are economic inputs.

## Follow-up implementation plan

| Question | Predeclared implementation | Interpretation and completion evidence |
|---|---|---|
| Does the candidate survive actual API costs? | /Users/mitch/dev/solmargintrader/research/meta_followups.py: frozen 1x long/flat ZEC BB40/2.5, slow-trend comparator and passives; 10/50/90 bps fees plus 2 bps execution. | Native Coinbase common contiguous history; indicator warmup from the training prefix; 50 bps is a hypothetical maker-rate sensitivity. Existing examined history remains exploratory. |
| Is apparent profit mostly ZEC exposure? | Rebuild original top 50 masks 0/1/31 with the ZEC slot kept in cash, without substituting another coin. | Fixed slots preserve funding. Compare original versus no-ZEC; do not call this a causal market experiment. |
| Does activity timing imply directional alpha? | Retain the corrected 300 test result and prospective hourly observations. | No retrospective hourly retuning or reinterpretation of volatility as direction. |
| Can the rule transport to Coinbase USD spot? | /Users/mitch/dev/solmargintrader/ecosystem/meta_forward.py: isolated frozen Coinbase cohort with candidate, cash, passive ZEC, training-scaled ZEC/cash and fixed BTC/ETH passive. | Separate from the existing Binance ensemble owner; reference candle fills do not certify executable quotes. |
| Can the account execute and reconcile a tiny spot round trip? | Existing explicit-size guarded Coinbase manual adapter; 2 USDC SOL canary, sell only newly acquired quantity. | Actual previews, fees, client intents, order IDs and fills; maximum 10 USD total deployed. This certifies plumbing only. |

The actual-cost replay and concentration outputs belong under
[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1).
The fixed-policy replay completed. Its common contiguous native Coinbase window
has 4,428 hourly bars: the first 1,771 provide the training prefix and indicator
warmup, and the last 2,657 evaluate previously examined history. Evaluation runs
from 2026-07-21 02:00 UTC to the exclusive cutoff of 2026-11-08 19:00 UTC.
The replay and calendar sources are
[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1/fee_replays.json](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1/fee_replays.json)
and
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1/calendar.json. At 90 bps commission plus 2 bps execution per side:

| Fixed policy | Account return | Maximum drawdown | Qualification |
|---|---:|---:|---|
| ZEC hourly BB40/2.5 | +4.53% | -30.71% | 42 fills; mean inventory exposure 23.37%; USD-denominated simulated fees 4,234.60 per initial 10,000 USD account |
| Passive ZEC | +129.64% | -37.33% | Same evaluation dates and entry/exit costs |
| ZEC SMA200 long/flat | -11.64% | -61.66% | Fixed slower comparator, not retuned |
| Equal BTC/ETH holding | +14.62% | -17.22% | Fixed equal initial allocations |

A training-only volatility ratio fixes the initial passive allocation at
47.9334% ZEC and 52.0666% cash. This uses a training volatility ratio; it
does not produce exactly matched risk, even in training. The actual training
mixture volatility is about 85.95% of BB volatility. It divides BB net hourly log-equity
volatility by same-prefix passive volatility and clamps the ratio to [0,1].
The allocation buys once and lets units drift; it does not rebalance hourly.
Over the same examined evaluation, it earns +62.14% with -27.61% maximum
drawdown, beating BB on both measures. The exact derivation and source binding
are in /Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/training-benchmark.json.
The training mixture check is saved in
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/training-mixture-check.json.

BB returns decline from 46.28% at 10 bps fees to 23.66% at 50 bps and 4.53% at 90 bps.
Its estimated historical zero-return commission ceiling is about 100.56 bps per
side while execution drag stays at 2 bps per side, as recorded in
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1/breakeven.json. That ceiling is scenario-specific, not a fee budget
that guarantees future profit. The maker-rate case has no queue/nonfill model.

Keeping the ZEC slot in cash changes the old zero +2 bps grid baseline from
+1.19% to -0.12%, ranked selection from +1.90% to +0.75%, and the full combination
from -0.48% to -0.59%. Passive market-cap-ten holding changes 26.97% to 13.15%.
The selected passive cohort changes 20.04% to 19.89%; its dependence on ZEC is
smaller on these specific folds. Concentration is therefore policy-dependent.
These are fixed-slot attribution diagnostics, not new out-of-sample tests.
The exact values are in
[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1/concentration.json](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/followups-v1/concentration.json).

The follow-up manifest binds its inputs, code and results. The implementation
author reran 12 research tests (five consolidation tests and seven follow-up
tests), 20 forward tests and Ruff over the six new source/test paths; all exited 0.
The saved logs confirm the successful test counts and lint result:

- /Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/research-tests.log
- /Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/forward-tests.log
- /Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/ruff.log

These checks establish software behavior, not profitability. The follow-up does
not reprice the old resting grid at 90 bps; only the newly declared directional
replay uses that actual-fee scenario. Final delivery must bind these checks to
the delivered source.

## Independent analysis and comparison

The separate analyst worked from underlying artifacts before reading this draft.
Its report is
[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/independent-analysis.md](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/independent-analysis.md).
It recommends cash for new live strategy capital and frozen hourly BB40/2.5 as a
paper challenger, with a training-scaled passive control and a diversified
passive control.

The parent received preliminary reviewer findings while preparing its own
synthesis. This is an independently sourced review blinded to the parent's
draft, not a claim of two fully blinded investment decisions. The parent initially
considered a diversified passive core as an allocation candidate; the reviewer
prefers cash until prospective evidence. The installed forward implementation compares both
without imposing a new real-money allocation. Its independently verified startup
and restart receipts are described below.

Agreement: no validated future-profit maximum; no grid/cycle/topology promotion;
actual fees must be included; simpler slow rules deserve a small frozen paper
family; missed decisions cannot be backfilled; minimum elapsed time or trade
counts alone cannot prove an edge. The retrospective replay and eventual
prospective evidence must resolve economic differences rather than averaging
the two opinions.

## Investment policy and prospective evaluation

Research comparison capital is 10,000 quote units per independent virtual book.
The native Coinbase replay uses USD; the live canary uses USDC. Those currencies
and the separate virtual books are not combined into one return series.
These accounts do not represent one funded portfolio with duplicated capital.
The owner selected approximately 30% drawdown tolerance after the protocol freeze.
The dated risk amendment preserves the original cohort parameters. This is a
planning limit, not a guaranteed loss cap; gaps can exceed it. On the fixed
delay-two historical replay, the scaled passive book has the largest return
among the declared books whose observed drawdown stays below 30%. That
retrospective ranking is not a sizing rule or a forecast.

1. The implementation owner froze the ten-book protocol at 17:42:10 UTC,
   before activation at 17:42:24 UTC on 2026-11-11. The original protocol is
   /Users/mitch/dev/solmargintrader/docs/META-FORWARD-PROTOCOL.json, SHA256
   `499e0e7621c3ad501d006db11f594c1f1619cd175030ef977aa1d3a9cd1f5f5e`.
   Day 30 is an engineering check; day 180 is descriptive; day 365 is the terminal
   economic review. Compare BB with cash and the three passive controls using
   paired hourly net-liquidation changes, a stationary block bootstrap with
   mean block length 168 hours, 10,000 replicates and seed 1391, and Holm adjustment
   across four primary comparisons. The maker scenario remains descriptive.
   Require at least 30 completed primary BB round trips and a valid complete
   common calendar; insufficient events make the endpoint inconclusive. There
   is no optional extension or automatic live promotion. The bootstrap is an
   approximation for dependent, potentially nonstationary observations.
2. Use current API taker fees and nonzero execution drag as primary assumptions.
3. Warm historical inputs for indicators only. Commit and confirm activation
   before any future decision can become eligible for reference execution.
4. Persist every observation, target, inventory mark, fee, outage and missed
   decision. Restarting cannot erase losses or turn a gap into historical fills.
5. Compare after-cost growth, drawdown, exposure, turnover and dependence-aware
   paired excess returns over shared dates. Report the entire frozen family.
6. Review operational health immediately. Assess economic evidence only as the
   frozen protocol permits; do not choose review times after observing P&L. A
   30-day initial review is an engineering checkpoint, not proof of profitability.
   Sparse rules may require months.
7. Do not scale live strategy capital until cost-stressed results support the
   candidate versus cash and an appropriately scaled passive alternative.
   Retuning starts a new cohort and cannot rewrite the old one.

Cash here means unchanged quote balance in the simulation, without assumed
interest. It does not establish that a stablecoin or exchange account is risk-free.
The corpus studies crypto trading mechanisms; it is not a comparison of all
investment asset classes or an optimal personal financial plan.

## Forward and live execution evidence

The independent analyst's 2026-11-11 status check found immature observations in
the existing ZEC ensemble service and no qualified profit evidence. It found the
two 1m Volty v2 accounts blocked with `missed_decision_window`. Preserve those
observations and do not reset the accounts. The new cohort must retain separate
ownership from existing services.

The installed cohort runs in /Users/mitch/.venvs/meta-forward-20261111 with
home /Users/mitch/.local/share/solmargintrader/meta-forward-20261111 and launchd
job `com.solmargintrader.meta-forward.1391`. Independent acceptance at
2026-11-11 17:45:23 UTC verified all 48 numerical source hashes, ten independent
10,000 USD books, 67 permitted seed bars, and a durable decision confirmed before
its 18:00 UTC eligible open. It observed zero trades and zero historical P&L.
A controlled restart changed the PID while preserving seven captured state
and ledger tables. Other service entries stayed unchanged. The acceptance
receipt is /Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/acceptance.json,
SHA256 `81f3c8f87aa668c4d8331390a97e185d6846ac17786378dbc99896b376421924`.

An hourly candle-open reference observed afterward is not an executable bid/ask
receipt. Forward accounting and actual fills remain separately labeled. The
existing specialized services retain their own ownership and observations.

Live validation records are kept privately under
[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/live-validation](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/live-validation).
The source receipt is
[/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/live-validation/round-trip-receipt.json](/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/live-validation/round-trip-receipt.json).
The 2 USDC round trip completed: buy order e1115fbb-18e6-4217-be24-c631af728949
and sell order ef956d48-c450-48d9-90e1-846a4873308a both filled. The bought
and sold quantity was exactly 0.02332942 SOL. Actual deployment was
1.9979911742729938 USDC, commissions 0.0356811310138138 USDC, and net
quote change -0.0314503132597938 USDC. No newly acquired SOL remains and
no manual order is unresolved. Individual fill receipts identify all three fills
as taker executions; buy fill sizes are quote units while the sell fill is base
units, so they cannot be naively summed. This validates the tested path only.

Use explicit quantities and durable client intents. Never use the separate
Oracle adapter's 75%-of-balance sizing for a tiny canary. Do not retry an ambiguous
submission; reconcile its saved client/order ID. The new strategy remains paper.

## Verification and reproducibility

Consolidation source: /Users/mitch/dev/solmargintrader/research/meta_analysis.py. The file preserves original
records instead of renaming all metrics to percentages or silently dropping
insufficient results. Byte-identical copies are aliases; semantic overlap remains
explicitly documented. Invalid or missing sources remain in the exclusion ledger.

The sibling review record is
[/Users/mitch/dev/solmargintrader/research/META-ANALYSIS.md.ddo-report.md](/Users/mitch/dev/solmargintrader/research/META-ANALYSIS.md.ddo-report.md).
The requested three-iteration DDO run applied all passes and closed ten
Medium-or-higher findings. Its final bound version retained one Medium finding:
the pending /dr paragraph lacked an owner, exact status and concrete next action.
That version ended `blind_audit_dissent`; its receipt is preserved. This revision
adds the actual research and deployment receipts and receives a separate final
review. Neither document review certifies future profitability.

The TASK-1391 implementation owner ran /dr on dependent trials, sequential
comparison, passive attribution, uncertain-edge allocation and tiny-trade
certification. Its final semantic gate passed all 115 authored assertions:
92 SUPPORTED and 23 NO-FACTUAL-ASSERTION, exit 0. One unrelated Kraken temporal
claim was withheld entirely; unsupported process notes remain in private repair
records. The actual gate is
/Users/mitch/.global-ai-hub/research/sequential-validation-and-capital-allocation-after-dependent-crypto-strategy-trials/gate.json.

Skill publication remains withheld. The owning trading hub's structural check
exited 1 with eight preexisting High missing-reference routes. The new local
spoke is not certified as a clean registered publication. The implementation
owner must reconcile those routes in separately scoped skill maintenance, wire
the spoke, rerun its structural gate and registry routing, then complete normal
publication. The exact findings, status and next action are saved in
/Users/mitch/.global-ai-hub/research/sequential-validation-and-capital-allocation-after-dependent-crypto-strategy-trials/report.md
and its sibling `structural-validation.json`. The adapter finish receipt at
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/dr-finish-receipt.json
records `BLOCKED`, exit 0. Trading research does not wait for that registry repair.

## Additional fixed checks and updated consolidation

The independent analyst also ran one unchanged delay-two reference replay on
the same 2,657 evaluation bars at 90 bps commission plus 2 bps execution. This matches
the new paper owner's conservative two-bar timing, rather than the original
delay-one historical variant. Results: BB +6.82%, DD -29.14%; scaled passive
ZEC/cash +61.59%, DD -27.57%; full ZEC +128.49%, DD -37.33%; BTC/ETH +14.18%,
DD -17.22%; SMA200 -30.49%, DD -66.57%. The fixed initial ZEC budget is unchanged.
The source-bound result is
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/latency-variant.json,
SHA256 `15e1481efc829261f234b49c2f1f28b46ddd444b2ff026a743079fbb8b58ecde`.
The passive comparison survives this latency sensitivity. It remains examined
history, not a second independent validation.

The legacy generic forward database contains 21,085 trial metadata rows and
1,083,241 call rows at this inventory observation. These calls are not completed
trades or investment P&L. Only labels, operational metadata and call counts were
read; protected candle and outcome values were not mined for a new ranking.
The saved inventory is
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/legacy-forward-inventory.json.

A separate authenticated readiness read found ZEC-USDC and ZEC-USD online, with
minimum quote size 1 and quote increment 0.01. A 2 USDC ZEC-USDC BUY preview returned
estimated commission 0.0178394449950445986 USDC and total 2 USDC. No ZEC order was
submitted. This preview and product metadata are saved in
/Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/zec-execution-readiness.json.
The tested actual round trip was SOL-USDC; a preview does not certify ZEC fills.
USD paper accounting also leaves USD/USDC basis and execution behavior to verify
before any investment promotion.

The updated single-file consolidation now includes the original family payloads,
new follow-up results, generic forward metadata, live receipts, paper acceptance
and /dr disposition: /Users/mitch/.local/share/solmargintrader/research/meta-analysis-20261111/run-v4/all-trials.json.
It retains 171 distinct source artifacts, with no read errors; SHA256
`72d86b9d035060a07702f995363371309ef8175ca5a682d9e31a61e26f03973a`. Its sibling inventory lists every source and byte-identical alias.
The earlier 146-artifact ledger above remains the fixed baseline reviewed by DDO.
