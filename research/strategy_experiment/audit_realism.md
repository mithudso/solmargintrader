# DSO realism, robustness and provenance audit

Research output, not investment advice; simulation only.

Version: 1
Delta: initial collection before candidate writes.

## Scope

All 34 registered default strategies were inspected with their cards, indicators and common engine. This is a defect-track audit. No parameter tuning ran. No unchanged strategy is represented as improved. Source and card defects were sent to the parent before candidate changes.

## Findings

| ID | Severity | Evidence | Finding and prescribed fix |
|---|---|---|---|
| R1 | Critical | backtester/core/strategies/signals.py:394, backtester/core/strategies/advanced.py:465, backtester/core/indicators.py:327, backtester/core/indicators.py:439 | Annualized volatility target sizing uses 365-bars/year default on every interval. Identical hourly/daily price paths allocate identical exposure. Uncapped hourly allocation is too large by sqrt(24). Infer annualization from visible timestamp step and pass explicit periods_per_year into realized/EWMA volatility helpers, with invalid-spacing refusal. Preserve original snapshots. Add daily/hourly known-answer test and causal prefix test. |
| R2 | High | backtester/strategy_cards/voltarget.md:100, backtester/strategy_cards/garch_vol_forecast.md:96 | Two cards describe hourly full-exposure degeneracy as not a bug. R1 shows the hourly volatility convention was wrong, so archive interpretation is unsupported. Candidate cards must label old hourly metrics as archived under daily volatility scaling, remove not-a-bug causal claim and point to rerun result. Keep original snapshot immutable. |

The reproduction uses the repository volatility helpers and `periods_per_year`, not a new formula. At target_vol=0.01, the unchanged voltarget returns 0.03742067023570752 on both daily and hourly timestamps; correct hourly size is 0.007638462325869778. The EWMA strategy returns 0.03775842443848675 on both; correct hourly size is 0.007707406113810582. These are hand-constructed correctness checks, not market performance measurements.

## Coverage and limitations

Registry keys: buy_and_hold, ma_crossover, rsi, breakout, macd, bb_reversion, bb_breakout, keltner, ts_momentum, stochastic, vwap_reversion, obv_trend, zscore, sma_regime, voltarget, grid, dual_momentum, adx_trend, ma_ribbon, ichimoku, ou_reversion, hurst_switch, vol_regime, atr_sized, garch_voltarget, dca, ema_crossover, ppo, fib_retracement, swing_confluence, lev_low, lev_medium, lev_high, trigger_trade.

173 pass rows follow. `ran` describes only the stated check, including explicitly static checks. It never certifies unexecuted numerical tests. Missing numerical studies remain insufficient evidence. Live execution inputs are gaps. This bundle cannot establish CLEAN or convergence.

| Pass | Method | Status | Evidence or reason |
|---|---|---|---|
| RB-01 | One-at-a-time parameter perturbation (±10%) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-02 | Parameter-surface plateau vs spike | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-03 | Protocol-knob sweep | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-04 | Structural-fragility test | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-05 | Start-date / start-bar sensitivity | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-06 | Sub-period and block stability | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-07 | Monte Carlo trade reshuffle (drawdown) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-08 | Trade-removal jackknife | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-09 | Variance test (degraded resample) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-10 | Randomised exit-parameter Monte Carlo | skipped (applicability) | Default registry has no separate tunable exit-parameter Monte Carlo protocol; specialized exit randomization is not a justified candidate edit. |
| RB-11 | Price noise injection | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-12 | Calibrated synthetic-process test | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-13 | Bar-start offset | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-14 | Bar-type sensitivity (time, tick, volume, dollar bars) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-15 | Sampling-frequency sweep | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-16 | Bar-resolution fill fidelity | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-17 | Cross-venue / data-feed sensitivity | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-18 | Exposure correlation and active-bar agreement | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-19 | Summary-scalar collision screen | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-20 | Effective number of bets / independent trials | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-21 | Component ablation | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RB-22 | Degrees-of-freedom count | ran | Reviewed constructor parameter counts and composed leverage wrappers for all 34 keys. Defaults are frozen; no parameter search is authorized by this experiment. |
| RB-23 | Inverted / time-reversed series | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-01 | Cost-path single application (with non-zero-cost reconciliation test) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-02 | Fee-schedule correctness | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-03 | Order-type and fee-side consistency | ran | Engine schedules target(t) to next-open market fills. CostConfig fee_bps / perp_base_fee_bps are explicit scenario assumptions; no maker fee claimed. |
| CE-04 | Fee unit and basis audit | ran | Reviewed engine.py::_Book._costs_on and perps borrow path: bps divide by 10,000 and notional basis are explicit. No unit defect found by static inspection. |
| CE-05 | Rebalance / resize turnover | ran | Reviewed engine.py::_Book.resize: charges on absolute delta_notional, releases proportional entry costs and borrow; no candidate edit indicated by static inspection. |
| CE-06 | Order-book walk vs modelled slippage | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-07 | Spread-based slippage | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-08 | Spread estimation from bars (Corwin–Schultz, Roll) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-09 | Volatility-scaled slippage | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-10 | Square-root market impact | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-11 | Temporary vs permanent impact (Almgren–Chriss) | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-12 | Volume-participation cap | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-13 | Capacity curve and break-even size | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-14 | Coin liquidity screen | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-15 | Break-even cost | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-16 | Cost sensitivity sweep | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-17 | Turnover vs gross edge and required win rate | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-18 | Turnover-banded net spread | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-19 | Oracle (perfect-foresight) net ceiling | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-20 | Expected-move vs cost gate | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-21 | Holding-period fee/carry hinge | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-22 | Leverage-multiplied fee drag | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-23 | Time-varying cost audit | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-24 | Funding vs borrow model fit | ran | Reviewed perps.py and leverage.py: Jupiter borrow is nonnegative, not signed CEX funding. Correct model class; live calibration remains a gap. |
| CE-25 | Accrual timing | ran | Reviewed engine loop: opens precede current-bar accrual; closes at open release before new interval; hpb derives EngineConfig interval. Static inspection only. |
| CE-26 | Historical signed-funding replay | skipped (applicability) | Tier strategies model Jupiter borrow rather than signed periodic CEX funding; unlevered strategies have no funding leg. |
| CE-27 | Liquidation formula and maintenance margin per venue and asset | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-28 | Liquidation drift | ran | Reviewed engine.py: liquidation price recomputed after borrow accrual each held bar, and before pending open fills on gaps. Static inspection only. |
| CE-29 | Intrabar liquidation and gap fill | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-30 | Trigger-price basis (mark vs last) | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-31 | Venue liquidation process | ran | leverage.py explicitly labels 50-bps forced-close penalty an assumption; tier costs forfeit collateral. Not certified as current venue rules. |
| CE-32 | Stop-to-liquidation distance | skipped (applicability) | Default leverage-tier MACD has no stop ATR parameter; unlevered strategies have no liquidation distance. |
| CE-33 | Flat-chart survival time | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-34 | Fill-delay sensitivity | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-35 | Request-to-fill and quote-to-fill drift | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-36 | Intrabar path ambiguity convention | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-37 | Limit-order fill realism | skipped (applicability) | Registered exposure strategies submit market targets, not passive limit orders. |
| CE-38 | Queue position and adverse selection | skipped (applicability) | Registered exposure strategies submit market targets, not passive limit orders. |
| CE-39 | Post-fill markout | skipped (applicability) | Registered exposure strategies submit market targets, not passive limit orders. |
| CE-40 | Fill-averaging (liquidity) test | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| CE-41 | Implementation shortfall (with unfilled remainder) | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-42 | Live realised-vs-modelled slippage tracking | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-43 | Tick, lot and minimum-notional rounding | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-44 | Fixed on-chain cost per transaction | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| CE-45 | MEV and sandwich exposure | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| RA-01 | Buy-and-hold on the same bars after costs | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-02 | Exposure- and leverage-matched benchmark | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-03 | Alpha/beta regression with HAC errors | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-04 | Market-timing / convexity regression (Treynor–Mazuy, Henriksson–Merton) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-05 | Upside vs downside beta | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-06 | Conditional alpha/beta on lagged state (Ferson–Schadt) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-07 | Rolling and sub-period alpha/beta stability | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-08 | Crypto factor attribution (CMKT, CSMB, CMOM) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-09 | Own time-series-momentum loading | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-10 | Carry/funding attribution | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-11 | Volatility-change exposure | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-12 | Performance by causal trend/range labels | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-13 | Performance by volatility regime | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-14 | Performance by bull/bear label | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-15 | HMM / Markov-switching regime performance (filtered only) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-16 | Gated vs always-on A/B (with switching costs) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-17 | Transition-slice performance | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-18 | Regime-label stability and switching cost | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-19 | Regime-definition sensitivity | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-20 | Regime coverage (independent episodes) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-21 | Documented failure mode vs payoff mathematics | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-22 | Historical crash and liquidation-cascade replay | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-23 | Hypothetical shock scenarios | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-24 | Reverse stress test | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-25 | Crisis-window and tail correlation | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-26 | Cross-asset parameter stability | skipped (applicability) | Experiment freezes original default parameters across assets; there are no per-asset parameter selections to compare. |
| RA-27 | Matched-window cross-asset comparison | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-28 | Dataset rank swing | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-29 | Dataset base rate | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-30 | Effective independent assets | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-31 | Spanning / incremental-Sharpe test (GRS) | skipped (applicability) | Registry experiment does not construct an existing portfolio/book of sleeves. |
| RA-32 | With/without-sleeve system comparison | skipped (applicability) | Registry experiment does not construct a portfolio/book of sleeves. |
| RA-33 | P&L by side and trade type | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-34 | Calendar and session slices | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RA-35 | Edge by market-cap and liquidity bucket | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-01 | Hit rate vs base rate and naive forecasters | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-02 | Dependence-robust hit-rate inference | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-03 | Pesaran–Timmermann directional test | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-04 | 3-class confusion matrix (UP / DOWN / FLAT) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-05 | Selective accuracy vs coverage | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-06 | Brier score / Brier skill score vs climatology | skipped (applicability) | Target exposure is not a forecast probability; no score-to-probability mapping is claimed. |
| IF-07 | Reliability diagram (bucketed up-rate vs level) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-08 | Monotonicity across score buckets | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-09 | Recalibration holdout (Platt, isotonic, temperature) | skipped (applicability) | Target exposure is not a forecast probability; no calibrator is claimed. |
| IF-10 | IC information ratio and positive-IC share | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-11 | IC / gross-edge decay across horizons | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-12 | Signal half-life | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-13 | Quantile / decile forward-return spread | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-14 | Signal turnover, flip rate and autocorrelation | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-15 | Granger non-causality test | skipped (applicability) | Targets are strategies, not standalone cross-series lead indicators. |
| IF-16 | Lead-lag cross-correlation profile | skipped (applicability) | Targets are strategies, not standalone cross-series lead indicators. |
| IF-17 | Label–execution alignment | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-18 | Label scheme choice (fixed horizon vs triple barrier) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-19 | FLAT band and tie handling | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-20 | Gate / filter value test | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-21 | Live-vs-backtest signal replay | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| IF-22 | Reference-implementation parity (TA-Lib / TradingView) | skipped (applicability) | Targets are strategies; independent indicator-reference parity series are outside this input. |
| IF-23 | Saturation / clipping fraction per component | skipped (applicability) | Targets are strategies, not per-component probabilistic indicator scores. |
| IF-24 | Undefined / zero / coverage audit | skipped (applicability) | Targets are strategies, not standalone indicator score arrays. |
| IF-25 | Pairwise score correlation and sign agreement | skipped (applicability) | Targets are strategies; strategy exposure redundancy belongs to RB-18. |
| IF-26 | Sign-stability of component skill (inversion legitimacy) | skipped (applicability) | Registry strategies use no adaptive learned weights or learned inversion. |
| IF-27 | Online hit-rate learner audit | skipped (applicability) | Registry strategies use no online hit-rate learners. |
| IF-28 | Diebold–Mariano test (HLN correction) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| IF-29 | Ensemble vs benchmark composites | skipped (applicability) | No composite configuration or learned ensemble is registered as a separate experiment target. |
| IF-30 | Hit rate by data-quality bucket | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-01 | Deterministic rerun diff | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-02 | Seed disclosure and independent streams | skipped (applicability) | Default strategy signal functions use no random sampling; deterministic seed=0 engine setting is recorded by runner. |
| RP-03 | Seed-sensitivity distribution | skipped (applicability) | Default strategy signal functions use no random sampling. |
| RP-04 | Nondeterminism source scan | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-05 | Config recorded beside result (config hash) | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-06 | Data version hash | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-07 | Environment pinning | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-08 | Reproduce-command execution | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-09 | Run ledger and stored intermediates | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-10 | Figure-to-result tracing | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-11 | Recompute derived figures | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-12 | Figure-census floor | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-13 | Stale-figure propagation | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-14 | Claim ledger | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-15 | Card defaults vs code defaults | ran | 43-test strategy-card suite PASS, including runtime default equality. Independent AST census also found 34 exact default matches. |
| RP-16 | Code parameter absent from card | ran | 43-test strategy-card suite PASS; card parameter dictionaries equal constructor default dictionaries for all 34 keys. |
| RP-17 | Warm-up and family declared vs instance | ran | 43-test strategy-card suite PASS: warmup and FAMILY exactly match instances for all registry cards. |
| RP-18 | Registry ↔ card bijection and duplicate keys | ran | Registry 34 keys, executable card directory 34 cards, bijection and duplicate-key checks pass. |
| RP-19 | Preset vs sweep-grid agreement | ran | 43-test strategy-card suite PASS including every sweep horizon preset equality. |
| RP-20 | Card schema and status contract | ran | 43-test strategy-card suite PASS including typed schema/status/runner validation. |
| RP-21 | Rating within scale, no top tier | ran | 43-test strategy-card suite PASS: no high rating exists in scale and each rating valid. |
| RP-22 | Rating body justification | ran | 43-test strategy-card suite PASS: every body states likelihood and basis. |
| RP-23 | Rating vs evidence basis | ran | 43-test strategy-card suite PASS: measured-oos basis only on measured status. |
| RP-24 | Rating distribution vs base rate | ran | 43-test strategy-card suite PASS: moderate-rating distribution within repository threshold. |
| RP-25 | Mechanism-match check | ran | Confirmed candidate-relevant mismatch: hourly voltarget/garch target sizing uses daily default annualization; old hourly card results describe defective implementation. Finding R1. |
| RP-26 | Overclaim-language scan | ran | Confirmed overclaim in two cards: hourly full-exposure degeneracy called not a bug despite default daily annualization. Finding R2. |
| RP-27 | Trial-count disclosure in the claim | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-28 | OOS-label integrity | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-29 | Mutation testing of the suite | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-30 | Tautological-test detection | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-31 | Metamorphic and property tests | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-32 | Independent-implementation / replay parity | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-33 | Assertion-strength review of smoke tests | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-34 | Research log of every configuration tried | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-35 | Duplicate-run dedupe in the ledger | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-36 | Hypothesis pre-registration | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-37 | Rule completeness / blind re-implementation | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-38 | Independent replication under altered specification | insufficient evidence (inputs absent) | Required executed experiment or artifact is not part of this audit bundle. Parent paired evaluation may supply a bounded subset; no result inferred from code or historical prose. |
| RP-39 | Live-vs-backtest divergence checklist | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |
| RP-40 | CUSUM drift monitor | gap | No venue-verified live fill, orderbook or transaction ledger is supplied to this frozen offline registry experiment. |

## Verification

`/Users/mitch/.venvs/soltui/bin/python -m unittest backtester.tests.test_strategy_cards -v` completed with exit 0: 43 tests passed. The first system-python attempt failed before tests because pandas is absent. No dependencies were installed.

The 43-test suite verifies card schema, registry bijection, exact defaults, warmup, family, sweep presets and bounded ratings. An independent AST census also found 34 registry keys and 34 executable cards with no default mismatch.

## Interpretation

Directional accuracy can stay identical after R1 because the edit changes exposure size rather than its sign. Judge return, drawdown, fees and realized volatility separately. A higher hit rate alone does not establish profitability. The parent comparison must retain every strategy, zero-call denominators and failed cells.

## Exit

Findings: Critical 1 / High 1 / Medium 0 corroborated code-or-claim defects. Remaining empirical methods are unresolved. Parent owns fixes, paired evaluation, reruns and final convergence verdict.


## Auxiliary scope extension — v2

Delta: v1 to v2 adds explicitly separate executable mechanisms outside REGISTRY.

| Mechanism | Scope checked | Result |
|---|---|---|
| PeerSpreadReversion | Peer alignment, causal fit window, gate, entry/exit | No new corroborated defect. This trades one asset; it is not a two-leg neutral portfolio. |
| Ladder grid | Planned-index timing, lot matching, costs, carry, terminal close | No new corroborated defect. Touch fills, queue realism and carry-without-liquidation remain limitations. Extension economics parity remains a hard gate. |
| DCA safety-order bot | Next-open base orders, deferred safety/TP, close stops, terminal accounting | No new corroborated defect. Close-triggered stops and bar fill assumptions remain limitations. |
| Triangle replay | Quote eligibility, latency, book freshness, cycle accounting | Critical R4: future quote timestamps accepted. Candidate now refuses future and nonfinite timestamps. |
| Scorecard | Aggregate/control path, adaptive outcomes, forecast outputs; catalog census 46 score/gate components | Critical R3: primary one-bar forecast return labels disagreed with executable horizon labels. Candidate diagnostic corrected. Component-level data/reference gaps remain. |

### R3 — Executable forecast labels

`backtester/core/scorecard.py::forecast_stats` computed the main hit rate and one-bar net from close[t] to close[t+1]. Its own horizon[1] table used open[t+1] to close[t+1]. With closes [100,110,120], opens [100,120,130], and long calls, original accuracy is 100% and original one-bar net is +898.608 bps. Capturable next-open accuracy is 0% and net is −848.270 bps. The candidate now uses the executable next-open path for both summaries and reports the label basis. It adds an active-sample majority baseline.

The candidate preserves adaptive_counts' documented close-close indicator-learning target and identifies it separately. The `z_vs_coinflip` statistic retains its explicitly named descriptive fair-coin null. The report explicitly states that serial dependence and class imbalance are uncorrected; the value must not be called evidence of trading skill.

### R4 — Future quote refusal

`backtester/core/trianglesim.py:123` checked only quote age <= max_age. At replay time 100, quotes stamped 200 passed. A three-leg hand example executed one apparent profitable cycle from future quotes. Candidate `_usable` now requires finite quote time and 0 <= age <= max_age. Current timestamps remain accepted; stale, NaN and infinite timestamps refuse. Parsing API and the original snapshot remain unchanged.

### Additional verification

The original auxiliary test modules completed 140 tests with exit 0. A bounded scenario emitted the existing CAGR overflow warning. The independent cadence/runner review completed 13 tests with exit 0. The candidate auxiliary regression suite completed 4 tests with exit 0. These checks found that green baseline tests did not detect the two planted hand examples.

### Independent candidate and comparison review

The cadence correction derives annualization from visible regular timestamps, keeps daily sizing identical and refuses invalid cadence. The candidate daily/hourly and prefix checks pass. The paired registry runner uses executable next-open accuracy, explicit denominators, flat abstention, errors, content hashes and fresh split portfolios with causal prefix-primed signal state. Trade-event win rate is explicitly distinguished from independent round trips. Cache gaps must refuse or use a disclosed deterministic contiguous subset; silently bridging them is invalid.

This extension does not establish all-method convergence. Missing empirical studies, independent component replications, realistic venue fills and live histories remain unresolved. No CLEAN verdict is claimed.
