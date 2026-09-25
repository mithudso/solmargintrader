---
name: regime-detection-and-classification
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-1 re-expansion, CVS 4.85 (highest of the round)
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  How to tell which market regime you are in, and whether acting on that belief
  is worth anything. Covers what a "regime" is and the axes worth classifying
  (trend/range, volatility level and direction, liquidity); the detector families
  — threshold indicators (ADX, Bollinger bandwidth), statistical memory (Hurst,
  variance ratio), volatility models (realized vol, GARCH, MS-GARCH), latent-state
  models (Hamilton Markov-switching / HMM), and changepoint detection (CUSUM,
  Bayesian online) — with what each actually measures and where it fails; the
  LAG problem that is fatal to naive gating; how to evaluate a regime filter
  against a fixed-weight benchmark; and why a detector that classifies well can
  still lose money. Educational only — NOT financial advice.
keywords:
  - regime detection
  - market regime
  - regime switching
  - Hamilton Markov switching
  - hidden Markov model
  - HMM market states
  - Hurst exponent
  - variance ratio test
  - ADX
  - Bollinger bandwidth squeeze
  - realized volatility
  - GARCH
  - MS-GARCH
  - changepoint detection
  - CUSUM
  - Bayesian online changepoint
  - regime filter
  - strategy gating
  - lookahead bias
tags:
  - trading-and-investing
  - regime
  - risk
  - quantitative
  - time-series
---

# Regime Detection and Classification

> **Educational information only — NOT financial, investment, or tax advice.** Regime detection is a
> way to be wrong more expensively if you trust it too much. Every method here is **lagging** — it
> tells you a regime changed *after* it changed. Read §5 before you gate anything on one.

**Scope.** How to *identify* the regime. What to *do* about it — gating, overlays, allocation — is
`references/strategy-failure-modes-and-synergy.md` §6. This spoke exists because that section leans on
regime classification as a mechanism and never explains how the mechanism works or how badly it fails.

| For… | Go to |
|---|---|
| What to do with a regime call (gating, convex overlay, vol targeting, fixed-weight) | `references/strategy-failure-modes-and-synergy.md` §6 |
| Which strategies break in which regime, and their observable signatures | same file, §2–§4 |
| Indicator definitions and formulas (ADX, Bollinger, ATR) | `references/technical-analysis.md` |
| Backtesting methodology, walk-forward, PBO, multiple testing | `references/trading-strategies-and-styles.md` §5 |
| ML-specific pitfalls (leakage, purged CV, deflated Sharpe) | `references/ai-and-ml-for-trading.md` §3.2; `references/ml-backtesting-pitfalls-and-production-systems.md` §8 |
| Volatility-scaled position sizing as an alternative to classification | `references/trading-risk-management.md` §2 |

## Contents

1. What a regime is, and which axes are worth classifying
2. Threshold indicators — ADX, Bollinger bandwidth
3. Statistical memory — Hurst, variance ratio
4. Volatility models — realized vol, GARCH, MS-GARCH
5. Latent-state models — Hamilton Markov-switching and HMMs
6. Changepoint detection — CUSUM, Bayesian online
7. The lag problem (the one that decides whether any of this pays)
8. Evaluating a regime filter honestly
9. Anti-patterns

---

## 1. What a regime is, and which axes are worth classifying

A **regime** is a period during which the statistical behaviour of returns is approximately stable —
and *different* from the adjacent periods. The useful framing is not "bull vs bear" but **which
statistical property changed**, because that is what determines which strategy breaks.

Four axes, matching the taxonomy in `strategy-failure-modes-and-synergy.md` §2:

| Axis | Question | Who cares |
|---|---|---|
| **Trend ↔ range** | Does the series have directional persistence, or does it revert? | Trend vs grid/mean-reversion |
| **Volatility level** | How big are the moves right now? | Every fixed-parameter stop, grid spacing, position size |
| **Volatility direction** | Is vol expanding or contracting? | Breakout wants expansion; carry/grid want contraction |
| **Liquidity / participation** | Is there depth and volume? | Execution-sensitive strategies; also every fill assumption |

**The axes are not independent, and conflating them is the most common modelling error.** A
high-volatility market can be strongly trending *or* violently mean-reverting; those demand opposite
strategies. A detector that outputs one label ("volatile") has thrown away the distinction that
mattered.

**Regimes are a modelling convenience, not a physical fact.** There is no ground-truth label. You are
imposing a discrete structure on a continuous process because discrete structure is actionable. Judge
the imposition by whether it improves decisions (§8), never by how well it fits.

## 2. Threshold indicators — ADX, Bollinger bandwidth

The cheapest family: compute an indicator, apply a threshold.

**ADX (Average Directional Index)** — measures **trend strength, not direction**. Convention: **ADX
above 25 = trending** (directional strategies have statistical support); **below 25 = ranging**
(breakout and trend strategies typically fail).

Two properties that matter more than the threshold:

- **It is non-directional.** ADX 40 tells you a strong trend exists, not which way. Pair it with a
  directional signal or it cannot generate a position.
- **It is lagging and smoothed twice** (directional movement → DI → smoothed into ADX). ADX peaks at
  or *after* trend exhaustion. High ADX is as consistent with "the move is ending" as "the move is
  strong" — which is precisely the trap in §7.

**Bollinger bandwidth** — `(upper − lower) / middle`. A **squeeze** (bandwidth at a multi-period low)
signals volatility contraction, which historically precedes expansion. It says **nothing about
direction**, and the expansion can resolve either way — trading the squeeze directionally is a coin
flip with extra steps.

**The threshold is the weak point.** 25 for ADX is a **convention, not a law** — it is asset- and
timeframe-dependent, and treating it as universal is how a filter that worked in backtest fails live.
Calibrate against your own data, and expect the calibration itself to be a fitted parameter you must
account for in §8.

## 3. Statistical memory — Hurst, variance ratio

More principled: measure whether the series has memory.

**Hurst exponent (H)** — long-term memory of a series:

| H | Interpretation | Favoured strategy |
|---|---|---|
| **> 0.5** | Trending / persistent | Momentum, trend-following |
| **≈ 0.5** | Random walk | Neither — no exploitable structure |
| **< 0.5** | Mean-reverting / anti-persistent | Counter-trend, grid, pairs |

A documented rule-based application: take trend-following signals only when **H > 0.55**, mean-reversion
only when **H < 0.45**, and in the transitional band **0.45 ≤ H ≤ 0.55** reduce size or stand aside.

**Hurst and ADX answer different questions and neither replaces the other.** A useful two-layer split
treats **Hurst as the strategic compass** (which *class* of strategy has structural support) and **ADX
as the tactical signal** (is a trend strong enough to act on *now*). The highest-confidence state is
both agreeing — high H and high ADX.

**Caveats that get skipped:** H is **estimator-dependent** (R/S, DFA and wavelet methods disagree on
the same series), **window-length-dependent**, and **unstable on short samples**. Reporting "H = 0.58"
without the estimator and window is not a measurement.

**Variance ratio test** — the more statistically honest sibling. Under a random walk, variance scales
linearly with the sampling interval; VR compares `Var(k-period return) / (k · Var(1-period return))`.
VR > 1 indicates persistence, VR < 1 reversion, and it comes with a **significance test** — so you can
ask whether the deviation from random walk is distinguishable from noise, which Hurst alone does not
tell you.

## 4. Volatility models — realized vol, GARCH, MS-GARCH

Volatility is the **most predictable** thing about returns, because it **clusters** — large moves
follow large moves. That makes the volatility axis the most reliable regime axis, and it is why
volatility targeting (`trading-risk-management.md`) often beats regime *classification* outright:
you get the benefit without ever making a discrete call.

- **Realized volatility** — rolling standard deviation of returns. Simple, robust, lagging by
  construction (a window average cannot react faster than its window).
- **GARCH** — models conditional variance with persistence and mean reversion in vol itself.
  Forecasts vol, not direction.
- **MS-GARCH (Markov-switching GARCH)** — lets the *volatility dynamics themselves* switch between
  states, combining §5's latent-state machinery with a volatility model.

**What none of them do is tell you direction.** A correct high-vol forecast is compatible with a
crash, a melt-up, or a violent range. Sizing on volatility is well-founded; *positioning* on it is not.

## 5. Latent-state models — Hamilton Markov-switching and HMMs

The formal treatment. A **regime-switching (Markov-switching) model** is a case of a **hidden Markov
model**: the regime is an unobserved state, transitions follow a first-order Markov chain, and you
infer the state from observable data.

**Hamilton (1989)** is the origin — a Markov-switching model that endogenously identified US business
cycle phases from GNP data, which opened the door to widespread use of regime-switching methods across
macroeconomics and finance. In finance the technique is prized for capturing the cyclical behaviour of
markets, and HMMs have become a standard tool for latent-state modelling of financial time series,
from volatility forecasting to equity strategies. In practice the applications concentrate on **shifts
in volatility regimes** rather than direction.

The framing that makes it worth the complexity: it infers **a market condition you cannot observe
directly** from price and volatility you can. That matters because many trading rules fail not because
their logic is wrong but because the environment changed underneath them.

**Where it bites:**

- **You choose the number of states.** Two-state (calm/turbulent) is the common default and is a
  modelling assumption, not a discovery. More states fit better and generalise worse.
- **Labels are not meaningful.** "State 1" has no inherent identity; you interpret it after the fact,
  which invites reading the story you wanted.
- **Fitting is easy to do with lookahead.** Estimating on the full sample then reporting in-sample
  regime classifications is not a forecast — it is a description. Only **online / filtered** estimates
  (state inferred using data up to *t* alone) are tradeable.
- **Constant transition probabilities are a strong assumption.** Time-varying transition probability
  extensions exist precisely because the constant-probability assumption is often wrong.

## 6. Changepoint detection — CUSUM, Bayesian online

A different question: not "which state am I in" but **"did something just change?"**

- **CUSUM** — accumulates deviations from a reference and signals when the cumulative sum breaches a
  threshold. Cheap, online, one tunable (the threshold) trading detection speed against false alarms.
- **Bayesian online changepoint detection** — maintains a distribution over *run length* (time since
  the last change) and updates it per observation. Gives a probability rather than a binary flag,
  which is more honest and directly usable for position sizing.

**Changepoint detection is the better framing for the transition problem** (§7), because transitions —
not the regimes themselves — are where the damage concentrates. A classifier tells you where you are;
a changepoint detector tells you the ground is moving.

## 7. The lag problem

**This is the section that decides whether any of the above pays for itself.**

Every method here is lagging. ADX is doubly smoothed. Hurst needs a window. Realized vol is a window
average. HMM filtering needs observations to update its posterior. Changepoint detection needs enough
post-change evidence to clear its threshold. **There is no exception in this document.**

The consequence: **a regime filter reduces your exposure to the wrong regime; it does not protect you
from the transition into it.** The loss you most wanted to avoid — the breakout that kills the grid,
the reversal that gives back the trend's gains — happens *before* the detector fires.

This produces the fundamental trade-off, and it has no clean solution:

- **Faster detector** (shorter window, looser threshold) → earlier warning, more false positives, more
  whipsaw, more cost from switching.
- **Slower detector** → fewer false alarms, later warning, more of the transition loss taken.

Both failure modes cost money, in different regimes. Tuning the detector is itself a fitted decision
that must be validated out-of-sample (§8).

**The practical implication is uncomfortable and worth stating plainly:** because the transition loss
is largely unavoidable, a **fixed-weight allocation across payoff shapes** — which never switches, so
never switches wrong — is often the more defensible baseline. That is why
`strategy-failure-modes-and-synergy.md` §6.4 makes fixed-weight the benchmark any gated system must
beat, not a fallback.

## 8. Evaluating a regime filter honestly

**A detector that classifies well can still lose money.** Classification accuracy is not the objective;
decision quality is. Evaluate accordingly.

1. **Benchmark against the un-gated system.** Run the strategy with the filter and without. If gating
   does not beat the fixed-weight or always-on version, the classifier is adding cost and complexity,
   not value. This single comparison invalidates most regime filters.
2. **Use only online/filtered state estimates.** A regime label computed with any future information —
   including a model fitted on the whole sample — is lookahead. This is the most common fatal error in
   published regime work.
3. **Count the degrees of freedom.** Detector choice, window length, threshold, number of states, plus
   every strategy parameter. They multiply. Adjust expectations for multiple testing
   (`trading-strategies-and-styles.md` §5; `ml-backtesting-pitfalls-and-production-systems.md` §8 on PBO and deflated Sharpe).
4. **Report performance sliced by regime AND by transition.** Aggregate statistics hide precisely where
   these systems fail. The transition slice is the whole question.
5. **Include switching costs.** Every regime change triggers reallocation: fees, slippage, and on-chain,
   priority fees plus failed-transaction waste. A filter that switches often can be right and still
   unprofitable.
6. **Test on the shapes that break each component**, not a random sample — see the shape-selected
   adversarial month set in `references/empirical-backtest-findings-log.md` §9.

## 9. Anti-patterns

1. **Fitting the regime model on the full sample and reporting in-sample labels.** Descriptive, not
   predictive. The single most common error.
2. **Treating threshold conventions as laws.** ADX 25 and Hurst 0.45/0.55 are starting points; they are
   asset- and timeframe-dependent, and the calibration is a fitted parameter.
3. **Reporting a Hurst exponent without the estimator and window.** R/S, DFA and wavelet methods
   disagree; the number alone is not a measurement.
4. **Collapsing the axes into one label.** "Volatile" does not distinguish a trending crash from a
   violent range — and those demand opposite strategies.
5. **Assuming the filter prevents the transition loss.** It reduces wrong-regime exposure; the turn
   still costs you (§7).
6. **Adding states to improve fit.** More states always fit better and generalise worse.
7. **Skipping the un-gated benchmark.** If you have not run it, you do not know the filter helps.
8. **Ignoring switching costs.** Frequent, correct switching can still lose money net of costs.
9. **Positioning on a volatility forecast.** Vol forecasts are relatively reliable and say nothing
   about direction. Size on them; do not point with them.

## References

Internal: `references/strategy-failure-modes-and-synergy.md` §2, §6, §8, §9;
`references/technical-analysis.md` (ADX, Bollinger, ATR formulas);
`references/trading-strategies-and-styles.md` §5 (backtesting, multiple testing);
`references/trading-risk-management.md` §2 (volatility-based sizing);
`references/ai-and-ml-for-trading.md` §3.2 and `references/ml-backtesting-pitfalls-and-production-systems.md` §8 (PBO, purged CV, deflated Sharpe).

External:
1. Cube Exchange — *What Is Market Regime Detection with Hidden Markov Models?* The "infer a condition
   you cannot observe directly" framing and why rules fail when the environment shifts. https://www.cube.exchange/what-is/market-regime-detection-with-hidden-markov-models
2. MDPI *Mathematics* — *On Regime Switching Models*. Markov-switching as a case of HMMs; Hamilton's
   first-order Markov chain with constant transition probabilities. https://www.mdpi.com/2227-7390/13/7/1128
3. arXiv — *Multi-regime Markov-switching models with time-varying transition probabilities*.
   Why the constant-transition-probability assumption is relaxed in practice. https://arxiv.org/pdf/2605.14976
4. PyQuantLab — *Enhancing Trading Strategies With a Hurst-Based Regime Filter*. The H > 0.55 / H < 0.45
   thresholds and the stand-aside transitional band. https://pyquantlab.medium.com/enhancing-trading-strategies-with-a-hurst-based-regime-filter-ac6639be43cf
5. FractalCycles — *Hurst Exponent vs ADX*. The strategic-compass vs tactical-signal split. https://fractalcycles.com/compare/hurst-vs-adx
6. QuantNeuralEdge — *Hurst Exponent: Trending vs Ranging Markets*. https://quantneuraledge.com/blog/hurst-exponent-trending-ranging-markets

**Source-quality note.** The **statistical machinery** (Hamilton Markov-switching, HMMs, MS-GARCH,
variance ratio, CUSUM, Bayesian online changepoint) rests on peer-reviewed literature, cited above via
secondary summaries rather than the primary papers — the mechanisms are standard and stable, but the
specific summaries were not verified against Hamilton (1989) directly in this pass. The **numeric
thresholds** (ADX 25, Hurst 0.45/0.55) are **practitioner conventions, not results** — single- or
lightly-sourced, asset- and timeframe-dependent, and to be treated as starting points for your own
calibration. No performance claim appears in this reference, deliberately: every regime-filter result
this session produced was dominated by its own un-gated benchmark or by parameter selection (§8.1,
§8.3), and publishing a number here would misrepresent that.
