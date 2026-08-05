# The concept family of strategy optimization

Scoping document for `/dso` (deep strategy optimizer). Written to answer one question: **what would
a strategy optimizer have to do to be worth running on this repo, given what this repo has already
measured?**

The short answer, and the reason this document exists: on this codebase's own evidence, the
optimization arm of a strategy optimizer is the *less* valuable half. The valuable half is defect
detection. Section 6 gives the numbers that force that conclusion.

Nothing here is investment advice.

---

## 1. Parent / super-domain

Strategy optimization is a special case of **model selection under multiple hypothesis testing**,
distinguished by three properties that make it harder than ordinary hyperparameter tuning:

1. **The evaluation metric is itself a noisy estimate.** A Sharpe ratio computed on 234 bars has a
   standard error large enough to reorder a leaderboard. Ranking on it is ranking on noise plus
   signal, and the ratio of the two is usually unknown.
2. **The search is adversarial to the evaluator.** Every configuration tried is another draw from
   the distribution of maxima. The best of 1,287 trials is expected to look good even when none of
   them has an edge.
3. **The data cannot be resampled.** There is one realized price path. Unlike A/B testing you cannot
   collect a fresh sample; you can only partition the one you have, and partitions leak through
   serial correlation.

Everything below is a technique for surviving one of those three.

## 2. Siblings (same level, same parent)

| Sibling | What it shares | What it does not |
| --- | --- | --- |
| ML hyperparameter optimization | search over configurations, held-out validation | i.i.d. resampling is valid; can collect more data |
| Feature selection | multiple-testing explosion | usually has a stable target variable |
| A/B test design | significance under repeated looks | can randomize assignment; has a control |
| Portfolio construction | optimizes a risk-adjusted objective | optimizes weights over assets, not rules over time |
| Experiment design (DoE) | choosing which trials to run | trials are cheap and independent |

The useful borrowing is from **A/B testing** (sequential-testing discipline, pre-registration) and
from **DoE** (deciding what *not* to try). The dangerous borrowing is from ML hyperparameter
optimization, whose whole culture assumes you can hold out an i.i.d. slice.

## 3. Children / sub-concepts, tagged against this repo

`HAVE` = implemented and tested here. `PARTIAL` = done once by hand, not tooled. `GAP` = absent.

### 3.1 Parameter search
| Concept | Status | Where / note |
| --- | --- | --- |
| Grid / preset sweep | `HAVE` | `research/sweep.py`, `research/cpcv_sweep.py` (1,287 configs) |
| Random / Bayesian / TPE / CMA-ES / genetic search | `GAP` | **Deliberately not wanted.** A more efficient searcher over a PBO-0.700 objective finds overfit configurations faster. Search efficiency is the wrong axis to improve here. |
| Presets as the unit of search | `HAVE` | cards carry `presets: {short, medium, long}`, drift-tested against `sweep.py` |

### 3.2 Objective design
| Concept | Status | Note |
| --- | --- | --- |
| Sharpe, Sortino, Calmar, profit factor, win rate | `HAVE` | `core/metrics.py` |
| Median / Q1 path Sharpe across CPCV paths | `HAVE` | `core/cpcv.py` — the right objective shape: a distribution, not a point |
| Drawdown-constrained / utility objectives | `GAP` | low value; Calmar plus the max-drawdown column already covers the decision |
| **Deflated Sharpe Ratio (DSR)** | `GAP` | **highest-value gap.** See §5.1 |

### 3.3 Validation protocol
| Concept | Status | Note |
| --- | --- | --- |
| Single 70/30 split | `HAVE` | `evaluation: single-split-70-30` on most cards — weakest tier, and labelled as such |
| Walk-forward | `HAVE` | earlier sweeps |
| Combinatorial purged CV | `HAVE` | `core/cpcv.py`, 28 paths |
| Purging + embargo around test blocks | `HAVE` | inside `cpcv_evaluate` |
| PBO via CSCV | `HAVE` | `pbo_cscv()` |
| Warm-up accounting (`warmup_bars`) | `HAVE` | on every card; shrinks the usable block set for 250-bar strategies |

This row is the repo's genuine strength. Most of the standard overfitting defences are already here.

### 3.4 Overfitting diagnostics
| Concept | Status | Note |
| --- | --- | --- |
| PBO | `HAVE` | measured 0.700 medium/long |
| Deflated Sharpe / multiple-testing haircut | `GAP` | §5.1 |
| Minimum backtest length / minimum track record length | `GAP` | §5.2 |
| White's Reality Check / Hansen SPA | `GAP` | heavier; bootstrap over the whole config set. Lower priority than DSR because PBO already answers the "is the leaderboard informative" question |
| **Evidence floor on trade count** | `PARTIAL` | the *phrase* is in the cards; no mechanical veto. §5.2 |
| **Result-vector degeneracy** | `GAP` | §5.3 |

### 3.5 Robustness
| Concept | Status | Note |
| --- | --- | --- |
| Parameter perturbation ±10% | `HAVE` | `research/perturb.py`, now across all 25 singles at every horizon |
| Cross-asset transfer | `PARTIAL` | BTC/ETH runs done by hand; not a gate |
| Cross-timeframe transfer | `PARTIAL` | 1d vs 1h done by hand; catastrophic for `hurst_switch` (1st → 23rd) |
| Regime stratification | `GAP` | would explain the 1d/1h collapse rather than just observing it |
| Bootstrap / noise injection on the price path | `GAP` | moderate value; perturbation covers the parameter axis but not the data axis |

### 3.6 Cost realism
| Concept | Status | Note |
| --- | --- | --- |
| Fees, slippage, perp borrow fee in the P&L path | `HAVE` | non-negotiable #3; `CostConfig` |
| Fill timing / no same-bar fills | `HAVE` | `gridsim.py` pessimism conventions |
| Market impact, capacity limits | `GAP` | not binding at $12/rung; would matter at size |

### 3.7 Attribution
| Concept | Status | Note |
| --- | --- | --- |
| Dataset vs strategy | `PARTIAL` | the sharpest finding this repo has produced (§6) and it is not tooled |
| Is it just beta / buy-and-hold in disguise | `PARTIAL` | `buy_and_hold` is in the registry as a benchmark, compared by hand |
| Parameter vs structure | `HAVE` | that is exactly what `perturb.py` answers |

### 3.8 Position sizing and risk overlay
| Concept | Status | Note |
| --- | --- | --- |
| Vol targeting | `HAVE` | `voltarget`, `garch_voltarget` — and see §5.3, they may be degenerate |
| Kelly / fractional Kelly | `GAP` | sizing on an edge you have not established is premature |
| Drawdown control | `HAVE` (extension) | risk rails in `src/core/risk.js` |

## 4. Adjacent / cross-over domains

The neighborhood that actually pays here.

- **Software correctness.** This repo's real losses to date have been *bugs*, not bad strategies:
  a sell-slippage double-count that survived all 30 tests because every test ran at zero cost; an
  Ichimoku displacement that would have leaked one bar; four fabricated card defaults; a duplicate
  `registry_key` that silently shadowed another card; a tautological test comparing a function to
  itself. Every one inflated or corrupted a reported number. **An optimizer that does not audit for
  these is optimizing a number it has not verified.**
- **Data quality.** Geo-blocked sources, non-OHLCV row order, gaps refused rather than
  forward-filled (`align_peer`). A reordered column silently measures the wrong series.
- **Execution microstructure.** The resting-ladder grid is a different object from the exposure
  staircase; `gridsim.py` and `grid.js` must move together or the backtest becomes a confident wrong
  number about the live strategy.
- **Statistics.** Stationarity and cointegration (`core/cointegration.py`, ADF with MacKinnon
  criticals) — and the reminder built into its own test that a 5% test has a 5% false-positive rate
  by construction, so scanning many windows *will* find spurious cointegration.
- **Reproducibility and provenance.** Strategy cards with bidirectional drift tests, and
  `research/verify_numbers.py` re-deriving every published figure from the result CSVs. This is
  rarer than it should be and it is what makes any claim here auditable.

## 5. Frontier / the gaps worth closing

### 5.1 Deflated Sharpe Ratio — the largest gap
PBO answers "is this leaderboard informative?" (answer: no, 0.700). It does **not** answer "given
that I searched N configurations, how much of this specific config's Sharpe is expected maximum?"
That is the Deflated Sharpe Ratio (Bailey & López de Prado): compute the expected maximum Sharpe
under the null across N trials given the observed *variance of trial Sharpes*, then evaluate the
candidate against that inflated benchmark rather than against zero.

With 1,287 configurations searched (75 singles + 1,002 pairs + 210 triples), the null expectation is
not zero, and comparing to zero overstates every result in `RANKED_LISTS.md`.

Note this is a **different quantity from the PBO**: the burden counts the whole search, while the
0.700 PBO was computed over the 25 singles. Quoting one as the other is the kind of slip this
document exists to prevent, and it happened once in the first draft of `/dso` itself.

**Before implementing, verify the expected-maximum formula against the source paper** — it involves
the Euler–Mascheroni constant and the inverse normal CDF at `1 − 1/N` and `1 − 1/(Ne)`, and this
document deliberately does not reproduce it from memory. Getting it subtly wrong would produce a
confident wrong haircut, which is worse than no haircut.

### 5.2 Evidence floor and minimum track record length
`ou_reversion` ranked **1st on BTC daily on 6 trades, with a Q1 path Sharpe of exactly 0.000**. Six
trades cannot distinguish edge from luck at any useful confidence. The cards use the phrase
"below the evidence floor" but nothing enforces it. This should be a **binary veto**, not a caveat:
below the floor, a result is not eligible to be reported as an improvement at all.

### 5.3 Result-vector degeneracy
`voltarget`, `garch_voltarget`, and `sma_regime` returned **numerically identical** hourly rows
(−2.282 Sharpe, −19.9% return, 292 trades) because the volatility cap binds on every bar. Three
"different" strategies were one strategy. Nothing detects this, and it inflates apparent search
breadth — which in turn inflates the multiple-testing burden in §5.1 while adding no diversity.

The check must compare **result vectors** (equity curves or per-bar exposure), not parameter sets.

### 5.4 Dataset-vs-strategy attribution
See §6. Not tooled; done by hand.

### 5.5 Contested / emerging, deliberately not adopted
- **LLM-driven strategy generation.** Directly relevant, because `/dso` is an LLM tool. An agent
  that can propose unlimited variants collapses the multiple-testing budget instantly. This is the
  main argument for `/dso` having a *promotion gate* rather than a *generator*.
- **Synthetic / generative market data** (GAN, diffusion simulators). A simulator trained on the one
  realized path cannot manufacture independent evidence about that path. Noted, not adopted.
- **Probabilistic Sharpe Ratio.** Sibling of DSR; subsumed by it for this purpose.

## 6. The measured evidence that decides the design

Every figure here is from this repo's own runs, reproducible via `research/cpcv_sweep.py` and
`research/verify_numbers.py`.

| Observation | Figure | What it implies for an optimizer |
| --- | --- | --- |
| PBO, singles (25 configs), medium and long, under CPCV | **0.700** | In-sample rank is *anti*-informative. A promotion gate reading in-sample Sharpe is worse than a coin flip. |
| Positive OOS Sharpe — earlier **single-split** sweep | **14% of 311** | The prior on any candidate improvement is low. |
| Made money, same single-split sweep | **9%** | `SUCCESS_LIKELIHOODS` has no `high` tier on purpose. |
| Short horizon, singles with positive median path Sharpe | **0 of 25** | Some regimes have nothing to optimize. |
| BTC daily vs SOL hourly | **25/25 positive vs 0/25** | The dataset explains more than the strategy. Any claimed improvement must be attributed before it is claimed. |
| `hurst_switch` SOL daily → SOL hourly | **1st → 23rd** (+0.699 → −3.123) | A win on one series is not a win. |
| `ou_reversion` BTC daily | **1st on 6 trades, Q1 = 0.000** | Trade count must be a veto. |
| `voltarget` / `garch_voltarget` / `sma_regime` hourly | **numerically identical** | Search breadth was overstated. |
| Card rating distribution | **20 very-low, 23 low, 0 moderate** | The honest state of 43 documented strategies. |

**Conclusion.** On this evidence, a `/dso` whose primary job is "make strategies more profitable"
would be a machine for converting the 0.700 PBO into confident false claims. The design that
respects both the ask and the evidence is:

1. **Defect track (primary, always runs).** Lookahead, cost omission, degeneracy, fabricated card
   defaults, registry/card drift, tautological or zero-cost tests, data-quality traps, unverified
   figures. These are *correctness* findings with a real fix and no statistical ambiguity — the
   "correct any mistakes" half of the ask, and where the measured value is.
2. **Promotion track (secondary, gated, usually declines).** A champion–challenger climb whose
   holdout is CPCV held-out blocks, whose score is median/Q1 path Sharpe, and whose must-pass vetoes
   are: costs still in the P&L path, a no-lookahead test present, trade count ≥ evidence floor, card
   defaults matching code, no numerically identical twin, PBO not worsened. Edits may only be chosen
   from working-set blocks — never from the holdout. **"No promotion" is the expected and correct
   outcome, and must be reported as a first-class result rather than a failure.**

That split is what `/dso` implements.

## 7. Method, sources, and coverage limits

- **Method.** Five-neighborhood family framing (parent, siblings, children, adjacent, frontier) per
  the `concept-family-explorer` Step 1 taxonomy, then each child tagged against this repo by reading
  `backtester/core/`, `backtester/strategy_cards/`, and `research/`. The scoring, `/dr` research
  fan-out, concept-tree writes, and optimizer cascade of that skill were **not** run — the ask named
  one concrete artifact, and its engine requires agent fan-out and deep research.
- **Sources.** This repository's code, cards, and result CSVs. Named external methods (Deflated
  Sharpe Ratio, CSCV, White's Reality Check, Hansen SPA, minimum track record length) are referenced
  by name from prior knowledge and are **not** cited to a fetched source here.
- **Coverage limits.** §5.1's formula is deliberately not reproduced — verify against the paper
  before implementing. Market impact and capacity are dismissed as non-binding *at current size*
  ($12/rung), which stops being true at scale. Regime stratification is called a gap without
  evidence that it would explain the 1d/1h collapse; that is a hypothesis, not a finding.
- **Standing constraint.** No live order has ever been placed from this repo.
