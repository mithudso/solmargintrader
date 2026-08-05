---
name: cross-asset-generalisation-testing
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-4 top gap, CVS 4.55
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  Whether a strategy result is a property of the strategy or of the one price
  series you tested it on. Covers the ladder of generalisation evidence (same
  series → same asset different instrument → correlated asset → uncorrelated
  asset → different market entirely) and what each rung actually rules out; why
  a second asset is a weaker test than it looks when the assets are correlated;
  what to hold fixed and what to re-fit when porting a strategy; the parameter-
  stability signal that distinguishes a real effect from a fitted one; and how to
  report a partial generalisation honestly. Educational only — NOT financial advice.
keywords:
  - generalisation
  - cross-asset testing
  - out-of-sample
  - robustness check
  - replication
  - overfitting
  - parameter stability
  - instrument robustness
  - correlated assets
  - external validity
tags:
  - trading-and-investing
  - backtesting
  - validation
  - risk
---

# Cross-Asset Generalisation Testing

> **Educational information only — NOT financial, investment, or tax advice.**

Every backtest result is ambiguous between two explanations: **the strategy works**, or **this price
series happened to reward it**. Out-of-sample testing on the *same* series addresses time-period
overfitting. It does nothing about **asset overfitting** — and with one asset you cannot tell the two
apart.

**Scope.**

| For… | Go to |
|---|---|
| Walk-forward protocol, multiple testing, PBO | `references/trading-strategies-and-styles.md` §5; `references/ml-backtesting-pitfalls-and-production-systems.md` §8 |
| The measured results this reference generalises | `references/empirical-backtest-findings-log.md` §9 |
| Which *individual parameters* travel, and how to normalise the ones that don't | `references/asset-specific-vs-universal-parameters.md` |
| The selection window and refit cadence used when porting | `references/walk-forward-window-length-and-refit-cadence.md` |
| Sampling frequency as a fitted parameter that must travel too | `references/sampling-frequency-and-bar-aggregation.md` |
| Weighting and objective choices that also need to survive the port | `references/sleeve-weighting-and-objective-selection.md` |
| Acquiring a second asset's data | the dataset README at `~/Downloads/sol-backtest-data/README.md` |

## Contents

1. The generalisation ladder
2. Why a second asset is weaker evidence than it looks
3. What to hold fixed and what to re-fit
4. Parameter stability as the real signal
5. Worked example — a partial generalisation, reported honestly
6. Anti-patterns

---

## 1. The generalisation ladder

Not all "we tested it elsewhere" claims are equal. Ordered by strength:

| Rung | Test | Rules out | Does **not** rule out |
|---|---|---|---|
| 0 | In-sample on one series | nothing | everything |
| 1 | **Out-of-sample, same series** | time-period fitting | asset fitting, regime luck |
| 2 | **Same asset, different instrument** (spot → perp) | microstructure artifacts | the asset's own price path |
| 3 | **Correlated second asset** (SOL → ETH) | single-asset idiosyncrasy | crypto-wide regime luck |
| 4 | **Uncorrelated asset** (crypto → FX, equities) | asset-class dependence | the era |
| 5 | **Different era or market** | era dependence | — |

**Most published strategy work stops at rung 1 and is described as though it reached rung 3.** Naming
the rung you actually reached is the single cheapest honesty improvement available.

**Rung 2 is genuinely useful and routinely skipped.** Spot vs perpetual futures on the same asset have
different participants, fee structures, funding, and available leverage — so a result that survives the
switch is not an artifact of one venue's microstructure. It is cheap evidence because the data usually
already exists.

## 2. Why a second asset is weaker evidence than it looks

Adding one correlated asset buys less than the count suggests.

- **Crypto majors are highly correlated.** SOL, ETH and BTC share drawdowns and share bull runs. Testing
  on two of them is closer to **one and a bit** independent observations than to two.
- **The regime is shared.** A 2021–2026 crypto test spans one cycle. Two assets over the same window
  are two views of **the same macro path**, not two samples from the population of possible paths.
- **Effective sample size is what matters**, not the number of series. Correlated series inflate
  apparent evidence exactly the way autocorrelated bars inflate apparent significance
  (`sampling-frequency-and-bar-aggregation.md` §1).

**The practical consequence:** a second correlated asset is a **falsification tool, not a confirmation
tool**. If the result *breaks* on it, that is strong evidence of overfitting. If it *holds*, that is
weak evidence of generality. Treat asymmetrically — the failure is informative, the pass is not.

## 3. What to hold fixed and what to re-fit

The most common way a generalisation test is quietly rigged is by re-fitting too much on the new asset.

| Element | Port or re-fit? | Why |
|---|---|---|
| **Signal rule / logic** | **Hold fixed** | This is the hypothesis; changing it means testing a different strategy |
| **Protocol** (train window, selection rule, fill model, costs) | **Hold fixed** | Changing it changes what "out-of-sample" means |
| **Parameters** (periods, thresholds, weights) | **Re-fit — via the same procedure** | Re-fitting is legitimate; hand-picking is not |
| **Price-scale-dependent params** (grid range, tick sizing) | **Must be re-derived** | A $60–$83 range is meaningless on a $60,000 asset |
| **Costs** | **Re-fit to the venue** | Fee tiers and liquidity genuinely differ |

**The bright line:** re-fitting parameters *by running the identical selection procedure* on the new
asset is fair — you are testing whether the *method* travels. Choosing parameters by looking at what
works on the new asset is not a generalisation test at all; it is a fresh fit wearing the language of
validation.

## 4. Parameter stability as the real signal

**The most informative output of a cross-asset test is usually not the returns — it is whether the
selected parameters land in the same place.**

If a strategy is capturing a real effect, the parameters that capture it should be similar across
assets, because they reflect something structural. If the optimal lookback is 12 on one asset and 288
on another, the "effect" is probably being fitted to each series separately, and the returns agreeing
is coincidence.

Report both, and weight the parameter agreement more heavily:

- **Returns agree, parameters agree** → the strongest available evidence short of a new market.
- **Returns agree, parameters differ wildly** → suspicious. Likely two separate fits.
- **Returns differ, parameters agree** → the mechanism may be real but its payoff is regime- or
  asset-dependent. Often the most honest and useful outcome.
- **Both differ** → no evidence of generality.

## 5. Worked example — a partial generalisation, reported honestly

From `references/empirical-backtest-findings-log.md` §9.7, a concave+convex sleeve book tested out-of-sample
on **SOL spot** and then re-run identically on **SOL perpetual futures**:

| | SOL spot (48 mo) | SOL perp (47 mo) |
|---|---|---|
| Best blend weight | w_grid **0.65** | w_grid **0.60** |
| Blend worst month | −18.50% | −22.08% |
| Sleeve correlation | −0.107 | −0.112 |
| Blend beats both sleeves | ✅ | ✅ |

**Read it against §4:** the *parameters* agreed (0.65 vs 0.60) and so did the correlation (−0.107 vs
−0.112). Under §4's rubric that is the "returns agree, parameters agree" case — the strongest pattern
in the table.

**And read it against §1:** this is **rung 2**, not rung 3. Spot and perp track the *same underlying
asset*, so the price series are nearly identical and the test rules out only microstructure artifacts.
It is real evidence and it is **not** cross-asset generalisation. Describing it as "validated on two
markets" would be false.

**The honest one-line summary of that result:** *"survives an instrument change on the same asset."*
That sentence is what a rung-2 result entitles you to say.

### 5b. Rung 3 — a genuine cross-asset test on matched spans

The same protocol was run on **BTCUSDT** over the **identical 48-month OOS window** as SOL
(2022-08 → 2026-07). This is rung 3.

| | SOL (48 OOS) | BTC (48 OOS) | Agrees? |
|---|---|---|---|
| **Blend beats both sleeves** | ✅ | ✅ | **YES** |
| Modal trend sampling | 4-hourly (26/48) | 4-hourly (30/48) | **YES** |
| **Modal grid level count** | **10 (35/48)** | **10 (48/48)** | **YES** |
| Sleeve correlation | −0.107 | −0.131 | **YES** |
| Best blend weight | w_grid 0.65 | w_grid 0.75 | close |
| Grid worst month | −47.27% | −19.78% | mostly scale — see note |
| Trend worst month | −38.26% | −24.75% | mostly scale — see note |
| Blend worst month | −18.50% | −10.20% | mostly scale — see note |
| Trend standalone mean | **+4.49%** | **−1.00%** | **NO — sign flips** |

> **Note on the "scale" rows — the hypothesis was tested, and it only mostly holds.** Measured over the
> same 48 months, σ_SOL/σ_BTC = **1.91** (mean monthly realized vol 25.03% vs 13.13%). But the grid
> tail ratio is **2.39** and the trend tail ratio is **1.55** — the volatility ratio sits *between*
> them, so dividing by it leaves roughly a **5pp residual in opposite directions** for the two sleeves.
> The tails are largely but **not purely** scale; part of the difference is asset-specific. Full working
> in `references/asset-specific-vs-universal-parameters.md` §4.1.

**What generalised — four things, and they are the structural ones.** The blend beat both sleeves on
both assets. **4-hourly sampling was modal on both.** **A 10-level grid was modal on both — and on BTC
it won in every single one of 48 months.** And the sleeve correlation agreed closely (−0.107 vs
−0.131). Under §4's rubric this is the "returns and parameters both agree" cell — the strongest
pattern available short of a new market.

**What did not generalise: trend's standalone edge.** +4.49% on SOL, **−1.00%** on BTC. Anyone
concluding "trend-following works" from the SOL result would have been wrong. Note the asymmetry that
matters: the *pairing* survived while one *component's* profitability did not — which is precisely the
argument for holding a book rather than a single sleeve.

### 5c. The truncated-sample trap — a live example

**An earlier version of this section reported the opposite conclusion, from the same asset.** Run on
only the **31 months of BTC history available at the time** (2022-08 → 2025-03), the results read:

| | 31-month BTC | 48-month BTC | |
|---|---|---|---|
| Best weight | 0.90 | **0.75** | moved toward SOL's 0.65 |
| Sleeve correlation | **+0.198** | **−0.131** | **sign flipped** |
| Grid worst month | −11.27% | −19.78% | tail was understated |

On the truncated sample I concluded the correlation "flips sign across assets" and wrote it up as a
genuine cross-asset divergence. **The fuller sample falsified that: the sign flip was an artifact of
the missing 17 months**, which happened to exclude a period where the two sleeves diverged.

**The lesson is not "use more data" — everyone knows that.** It is sharper: **a truncated sample does
not merely add noise, it can produce a confident, coherent, wrong conclusion that survives sanity
checks.** The +0.198 reading was not an obvious outlier; it looked like a finding, and it was
interpreted as one. The only thing that caught it was extending the sample.

**Practical rule:** when comparing assets, **match the OOS windows exactly** before comparing anything.
A comparison across different spans is not a comparison of assets; it is a comparison of assets *and*
periods, and you cannot tell which produced the difference.

## 6. Anti-patterns

1. **Claiming a rung you did not reach.** Out-of-sample on one series is rung 1, however many months
   it covers (§1).
2. **Counting correlated assets as independent evidence.** Two crypto majors over one cycle are not
   two samples (§2).
3. **Treating a pass as confirmation.** A correlated second asset falsifies well and confirms poorly —
   the asymmetry is the whole point (§2).
4. **Re-fitting by hand on the new asset** and calling the result validation (§3).
5. **Porting price-scale-dependent parameters literally** — a fixed dollar grid range across assets of
   different price levels is meaningless (§3).
6. **Changing the protocol between assets**, so "out-of-sample" means two different things (§3).
7. **Reporting only returns.** Parameter agreement is the more informative signal (§4).
8. **Testing one extra asset and stopping.** The ladder has five rungs; one step up is one step (§1).
9. **Ignoring that both assets share an era.** Same-window tests share the macro path regardless of
   which assets they use (§2).

## References

Internal: `references/empirical-backtest-findings-log.md` §9.7 (the worked example and its OOS
protocol); `references/trading-strategies-and-styles.md` §5 (walk-forward, multiple testing);
`references/ai-and-ml-for-trading.md` §3.2 and `references/ml-backtesting-pitfalls-and-production-systems.md` §8 (PBO, deflated Sharpe, purged CV);
`references/sampling-frequency-and-bar-aggregation.md` §1 (effective sample size);
`references/sleeve-weighting-and-objective-selection.md` (what else must survive the port).

**Evidence note.** The §5 numbers are **first-party measurements** from this repo — reproduce with
`~/Downloads/sol-backtest-data/_scripts/run_walkforward_book.py`. The generalisation **ladder in §1 and
the fixed-vs-re-fit table in §3 are a framework**, not a cited result: they organise standard
validation reasoning into an explicit rung structure, and no external source is claimed for the
specific five-rung formulation. The asymmetry argument in §2 (correlated assets falsify well, confirm
poorly) follows from effective-sample-size reasoning and is stated without citation. **A genuine
cross-asset test (rung 3+) had not been completed at the time of writing** — which is precisely why
this reference exists, and why §5 is labelled partial rather than presented as validation.
