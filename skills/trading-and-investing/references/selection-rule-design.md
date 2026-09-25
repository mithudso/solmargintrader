---
name: selection-rule-design
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-7 top gap, CVS 4.65
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  The third walk-forward knob nobody tests — the RULE that picks a configuration
  from the training window. Covers the candidate rules (argmax mean, median,
  Sharpe, maximin, rank aggregation) and what each optimises; the two controls
  that make a selection experiment interpretable at all — a RANDOM baseline
  (does selection beat picking blindly?) and an ORACLE bound (how much is even
  available?); measured evidence that all five rules beat random but captured
  only ~29% of the achievable span while still losing to buy-and-hold; the
  counter-intuitive result that selecting on worst-case training months produced
  the WORST out-of-sample tail; and why rule choice interacts with window length
  so the two cannot be tuned separately. Educational only — NOT financial advice.
keywords:
  - selection rule
  - model selection
  - argmax
  - objective function
  - rank aggregation
  - maximin
  - random baseline
  - oracle bound
  - walk-forward
  - parameter selection
tags:
  - trading-and-investing
  - backtesting
  - validation
  - quantitative
---

# Selection Rule Design

> **Educational information only — NOT financial, investment, or tax advice.**

A walk-forward has three knobs, and the literature discusses one. Everybody argues about the strategy;
some people test the **window length** and **refit cadence**
(`walk-forward-window-length-and-refit-cadence.md`). Almost nobody asks about the third: **given the
training window, which rule picks the configuration?** In practice it is always
`max(configs, key=mean(train_returns))`, chosen by habit.

**Scope.**

| For… | Go to |
|---|---|
| Window length and refit cadence — the other two knobs | `references/walk-forward-window-length-and-refit-cadence.md` |
| Choosing the objective for a *book* rather than a config | `references/sleeve-weighting-and-objective-selection.md` §1 |
| Walk-forward protocol, purging, multiple testing | `references/trading-strategies-and-styles.md` §5; `references/algorithmic-and-quant-trading.md` §5.3 |
| Whether the chosen value travels to another asset | `references/asset-specific-vs-universal-parameters.md` |
| The surrounding measured runs | `references/empirical-backtest-findings-log.md` §9 |

## Contents

1. The candidate rules
2. The two controls that make the experiment mean anything
3. Measured: selection beats random, and still loses to buy-and-hold
4. The maximin paradox
5. Rule and window are not separable
6. Anti-patterns

---

## 1. The candidate rules

Each rule answers "best on the training window" differently, and each encodes a different belief about
what carries forward.

| Rule | Picks the config with… | Implicit belief |
|---|---|---|
| **argmax mean** | highest average training return | Past average return predicts future average return |
| **argmax median** | highest median training month | Typical months carry forward; outliers are noise |
| **argmax Sharpe** | highest mean ÷ stdev | Consistency carries forward better than magnitude |
| **maximin** | best *worst* training month | Downside behaviour is the stable property |
| **rank aggregation** | best average *rank* across months | Only the ordering is reliable; magnitudes are not |

**The choice is not cosmetic.** Mean is dominated by outlier months, so one enormous month can elect a
configuration that is otherwise mediocre. Median and rank aggregation deliberately discard magnitude.
Sharpe rewards low variance, which in a strategy context often means *low activity*. Maximin optimises
the tail — or is supposed to (§4).

## 2. The two controls that make the experiment mean anything

**Comparing five selection rules against each other tells you almost nothing on its own.** One of them
has to come first. Two baselines turn a beauty contest into a measurement:

- **RANDOM** — pick a configuration uniformly at random at each refit, averaged over many seeds. **This
  is the null.** If your clever rule does not beat random selection, the entire selection step is
  ceremony, and you should stop paying its multiple-testing cost.
- **ORACLE** — pick, at each step, the config that will actually perform best *next* month. Impossible
  and deliberately cheating. It bounds **how much selection could possibly earn**, which converts a
  raw return into a meaningful fraction: *of the gain that was available, how much did we capture?*

**Without the random baseline you cannot tell skill from luck; without the oracle you cannot tell a
good result from a small one.** Report both, always.

## 3. Measured: selection beats random, and still loses to buy-and-hold

Grid + trend book on SOL, 1-hour bars, **48 out-of-sample months** (2022-08 → 2026-07). Protocol held
fixed at the inherited settings — 12-month rolling window, monthly refit, book weight 0.65 — so **only
the rule varies**. 18 grid configs, 54 trend configs.

| Selection rule | book mean | book median | worst month | % profitable |
|---|---:|---:|---:|---:|
| **argmax mean (incumbent)** | **+1.66%** | +1.22% | −18.50% | 54% |
| maximin (worst month) | +0.61% | +1.52% | −31.24% | 56% |
| argmax Sharpe | +0.42% | +0.56% | −23.36% | 54% |
| rank aggregation | +0.40% | +1.44% | −20.12% | 56% |
| argmax median | −0.03% | +0.16% | −18.08% | 52% |
| **RANDOM** (200 seeds) | **−1.61%** | | −28.97% | |
| *random 95% band* | *[−3.72%, +0.03%]* | | | |
| **ORACLE** (cheats) | **+9.65%** | +7.60% | −5.20% | 90% |
| **Buy & hold** | **+5.64%** | −1.07% | −56.52% | 44% |

**Three findings, in descending order of confidence.**

**1. Selection is doing something real.** All five rules beat the random baseline, and the incumbent
sits **outside random's 95% band**. Picking a config from training data genuinely beats picking one
blindly. That is not obvious and it is worth knowing — much of this family's other evidence has gone
the other way.

**2. The inherited default appears to be the right one — modestly.** `argmax mean` won outright at the
headline protocol. Repeating the comparison at five distinct window lengths (6, 9, 12, 18, 24) on a
common 36-month out-of-sample span, it won **3 of 5**. Under a uniform null over five rules that is
**p ≈ 0.058**. Suggestive, not established — and notably the *opposite* verdict from refit cadence,
where the inherited default was the one that failed.

**3. But the ceiling is low and buy-and-hold still wins.** The oracle returned **+9.65%**; the
incumbent captured only **29.1%** of the random→oracle span. And **buy-and-hold returned +5.64% over
the same 48 months — more than triple the best rule.** So: selection beats chance, chance is a low bar,
and none of it beat holding the asset. Both statements are true and reporting only the first would be
the familiar dishonesty.

## 4. The maximin paradox

**Selecting on the worst training month produced the worst out-of-sample tail.** Maximin picked
configs whose worst training month was best — and delivered a **−31.24%** worst month, against
**−18.50%** for argmax-mean, which optimises nothing about tails at all.

**The mechanism is selection on a noisy order statistic.** A config's worst month over a 12-month
window is a single observation — the minimum of twelve — and minima are far noisier than means. Picking
the config with the least-bad worst month largely picks **the config that got lucky in its worst
month**, and that luck does not persist. Optimising a statistic estimated from one observation selects
for favourable noise, not for a durable property.

**The general lesson: prefer selection criteria computed from many observations over criteria computed
from few, even when the few-observation criterion is closer to what you actually care about.** Wanting
tail protection does not mean selecting on a tail estimate. It is the same reason the worst-month
column in `walk-forward-window-length-and-refit-cadence.md` §3 carries an n=1 warning.

## 5. Rule and window are not separable

The five-window comparison in §3 shows the ranking **changing with the window**:

| Window | Winning rule |
|---:|---|
| 6 | argmax median (+2.11%) |
| 9 | argmax mean |
| 12 | argmax mean |
| 18 | argmax mean |
| 24 | rank aggregation (+0.65%) |

`argmax median` was the *best* rule at a 6-month window (+2.11%) and the *worst* at 12 (−0.04%). That
is not noise around a stable ordering; it is an interaction. **Short windows have few months, so the
median is computed from very little and behaves differently than it does over 24.**

**Consequence: you cannot tune the window, then tune the rule, and expect the pair to be jointly
sensible.** They have to be evaluated together — which also means the degrees of freedom multiply, and
the multiple-testing cost with them (`algorithmic-and-quant-trading.md` §5.3).

## 6. Anti-patterns

1. **Never questioning `argmax mean`.** It is a choice, not a law — and here it happened to be a
   defensible one, which you could only know by testing (§3).
2. **Comparing selection rules with no random baseline.** One rule always wins; without the null you
   cannot tell whether any of them beat blind picking (§2).
3. **Reporting a selection result with no oracle bound.** "+1.66%" means nothing until you know the
   achievable range was −1.61% to +9.65% (§2).
4. **Selecting on a statistic estimated from one or two observations** — worst month, max drawdown,
   best month. You will select for favourable noise (§4).
5. **Assuming the rule that optimises a property delivers that property out-of-sample.** Maximin
   optimised the tail and produced the worst tail measured (§4).
6. **Tuning window and rule independently.** They interact; the best rule changed with the window (§5).
7. **Reporting "selection beat random" without also reporting that buy-and-hold beat selection** (§3).
8. **Forgetting that the rule is itself a fitted choice.** Trying five rules is five more configurations
   in your multiple-testing accounting (§5).

## References

Internal: `references/walk-forward-window-length-and-refit-cadence.md` (the other two knobs, and the
n=1 caution this section's §4 generalises); `references/sleeve-weighting-and-objective-selection.md` §1
(objective choice one level up — for the book rather than the config);
`references/trading-strategies-and-styles.md` §5 and `references/algorithmic-and-quant-trading.md` §5.3
(walk-forward protocol, degrees of freedom, multiple testing);
`references/asset-specific-vs-universal-parameters.md` (whether a selected value travels);
`references/empirical-backtest-findings-log.md` §9 (surrounding measured runs).

**Evidence note.** The §3–§5 tables are **first-party measurements** — reproduce with
`~/Downloads/sol-backtest-data/_scripts/run_selection_rules.py`, which reuses the simulation cache
built by `run_window_sweep.py` and prints the random band and oracle bound. **One asset (SOL), one
venue, two strategy families, 48 out-of-sample months, five rules.** The random baseline is 200 seeds;
the oracle is a deliberate look-ahead upper bound and is **not achievable**. The "incumbent is best"
claim rests on 3 of 5 window settings at **p ≈ 0.058** and should be read as suggestive only. **No rule
here beat buy-and-hold over the measured window**, so nothing in this file is evidence of a profitable
configuration, and no value is a recommendation.
