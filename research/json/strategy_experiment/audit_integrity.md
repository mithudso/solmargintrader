# DSO integrity audit: original default strategy registry

research output, not investment advice; simulation only

Version: 1
Delta: Initial audit.

Scope: 34 registered defaults; 100 passes in DI, OV, ST and RR. This is the pre-fix integrity family report, not the final all-family convergence result.

## Finding

F1 — Critical — RR-01 / DI-18. Annual target_vol is divided by volatility annualized at 365 bars/year even on hourly data. Risk-normalized exposure is therefore oversized before cap. Evidence: backtester/core/strategies/signals.py:394, backtester/core/strategies/advanced.py:465, backtester/core/indicators.py:327, backtester/core/indicators.py:438.

Candidate copies only: infer validated cadence from visible timestamps and pass 365*86400/cadence explicitly into realised_vol and ewma_vol. Assert daily parity, hourly scaling, causal prefix invariance and refusal on invalid cadence.

## Verification

216 existing targeted tests passed in 13.730 seconds using the existing Python 3.13 environment. The initial system-Python attempt failed because pandas was absent; it was not a strategy regression. Exact command and exit codes are in the JSON.

## Applicability and evidence

A `ran` row states exactly what was inspected or executed. It does not imply the check passed. Missing numerical methods are explicitly unexecuted. Historical cache comparisons cannot establish a fresh holdout or promotion.

| Pass | Method | Status | Evidence / limitation |
| --- | --- | --- | --- |
| DI-01 | Prefix-invariance (truncation) test | insufficient evidence (inputs absent) | Full sequential prefix-invariance check for every registered default at eight checkpoints not run in this sub-audit. Existing tests cover subsets only. |
| DI-02 | Engine future-access guard | ran | Inspected read-only owned public BarWindow arrays and passing adversarial history tests in test_engine_audit. |
| DI-03 | Data-slice re-run lookahead analysis | insufficient evidence (inputs absent) | Full trade-entry slice reruns at 20 signal checkpoints not run. |
| DI-04 | Static scan for future-reaching constructs | ran | Scanned every registered strategy implementation; no shift(-n), bfill, centred window or future public access found. Ichimoku displaces backwards. |
| DI-05 | Fill-price reachability | ran | Inspected queued next-open fills and gap liquidation handling; existing gap fixtures passed. |
| DI-06 | Higher-timeframe resample and bin-edge leakage | skipped (applicability) | Registered defaults consume one OHLCV timeframe; no higher-timeframe resampler. |
| DI-07 | External series as-of alignment with staleness cutoff | skipped (applicability) | Registered defaults use OHLCV only; trigger explicitly refuses funding-dependent conditions. |
| DI-08 | Outcome-resolution lag | skipped (applicability) | Registered defaults have no learned weights or outcome-resolution ledger. |
| DI-09 | Warm-up adequacy (recursive convergence) | insufficient evidence (inputs absent) | No >=5000-candle startup-convergence benchmark per recursive signal measured. |
| DI-10 | Burn-in discard | ran | Inspected engine burn-in: no decisions before warmup, but native metrics include flat startup. Comparison must trim to a common scoring start. |
| DI-11 | Bar-contract validation | ran | Inspected validate_bar_arrays and CsvLoader bar contract; validation tests in engine suite passed. |
| DI-12 | Gap policy and cadence refusal | ran | Inspected simulation cadence refusal in validate_bar_arrays. No gap repair was performed. |
| DI-13 | Tick-vs-candle gap classification (and gap sensitivity) | insufficient evidence (inputs absent) | No tick-classified gap runs with Wilson intervals provided. |
| DI-14 | Cross-granularity consistency | insufficient evidence (inputs absent) | No matched fine/coarse granularity audit executed here. |
| DI-15 | Resample completeness accounting | insufficient evidence (inputs absent) | No per-bar minute-coverage column evaluated. |
| DI-16 | Outlier / bad-tick filter | insufficient evidence (inputs absent) | No quote/tick outlier sensitivity data. |
| DI-17 | Second-source data cross-check | insufficient evidence (inputs absent) | No second-source comparison dataset evaluated. |
| DI-18 | Unit and sign alignment | ran | Inspected signal, time, exposure and cost units. RR-01 identifies volatility annualization defect. |
| DI-19 | Point-in-time universe (survivorship) | skipped (applicability) | Individual fixed-asset runs, no portfolio-universe selection claim. |
| DI-20 | Terminal-value (delisting) treatment | skipped (applicability) | No delisting event series or delisting return claim in selected assets. |
| DI-21 | Point-in-time data and revisions | insufficient evidence (inputs absent) | No received-at/as-of revision ledger for cached bars. |
| DI-22 | Corporate actions and roll adjustment | skipped (applicability) | No corporate actions, redenomination or futures roll series used. |
| DI-23 | Timezone, session and bar-boundary pin | ran | Inspected UTC epoch-seconds contract and interval constants; all crypto bars use 365-day annualization. |
| DI-24 | Cross-series synchronisation | skipped (applicability) | Individual single-series strategies; pairs use a separate runner and are outside REGISTRY. |
| DI-25 | Gross-vs-net shadow book | ran | Inspected zero-cost shadow book; existing short/long resize and isolated-gap fixtures passed. |
| DI-26 | Buy-and-hold identity (known answer) | ran | Existing zero-cost buy-and-hold identity fixtures passed in engine suite. |
| DI-27 | Equity reconciliation | ran | Inspected spot/perp book valuation and tested isolated collateral behavior. Close-marked equity is clamped after liquidation; this is no intrabar-equity proof. |
| DI-28 | Lot matching consistency | skipped (applicability) | Exposure-target strategies use one position; grid exposure is not ladder-grid lot matching. |
| DI-29 | Mechanism sign, symmetry and exit capture | ran | Existing strategy fixtures passed for crossover, momentum, reversions, breakout, regimes, sizing, triggers and textbook mechanisms. |
| DI-30 | Null-data (random-walk) canary | insufficient evidence (inputs absent) | No all-registry random-walk null calibration executed; a single random Sharpe is not itself proof of leakage. |
| DI-31 | Synthetic ground-truth environment | insufficient evidence (inputs absent) | No planted-edge/null environment run for every registered strategy. |
| DI-32 | Cross-implementation parity (ported economics) | skipped (applicability) | No paired economic port in REGISTRY; GridLong is not the extension resting-order ladder. |
| DI-33 | Cross-engine differential validation | gap | No independent second engine configured for these 34 strategies. |
| DI-34 | Input and config hardening | ran | EngineConfig validates again at run entry. Existing mutation and nonfinite-cost fixtures passed. Does not prove all nondefault strategy constructor inputs valid. |
| OV-01 | Protocol grade | ran | Protocol identified: fixed-rule historical chronological split. Label exploratory temporal comparison, below walk-forward/CPCV. |
| OV-02 | Single chronological split (holdout) | insufficient evidence (inputs absent) | Paired result rows and exact heldout observation/trade counts pending parent execution; minimum method asks >=1000 observations. |
| OV-03 | Split-position regime audit | insufficient evidence (inputs absent) | Train/test regime content not measured in this sub-audit. |
| OV-04 | IS-rank vs OOS-rank correlation | insufficient evidence (inputs absent) | IS/OOS rank vectors not yet supplied. |
| OV-05 | Walk-forward (anchored or rolling) | insufficient evidence (inputs absent) | No multiwindow walk-forward runs performed in this sub-audit. |
| OV-06 | Window length and refit cadence on a common test span | skipped (applicability) | No refit cadence or fitted window search in fixed default comparison. |
| OV-07 | Selection rule vs random baseline and oracle | skipped (applicability) | No walk-forward candidate-selection rule run. |
| OV-08 | Plain k-fold admissibility | skipped (applicability) | No shuffled/plain k-fold used by proposed chronological comparison. |
| OV-09 | Purged k-fold CV | insufficient evidence (inputs absent) | No purged-fold runs in paired protocol. |
| OV-10 | Purge and embargo width audit | insufficient evidence (inputs absent) | No fold-label interval purge/embargo audit for paired protocol. |
| OV-11 | Combinatorial purged CV (CPCV) | insufficient evidence (inputs absent) | No new CPCV results produced for both copies. |
| OV-12 | CPCV path-count and independence check | insufficient evidence (inputs absent) | No new common usable block/path distribution produced. |
| OV-13 | Warm-up usable-block accounting | insufficient evidence (inputs absent) | No CPCV warmup/block counts produced; paired runner must use common scored span. |
| OV-14 | Block isolation and return stitching | insufficient evidence (inputs absent) | Paired runner final implementation not reviewed here; fresh instances and return stitching need checking. |
| OV-15 | Fit-provenance check on "fixed-parameter" claims | ran | Defaults and cached histories predate experiment and have been examined; fixed parameters do not make the last 30% historically untouched. |
| OV-16 | Nested CV | skipped (applicability) | No inner hyperparameter selection performed. |
| OV-17 | Validation-pipeline null calibration | insufficient evidence (inputs absent) | No validation false-positive calibration run. |
| OV-18 | Predeclared-configuration holdout | gap | Pre-discovery configuration/data freeze cannot be reconstructed from an already researched cache. |
| OV-19 | Holdout window integrity | ran | Historical cache cannot establish post-discovery holdout; do not call it fresh out-of-sample validation. |
| OV-20 | Forward test / paper trading (with ledger existence check) | gap | No new prospective per-strategy ledger collected by this offline audit. |
| OV-21 | Live-vs-backtest performance tracking (promotion gate) | gap | No matched live fill ledger for all 34 strategies. |
| OV-22 | Cross-asset transfer, parameters frozen | insufficient evidence (inputs absent) | Cross-asset paired runs pending parent execution. |
| OV-23 | Cross-asset transfer, re-fit by the identical procedure | skipped (applicability) | Frozen default transfer only; no refitting procedure. |
| OV-24 | Generalisation-ladder rung label | insufficient evidence (inputs absent) | Historical comparison only; no new evidence ladder rung established. |
| OV-25 | Prequential evaluation of adaptive indicators | skipped (applicability) | No adaptive learned indicator weights in registered defaults. |
| ST-01 | Autocorrelation-corrected Sharpe annualisation (Lo 2002) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-02 | Studentized block-bootstrap Sharpe CI (Ledoit–Wolf) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-03 | Difference-of-two-Sharpes test | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-04 | Probabilistic Sharpe Ratio (PSR) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-05 | Minimum Track Record Length (MinTRL) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-06 | Deflated Sharpe Ratio (DSR) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-07 | Trial count and effective N | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-08 | Minimum Backtest Length (MinBTL) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-09 | Probability of Backtest Overfitting (PBO, CSCV) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-10 | White's Reality Check | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-11 | Hansen SPA test | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-12 | Romano–Wolf stepdown | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-13 | Bonferroni / Holm (FWER) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-14 | Benjamini–Hochberg / Benjamini–Yekutieli (FDR) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-15 | Harvey–Liu–Zhu t > 3.0 hurdle | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-16 | Harvey–Liu haircut Sharpe | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-17 | Stationary bootstrap CI (Politis–Romano, Politis–White block length) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-18 | Trade-level bootstrap of expectancy | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-19 | Monte Carlo permutation test (MCPT, with selection) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-20 | Random-entry / matched-exposure null | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-21 | Binomial test of hit rate vs base rate (with Wilson lower bound) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-22 | Effective sample size (overlapping-event de-duplication) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-23 | Evidence floor (minimum trades / blocks / paths / calls) | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-24 | Per-block sign test vs per-block base rate | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| ST-25 | Holdout-reuse count | insufficient evidence (inputs absent) | New paired return vectors, trade outcomes, null/bootstrap draws, full historical trial ledger or selection-aware statistics not provided to this sub-audit. No significance or promotion claim established. |
| RR-01 | Annualisation constant audit | ran | Engine ppy is correct; VolTargetTrend and GarchVolTarget sizing call daily-default volatility at every cadence (finding F1). |
| RR-02 | Metric implementation parity across code paths | ran | Inspected shared compute_metrics; paired runs must use this same convention. No independent engine evaluated. |
| RR-03 | Return-series construction | ran | Inspected simple_returns including supplied initial_equity and boundary costs. Existing boundary-cost test passed. |
| RR-04 | CAGR on short windows | ran | Engine always computes CAGR. Comparison must prioritize period return and duration and omit annual-growth claims for short windows. |
| RR-05 | Sortino ratio and downside-deviation convention | ran | Sortino uses RMS of min(excess,0) over every supplied return, annualized by sqrt(ppy). |
| RR-06 | Maximum drawdown with intrabar marking | gap | Leveraged native metric curve marks closes, not intrabar equity extremes; liquidations use high/low, but drawdown may understate intrabar risk. |
| RR-07 | Drawdown duration / time under water | insufficient evidence (inputs absent) | Native duration is peak-to-trough only; full underwater/recovery durations not computed. |
| RR-08 | Win rate and decided-trade definition | ran | trade_stats counts realized fills including resize_down, excludes open/resize_up/grid_entry. Label as fill outcome rate; it is not completed-position win rate. |
| RR-09 | Expectancy net of all costs | ran | Realized P&L allocates entry costs and settles borrow; existing fee/basis fixtures passed. Mean fill P&L is distinct from episode expectancy. |
| RR-10 | Kelly fraction from thin samples | skipped (applicability) | No Kelly sizing formula or claim in registered defaults. |
| RR-11 | Leverage growth bound (volatility drag) | insufficient evidence (inputs absent) | No geometric growth bound estimate and uncertainty for selected tier leverages. |
| RR-12 | Leverage invariance of Sharpe across tiers | insufficient evidence (inputs absent) | Tier matched-series output distributions pending; default tier signals are identical macd and leverage/cost effects must explain P&L. |
| RR-13 | Exposure / time-in-market definition | ran | exposure_fraction is mean absolute marked notional/equity, including leverage, not fraction of bars active. Use separate coverage name. |
| RR-14 | Strategy turnover and cost drag | ran | Native total_fees sums fee+slippage; borrow is separate. Report these definitions explicitly, do not call fees exchange-fee-only. |
| RR-15 | Risk of ruin | insufficient evidence (inputs absent) | No full-path bootstrap ruin simulation performed. |
| RR-16 | MAE / MFE excursion analysis | insufficient evidence (inputs absent) | No trade-window MAE/MFE table computed. |

## Per-strategy coverage

| Strategy | Class | Warmup bars | Finding |
| --- | --- | --- | --- |
| buy_and_hold | BuyAndHold | 0 | No source-supported performance defect identified |
| ma_crossover | MaCrossover | 50 | No source-supported performance defect identified |
| rsi | RsiMeanReversion | 15 | No source-supported performance defect identified |
| breakout | DonchianBreakout | 21 | No source-supported performance defect identified |
| macd | MacdCross | 53 | No source-supported performance defect identified |
| bb_reversion | BollingerReversion | 20 | No source-supported performance defect identified |
| bb_breakout | BollingerBreakout | 20 | No source-supported performance defect identified |
| keltner | KeltnerBreakout | 61 | No source-supported performance defect identified |
| ts_momentum | TsMomentum | 61 | No source-supported performance defect identified |
| stochastic | StochasticOversold | 18 | No source-supported performance defect identified |
| vwap_reversion | VwapReversion | 20 | No source-supported performance defect identified |
| obv_trend | ObvTrend | 22 | No source-supported performance defect identified |
| zscore | ZScoreReversion | 20 | No source-supported performance defect identified |
| sma_regime | Sma200Regime | 200 | No source-supported performance defect identified |
| voltarget | VolTargetTrend | 101 | F1 |
| grid | GridLong | 50 | No source-supported performance defect identified |
| dual_momentum | DualMomentum | 13 | No source-supported performance defect identified |
| adx_trend | AdxFilteredTrend | 43 | No source-supported performance defect identified |
| ma_ribbon | MaRibbon | 50 | No source-supported performance defect identified |
| ichimoku | IchimokuCloud | 78 | No source-supported performance defect identified |
| ou_reversion | OuHalfLifeReversion | 251 | No source-supported performance defect identified |
| hurst_switch | HurstRegimeSwitch | 251 | No source-supported performance defect identified |
| vol_regime | VolRegimeSwitch | 251 | No source-supported performance defect identified |
| atr_sized | AtrSizedTrend | 101 | No source-supported performance defect identified |
| garch_voltarget | GarchVolTarget | 101 | F1 |
| dca | DollarCostAveraging | 0 | No source-supported performance defect identified |
| ema_crossover | EmaCrossover | 200 | No source-supported performance defect identified |
| ppo | PpoCross | 37 | No source-supported performance defect identified |
| fib_retracement | FibRetracement | 61 | No source-supported performance defect identified |
| swing_confluence | SwingConfluence | 50 | No source-supported performance defect identified |
| lev_low | LevLow | 53 | No source-supported performance defect identified |
| lev_medium | LevMedium | 53 | No source-supported performance defect identified |
| lev_high | LevHigh | 53 | No source-supported performance defect identified |
| trigger_trade | TriggerTrade | 120 | No source-supported performance defect identified |

## Interpretation

The directional label is the next bar open-to-close sign. Flat exposures abstain; give calls, hits, coverage and same-sample base rate. All registered defaults are long/flat, so raw directional accuracy often equals the long base rate on the active bars. This does not establish forecasting edge. Native engine win_rate counts realized fills, including partial reductions. Close-marked maximum drawdown omits intrabar equity extrema. Annualized CAGR on short windows is not a reliable headline. Do not describe unrun CPCV, bootstrap, PBO or prospective evidence as passed.

No published historical figures were invalidated in this sub-audit; existing reports were not recomputed. F1 can change hourly candidate P&L without changing the long/flat direction of either signal.

Canonical loop and severity rules: /Users/mitch/.claude/skill-consolidation/convergence-and-severity.md. Promotion contract: /Users/mitch/.claude/skill-consolidation/champion-challenger.md.
