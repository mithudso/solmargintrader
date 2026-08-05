---
name: portfolio-theory-and-asset-allocation
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  The theory, and the estimation problem that limits it. Markowitz mean-variance
  and the efficient frontier; why diversification works through CORRELATION
  rather than count, with the variance algebra showing what it can and cannot
  remove; CAPM, beta and the security market line, plus the empirical record
  against it; factor models (Fama-French three- and five-factor, Carhart
  momentum) and factor decay; rebalancing and the conditional rebalancing bonus;
  strategic vs tactical allocation. Then the honest half — optimisers as
  "estimation-error maximisers" (Michaud 1989), the DeMiguel-Garlappi-Uppal
  finding that naive 1/N is hard to beat out of sample, and correlation
  instability. Educational only — NOT financial advice.
keywords:
  - modern portfolio theory
  - Markowitz
  - efficient frontier
  - mean variance optimisation
  - diversification
  - correlation
  - covariance
  - systematic risk
  - idiosyncratic risk
  - CAPM
  - beta
  - security market line
  - Sharpe ratio
  - factor model
  - Fama-French
  - Carhart
  - momentum factor
  - rebalancing
  - rebalancing bonus
  - strategic asset allocation
  - tactical asset allocation
  - estimation error
  - shrinkage
  - Black-Litterman
  - 1/N
  - risk parity
---

# Portfolio Theory & Asset Allocation (spoke)

A spoke of the **`trading-and-investing`** hub. This page owns the **theory**. Two neighbours own the practice and are not duplicated here: **`sleeve-weighting-and-objective-selection`** owns how much capital each strategy sleeve actually gets, and the measured finding that different objectives rank the same blends *oppositely*; **`trading-risk-management`** owns per-trade sizing, stops and Kelly. The consumer how-to for long-term passive allocation is the sibling family's `investing-and-retirement`.

> **Educational information only — NOT financial, investment or tax advice.** Every model here takes **expected returns, variances and correlations as inputs**, and all three must be *estimated* from finite, noisy, non-stationary data. §10–§12 are about how badly that undermines the elegant results in §1–§9. **A portfolio optimiser is not a machine that produces good portfolios; it is a machine that produces the portfolio that would have been good if your inputs were right.** Treat the mathematics as a way of thinking, not as a method that answers the question.

## Contents

1. The one insight: risk is a property of the portfolio
2. The variance algebra, and what diversification can remove
3. The efficient frontier
4. The Sharpe ratio and the capital allocation line
5. CAPM, beta, and the security market line
6. What the evidence did to CAPM
7. Factor models
8. Rebalancing
9. Strategic vs tactical allocation
10. Estimation error — the central problem
11. 1/N, and why naive diversification is hard to beat
12. Correlation instability
13. Anti-patterns

## 1. The one insight: risk is a property of the portfolio

Markowitz's 1952 contribution was not "diversify" — that was folk wisdom. It was that **an asset's risk cannot be evaluated in isolation**, because what matters is its contribution to the *portfolio's* variance, which depends on how it **co-moves** with everything else held.[^markowitz]

A volatile asset that moves against the rest of the portfolio can **reduce** total risk. A calm asset perfectly correlated with the portfolio reduces nothing. Standalone volatility is therefore the wrong lens, and stacking up "safe" assets that all fall together is not diversification.

## 2. The variance algebra, and what diversification can remove

For two assets with weights *w₁, w₂*:

```
σ²_p = w₁²σ₁² + w₂²σ₂² + 2·w₁w₂·ρ₁₂·σ₁σ₂
```

The whole subject sits in the third term, and **only the correlation ρ appears there** — the benefit is driven by co-movement, not by the number of holdings.

- **ρ = +1** — no benefit; portfolio risk is the weighted average.
- **ρ = 0** — meaningful reduction.
- **ρ = −1** — some weighting drives variance to zero.

**For N equally-weighted assets**, portfolio variance tends toward the **average covariance** as N grows: own-variance terms shrink with 1/N, covariance terms do not. That gives the field's central split:

- **Idiosyncratic (diversifiable) risk** — asset-specific, removable, and most of it goes quickly. The marginal benefit of the 40th holding is small.
- **Systematic (market) risk** — the common factor. **Cannot be diversified away by adding more of the same asset class at any N.**

**Two implications that get missed.** Diversification has **diminishing returns in count** and **no ceiling in independence** — one genuinely uncorrelated sleeve does more than fifty more equities. And correlations **rise in crises**, so part of what you diversified against in calm markets is still there in the only regime that matters (§12).

## 3. The efficient frontier

Plot every feasible portfolio in (risk, return) space. The upper-left boundary — maximum return per unit of risk — is the **efficient frontier**; anything below is dominated. **Mean-variance optimisation** solves for it given expected returns, variances and correlations.

- The frontier is **curved**, and the curvature *is* the diversification benefit.
- The **minimum-variance portfolio** is the leftmost point and needs **no return forecast**, only a covariance matrix. That makes it the least input-hungry and most defensible point on the frontier — which matters a great deal once §10 arrives.
- **The frontier is computed, not observed.** It is a function of three estimated inputs, and that sentence carries most of the weight on this page.

## 4. The Sharpe ratio and the capital allocation line

```
Sharpe = (R_p − R_f) / σ_p
```

Excess return per unit of volatility. Adding a risk-free asset lets you hold any point on a straight line from *R_f* through a risky portfolio; the steepest such line touches the frontier at the **tangency (maximum-Sharpe) portfolio**. Moving along that line is lending or borrowing, not changing the risky mix.

**Where Sharpe misleads:** it penalises upside volatility identically to downside; it assumes roughly symmetric returns; and it is **trivially inflated by selling tail risk**, which produces a smooth series right up until it does not. `strategies-and-risk` §3 and `volatility-and-pricing` §2 are the same warning in options form. Sortino, Calmar and drawdown-based measures → `trading-risk-management`.

## 5. CAPM, beta, and the security market line

CAPM (Sharpe, Lintner, Mossin) says only **systematic** risk should be compensated, because idiosyncratic risk is removable for free:

```
E[R_i] = R_f + β_i (E[R_m] − R_f)
```

**Beta** is sensitivity to the market: `β = cov(R_i, R_m) / var(R_m)`. β > 1 amplifies, β < 1 damps. The **security market line** plots expected return against beta.

**The idea that survives even though the model does not:** do not expect to be paid for risk you could have diversified away. A concentrated single-stock position carries idiosyncratic risk the market will not compensate you for bearing.

## 6. What the evidence did to CAPM

Stated plainly, because CAPM is still taught as if descriptive:

- The empirical beta-return relationship has been **much flatter than predicted**, and in some samples essentially absent.
- **Beta is unstable**, and estimates depend heavily on the window and return frequency.
- **Documented anomalies** — size, value, momentum, profitability, low volatility — relate to average returns *after* controlling for beta, which CAPM says is impossible.
- **Roll's critique:** the "market portfolio" is unobservable, so any test is a test of the proxy.

**The honest position:** CAPM is the right first idea — compensation for undiversifiable risk — with the wrong single factor. That is what motivated §7.

## 7. Factor models

**Fama-French three-factor** (1993) adds size and value to the market:

```
R_i − R_f = α + β_m(R_m − R_f) + β_s·SMB + β_v·HML + ε
```

**SMB** = small minus big, **HML** = high minus low book-to-market.[^ff3] **Carhart** (1997) adds **momentum** (UMD). **Fama-French five-factor** (2015) adds profitability (RMW) and investment (CMA).[^ff5]

**What a factor model is really for:** not forecasting, but **attribution**. It answers "is this return explained by known exposures, or is something left over?" A strategy whose returns load entirely on momentum has not discovered anything — it has bought a documented factor, probably more expensively than it could have.

**Three cautions, most important first:**

1. **Factor decay.** Published premia have generally weakened after publication — McLean & Pontiff is the canonical statement, and this family's own `RANKED_LISTS.md` cites their 26% in-sample / 58% out-of-sample decay figures. A factor in a paper is not that factor available to you at that magnitude.
2. **The factor zoo.** Hundreds of proposed factors exist, most produced by a large unrecorded search. Multiple-testing accounting → `algorithmic-and-quant-trading` §5.3 and `ml-backtesting-pitfalls-and-production-systems`; the corrected significance threshold is materially above the conventional t > 2 (Harvey-Liu-Zhu argue for t > 3.0).
3. **Factors have long drawdowns.** Value underperformed for well over a decade in the recent record. A factor being real does not make it survivable at your horizon or your conviction.

## 8. Rebalancing

Holding fixed target weights requires periodically selling what grew and buying what lagged.

**What rebalancing actually does: it controls risk drift.** Left alone, the highest-returning (usually highest-risk) asset comes to dominate — an unrebalanced 60/40 becomes an equity portfolio precisely *after* equities have run.

**The "rebalancing bonus" is real but conditional.** For assets with similar returns, **low correlation**, and **mean reversion**, systematic rebalancing can add return by mechanically selling high and buying low. It is not a free lunch: against a **persistently trending** asset, rebalancing *reduces* return by trimming the winner. The bonus is a property of the correlation and mean-reversion structure, not of the act of rebalancing.

**Costs belong in the comparison:** transaction costs, spreads, and in a taxable account **realised capital gains** — including wash-sale interaction (`trading-regulation-compliance-and-taxes` §6–§7). **Threshold** rebalancing (act when a weight leaves a band) generally dominates **calendar** rebalancing on cost, because it trades only when the drift is material.

## 9. Strategic vs tactical allocation

- **Strategic (SAA)** — long-horizon target weights from objectives and risk tolerance. Changed rarely.
- **Tactical (TAA)** — deliberate short-to-medium-term deviations based on a view.

**The honest asymmetry:** SAA requires only that you can state a risk tolerance. TAA requires you to **forecast**, and is subject to the evidence in `investing-vs-trading` that most active deviation underperforms after costs. TAA is not free even when it is right, because it consumes turnover and tax.

## 10. Estimation error — the central problem

Everything above takes μ, σ and ρ as **given**. They are estimated from a finite non-stationary sample, and the errors are large.

**Michaud's characterisation is the one to remember: mean-variance optimisers are "estimation-error maximisers."**[^michaud] The mechanism is direct — the optimiser has no concept of uncertainty, so an asset whose expected return is overstated by noise looks genuinely attractive and it **concentrates into it**. The optimisation actively seeks your largest estimation errors.

**Expected returns are by far the worst input.** Volatilities estimate reasonably from moderate samples; correlations less well; **means need impractically long samples** to distinguish from zero, because the standard error of a mean return falls only as 1/√T against volatility an order of magnitude larger. This is the same arithmetic that makes Sharpe-ratio significance require long histories.

**Standard mitigations, honestly labelled as mitigations:**

- **Constraints** (no shorting, position caps) — crude; they work mainly by stopping the optimiser expressing its worst conclusions.
- **Shrinkage** (Ledoit-Wolf and relatives) — pull the covariance matrix toward a structured target. A genuine improvement and standard practice.
- **Black-Litterman** — start from equilibrium weights, tilt only where you hold an explicit view with an explicit confidence.
- **Drop μ entirely** — minimum-variance and **risk-parity** approaches avoid the worst input by not using it. That is most of why they are popular.

## 11. 1/N, and why naive diversification is hard to beat

**DeMiguel, Garlappi & Uppal (2009)** evaluated fourteen mean-variance-based models against naive **equal weighting (1/N)** out of sample across several datasets, and found **none consistently beat 1/N** on Sharpe ratio, certain-equivalent return or turnover.[^demiguel]

**Why, in one sentence:** the estimation error the sophisticated models introduced exceeded the benefit of the optimisation they performed.

**How to read this without over-reading it.** It is not "theory is useless." It is that **the gap between in-sample optimality and out-of-sample performance is dominated by input error**, so the burden of proof sits on the complicated method. Two consequences:

- **Equal weighting is a legitimate baseline, not a strawman.** Any scheme should be shown to beat it out of sample or it has not earned its complexity.
- **This family reaches the same conclusion empirically.** `sleeve-weighting-and-objective-selection` ranks weighting schemes by how much each must *estimate* and makes the plateau argument for round-number weights; `selection-rule-design` measured all five selection rules beating a random baseline yet capturing only **29%** of the random-to-oracle span, with buy-and-hold still ahead. Different data, same lesson: **complexity that consumes estimates pays off less often than it appears it will.**

## 12. Correlation instability

Correlation is the input the entire framework rests on (§2), and it is **not stable**.

- **Correlations rise in crises.** Diversification thins exactly when needed, because in a liquidity event everything is sold at once. A portfolio diversified on calm-period correlations is less diversified than its backtest claims in the regime that matters.
- **The estimate itself swings hard.** This family's measured example: a pairwise correlation used for allocation **ranged from −0.58 to +0.68** across sub-periods (`empirical-backtest-findings-log`) — a sign flip, not a wobble. Any scheme whose weights are a continuous function of that number inherits the instability.
- **Correlation is a linear measure** and misses tail dependence: two assets can be near-uncorrelated in normal conditions and crash together.

**The rule that follows:** prefer schemes whose output is **insensitive** to correlation estimates, and stress-test any diversification claim on crisis sub-periods rather than the full sample.

## 13. Anti-patterns

1. **Counting holdings as diversification.** Only correlation appears in the variance formula (§2).
2. **Expecting compensation for idiosyncratic risk.** It is removable, so it is not paid for (§5).
3. **Teaching CAPM as descriptive.** The beta-return relationship is much flatter than predicted (§6).
4. **Running mean-variance on historical means.** It maximises your estimation errors (§10).
5. **Treating an efficient frontier as observed.** It is computed from three estimates (§3).
6. **Ranking on Sharpe alone.** Tail-selling prints a high Sharpe until it does not (§4).
7. **Buying a published factor at its published premium.** Premia decay post-publication (§7).
8. **Ignoring the factor zoo's multiple testing.** The corrected threshold is well above t > 2 (§7).
9. **Assuming a rebalancing bonus.** It needs low correlation and mean reversion; against a trend it costs return (§8).
10. **Calendar-rebalancing a taxable account** without comparing thresholds and tax cost (§8).
11. **Dismissing 1/N as a baseline.** Fourteen optimisation models failed to consistently beat it (§11).
12. **Diversifying on full-sample correlations.** They rise in crises and the estimate can flip sign (§12).

## References (sources)

[^markowitz]: Harry Markowitz, "Portfolio Selection," *Journal of Finance* 7(1), 1952 — the origin of mean-variance analysis and of the insight that an asset's risk must be judged by its contribution to portfolio variance. tier-2 (peer-reviewed, foundational). Supports §1–§3. verified-as-of: 2026-08-05
[^ff3]: Eugene Fama & Kenneth French, "Common Risk Factors in the Returns on Stocks and Bonds," *Journal of Financial Economics* 33(1), 1993 (market, SMB, HML); Mark Carhart, "On Persistence in Mutual Fund Performance," *J. Finance* 52(1), 1997 (adds momentum). tier-2 (peer-reviewed). Supports §7. Factor data: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html verified-as-of: 2026-08-05
[^ff5]: Eugene Fama & Kenneth French, "A Five-Factor Asset Pricing Model," *JFE* 116(1), 2015 — adds profitability (RMW) and investment (CMA). tier-2 (peer-reviewed). Supports §7. verified-as-of: 2026-08-05
[^michaud]: Richard Michaud, "The Markowitz Optimization Enigma: Is 'Optimized' Optimal?", *Financial Analysts Journal* 45(1), 1989 — the "estimation-error maximiser" characterisation. tier-2 (peer-reviewed). Supports §10, the pivot of this page. verified-as-of: 2026-08-05
[^demiguel]: Victor DeMiguel, Lorenzo Garlappi & Raman Uppal, "Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?", *Review of Financial Studies* 22(5), 2009 — fourteen models, none consistently beating equal weighting out of sample on Sharpe, certain-equivalent return or turnover. tier-2 (peer-reviewed). Supports §11. verified-as-of: 2026-08-05
[^sec-allocation]: SEC / Investor.gov — asset allocation, diversification and rebalancing for individual investors, including that diversification does not eliminate market risk. https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/asset-allocation — tier-1 (regulator). Supports §2 and §8. verified-as-of: 2026-08-05
