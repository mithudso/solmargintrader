---
name: sleeve-weighting-and-objective-selection
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-3 gaps CVS 4.50 + 4.25, clustered
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  How much capital to give each strategy sleeve, and — first — what you are
  optimising for. Covers why the objective question precedes the weighting
  question (mean return, tail, risk-adjusted and hit rate rank blends DIFFERENTLY
  and often oppositely); the weighting schemes (equal, inverse-volatility, risk
  parity, minimum-variance, Kelly) and which inputs each requires; why schemes
  that estimate a correlation matrix are fragile when correlation is unstable;
  the robustness argument for simple weights; rebalancing frequency and its cost;
  and measured evidence that a broad plateau of weights beat both sleeves while
  the correlation estimate underneath swung across its entire range. Educational
  only — NOT financial advice.
keywords:
  - sleeve weighting
  - capital allocation
  - risk parity
  - inverse volatility
  - minimum variance
  - equal weight
  - Kelly criterion
  - objective function
  - tail risk
  - drawdown vs return
  - rebalancing
  - correlation instability
  - estimation error
tags:
  - trading-and-investing
  - portfolio
  - risk
  - allocation
---

# Sleeve Weighting and Objective Selection

> **Educational information only — NOT financial, investment, or tax advice.**

**Two questions that are always asked in the wrong order.** People ask "what weights?" before "optimising
for what?" — but the second determines the first, and different objectives produce *opposite* answers on
the same data. This reference treats them together because separating them is the error.

**Scope.**

| For… | Go to |
|---|---|
| Why pair opposite payoff shapes at all, and the measured OOS result | `references/strategy-failure-modes-and-synergy.md` §1, §6 and `references/empirical-backtest-findings-log.md` §9.7 |
| Position sizing *within* one strategy (Kelly, ATR, fixed-fractional, risk of ruin) | `references/trading-risk-management.md` §2–§3 |
| Regime gating as an alternative to fixed weights | `references/regime-detection-and-classification.md` |
| Walk-forward and multiple-testing discipline | `references/trading-strategies-and-styles.md` §5 |
| The same objective question one level down — picking a *config*, not a weight | `references/selection-rule-design.md` |
| Running the resulting book as software | `references/trading-bot-infrastructure-and-monitoring.md` |

## Contents

1. The objective question comes first
2. Measured: the objective changes the answer
3. Weighting schemes and what each one needs
4. Why correlation-estimating schemes are fragile
5. The case for simple weights
6. Rebalancing
7. Anti-patterns

---

## 1. The objective question comes first

"What weights should I use?" is unanswerable until you say what you are maximising. The common
candidates rank the same blends differently:

| Objective | What it rewards | Who should care |
|---|---|---|
| **Mean return** | Highest expected growth | Long horizon, capital you can genuinely leave alone |
| **Worst month / max drawdown** | Survival of the bad path | Anyone who might stop, be stopped out, or need the money |
| **Risk-adjusted** (Sharpe/Sortino/Calmar) | Return per unit of variability | Comparing strategies of different volatilities |
| **Hit rate** (% profitable periods) | Consistency | Psychological sustainability; anything with outside scrutiny |

**These are not close substitutes.** A blend can improve one while degrading another, and normally
does. Choosing implicitly — by optimising whatever your backtest happens to print — means the objective
was chosen by your tooling.

**The often-decisive practical point:** a strategy you abandon has a realised return of whatever it had
when you quit. If a −47% month would make you stop, then a book that never has one is *better for you*
than a higher-mean book that does, regardless of what the expected-value calculation says. Tail
objectives are not timidity; they are a recognition that you are part of the system.

## 2. Measured: the objective changes the answer

From the out-of-sample walk-forward in `references/empirical-backtest-findings-log.md` §9.7 — a concave grid
sleeve and a convex trend sleeve, both selected out-of-sample, 48 OOS months:

| | mean | median | worst month | % profitable |
|---|---|---|---|---|
| Grid alone (w=1.00) | +0.14% | **+1.81%** | −47.27% | **65%** |
| Trend alone (w=0.00) | **+4.49%** | −1.02% | −38.26% | 48% |
| Blend @ w_grid 0.65 | +1.66% | +1.22% | **−18.50%** | 54% |

**Three different objectives, three different winners on identical data.** Maximise mean → hold trend
alone. Maximise hit rate or median → hold grid alone. Minimise the tail → blend, which roughly
**halves the worst month** relative to the better sleeve.

**There is no weight that wins on everything, and looking for one is a category error.** The blend
costs ~2.8 points of mean return to buy ~20 points of tail improvement. Whether that is a good trade is
a question about you, not about the data.

## 3. Weighting schemes and what each one needs

Ordered by how much they must *estimate* — which is the same as ordered by how badly they can fail.

| Scheme | Weight rule | Inputs needed | Failure mode |
|---|---|---|---|
| **Equal weight** | 1/N | none | Ignores that sleeves differ in volatility; the loudest sleeve dominates risk |
| **Inverse volatility** | ∝ 1/σᵢ | each sleeve's vol | Vol is estimable but non-stationary; ignores correlation entirely |
| **Risk parity** | equal *risk contribution* | vols **+ correlation matrix** | Correlation estimation error (§4) |
| **Minimum variance** | minimise portfolio σ | vols **+ correlation matrix** | Extremely sensitive to estimation error; often extreme weights |
| **Kelly / growth-optimal** | maximise log growth | expected **returns** + covariance | Needs expected returns — the least estimable quantity in finance |

**The ladder is the point.** Each step up promises a better-optimised portfolio and demands an input
that is harder to estimate. Since the optimiser treats its inputs as *true*, estimation error is
converted directly into confident, wrong weights — and the more sophisticated the scheme, the more
aggressively it acts on the noise.

**Volatility is the one input worth trusting**, because it clusters and is genuinely forecastable
(`regime-detection-and-classification.md` §4). Expected returns are the least trustworthy. That
ordering is why inverse-volatility is often the sweet spot: it uses the estimable input and ignores
the unreliable ones.

## 4. Why correlation-estimating schemes are fragile

Risk parity and minimum variance both require a correlation matrix. **On the measured data, that input
was not stable enough to support them.**

The two sleeves' out-of-sample correlation, same 48 months:

- **Pooled: −0.11**
- **Non-overlapping 12-month blocks: +0.06, −0.01, −0.51, −0.50**
- **Rolling 12-month: −0.58 to +0.68**, stdev **0.34**, negative in only 68% of windows

A correlation input that ranges from strongly negative to strongly positive is not a parameter; it is a
sampling artifact. **A minimum-variance optimiser fed that number will produce confidently different
weights every quarter, each justified by an estimate that will not persist.** Rebalancing on those
weights converts estimation noise directly into turnover and cost.

**The finding that rescues the whole approach:** the blend beat both sleeves' worst months in **all four
blocks anyway — including the block where correlation was mildly positive.** The tail benefit does not
require stable negative correlation. It requires only that **the sleeves' worst months do not coincide**,
which is a weaker and far more robust condition. In the measured data the roles even swapped: grid had
the worse tail early, trend later.

**So: rely on "their bad months land in different places," not on a correlation coefficient.**

## 5. The case for simple weights

Given §4, the argument for equal or inverse-volatility weighting is not laziness — it is that they
**require inputs you can actually estimate**.

Supporting evidence from the same run: **every weight from w_grid 0.05 to 0.85 beat both sleeves' worst
months.** The result is a broad **plateau**, not a sharp peak. When the objective surface is that flat,
precision in weighting buys almost nothing, while the machinery required to achieve that precision
introduces real estimation risk.

**The diagnostic to run before optimising weights:** plot the objective across the weight range. If it
is a plateau, take a round number in the middle of it and stop. If it is a sharp peak, be suspicious —
sharp optima in strategy research are usually fitted, and a weight that only works at exactly 0.63 will
not survive contact with a new year of data.

## 6. Rebalancing

Weights drift as sleeves perform differently. Rebalancing restores them; it also costs money and, in
crypto, generates a **taxable disposal per trade**
(`references/onchain-pnl-and-tax-accounting.md`).

- **Calendar rebalancing** (monthly, quarterly) — predictable, easy to model, may trade when nothing
  needs fixing.
- **Threshold rebalancing** (when a weight drifts more than X% from target) — trades only when it
  matters, and is usually the better default.
- **Never rebalancing** is a decision too: the winning sleeve grows until the book is effectively
  single-sleeve, and your tail protection quietly disappears. **That is the failure mode that looks
  like success right up until it doesn't.**

Rebalancing is mechanically **counter-trend** — it sells the winner to buy the loser. In a persistent
trend that costs money. Combined with §5's plateau finding, this argues for **wide bands and
infrequent rebalancing** rather than tight tracking of a precise target.

## 7. Anti-patterns

1. **Choosing weights before choosing an objective.** Unanswerable in that order (§1).
2. **Reporting only mean return for a book built to reduce tail risk.** Measuring the thing it was not
   built to do (§2).
3. **Feeding an unstable correlation estimate into a minimum-variance optimiser** and rebalancing on
   the output (§4).
4. **Optimising to a sharp weight peak.** Almost certainly fitted; check for a plateau (§5).
5. **Using Kelly with estimated expected returns** as though the estimate were the truth (§3).
6. **Never rebalancing**, then being surprised the book became one sleeve (§6).
7. **Rebalancing tightly and often** without counting fees, slippage and taxable disposals (§6).
8. **Assuming diversification requires negative correlation.** Non-coincident bad months suffice, and
   are far more robust (§4).
9. **Equal-weighting sleeves of very different volatility** and calling it balanced — risk, not
   capital, is what is being allocated (§3).

## References

Internal: `references/strategy-failure-modes-and-synergy.md` §1, §6, §9.7 (the pairing rationale and
the measured OOS result); `references/trading-risk-management.md` §2–§3 (sizing within a strategy);
`references/regime-detection-and-classification.md` §4 (volatility as the estimable input);
`references/trading-strategies-and-styles.md` §5 (walk-forward, multiple testing);
`references/onchain-pnl-and-tax-accounting.md` (rebalancing as taxable disposals);
`references/trading-bot-infrastructure-and-monitoring.md` (running the book).

**Evidence note.** The §2, §4 and §5 numbers are **first-party measurements** from this repo —
reproduce with `~/Downloads/sol-backtest-data/_scripts/run_walkforward_book.py`. They are **48
out-of-sample months on a single asset (SOL) with two sleeves**, which is enough to demonstrate that
the objective changes the answer and that the correlation input was unstable *here*, and **not** enough
to establish any particular weight as correct in general. The scheme taxonomy in §3 is standard
portfolio-construction material stated without external citation; the estimation-error argument is
conventional and long-standing in the literature, though this reference does not cite the primary
sources for it. **No weight, objective or number here should be read as a recommendation.**
