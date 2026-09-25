---
name: asset-specific-vs-universal-parameters
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-5 top gap, CVS 4.70
hub: trading-and-investing
version: "1.0.1"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  Which strategy parameters travel between assets and which must be re-fitted per
  asset — and how to tell before you find out expensively. Covers the three
  parameter classes (structural, scale-dependent, asset-specific) and the test
  that assigns a parameter to one; why price-scale and volatility-scale parameters
  must be NORMALISED rather than ported; measured evidence that some parameters
  were identical across SOL and BTC while a whole strategy's profitability flipped
  sign; the diagnostic value of a parameter that agrees across assets; and how to
  design a strategy so fewer of its parameters are asset-specific in the first
  place. Educational only — NOT financial advice.
keywords:
  - parameter generalisation
  - universal parameters
  - asset-specific tuning
  - normalisation
  - volatility scaling
  - price scale
  - re-fitting
  - cross-asset
  - structural parameters
  - dimensionless parameters
tags:
  - trading-and-investing
  - backtesting
  - validation
  - portfolio
---

# Asset-Specific vs Universal Parameters

> **Educational information only — NOT financial, investment, or tax advice.**

When a strategy moves to a new asset, some parameters carry over unchanged, some need rescaling, and
some have to be re-fitted from scratch. **Treating all three the same is how a working strategy breaks
silently on a new market** — and how a broken one gets rescued by a re-fit that hides the failure.

**Scope.**

| For… | Go to |
|---|---|
| Whether the *result* generalises at all, and the rung ladder | `references/cross-asset-generalisation-testing.md` |
| The measured SOL-vs-BTC numbers cited here | `references/empirical-backtest-findings-log.md` §9.7 |
| Sampling frequency specifically (the most-transferable parameter found) | `references/sampling-frequency-and-bar-aggregation.md` |
| Walk-forward window length and refit cadence as fitted parameters | `references/walk-forward-window-length-and-refit-cadence.md` |
| The selection *rule* itself as a fitted choice | `references/selection-rule-design.md` |
| Sleeve weights and the objective that determines them | `references/sleeve-weighting-and-objective-selection.md` |
| Volatility-based position sizing as a normalisation mechanism | `references/trading-risk-management.md` §2 |

## Contents

1. Three parameter classes
2. The test that assigns a parameter to a class
3. Normalisation — how to make a parameter travel
4. Measured: what travelled between SOL and BTC
5. Parameter agreement as a diagnostic
6. Designing for transferability
7. Anti-patterns

---

## 1. Three parameter classes

| Class | Definition | Behaviour across assets | Examples |
|---|---|---|---|
| **Structural** | Encodes something about *market behaviour in general* | Should transfer unchanged. If it doesn't, question the strategy | Sampling frequency, grid level count, lookback ratios |
| **Scale-dependent** | Denominated in price or volatility units | Must be **normalised**, never ported literally | Grid range in dollars, stop distance, position notional |
| **Asset-specific** | Depends on this asset's idiosyncratic behaviour | Must be re-fitted, and its need to be re-fitted is a warning | Anything that only works on one asset |

**The classes are a hypothesis you test, not a label you assign by intuition.** A parameter you
*believe* is structural but that changes wildly across assets was never structural — it was fitted, and
you had mislabelled it.

**The asset-specific class deserves suspicion in proportion to its size.** A strategy with two
structural parameters and one asset-specific one is plausible. A strategy where most parameters are
asset-specific is not a strategy; it is a fitting procedure that produces a different strategy per
asset, and its backtest across N assets is N separate in-sample fits.

## 2. The test that assigns a parameter to a class

Run the identical selection procedure on two or more assets and compare the *selected* values —
not the returns.

| Outcome | Class | What to do |
|---|---|---|
| Same value selected on both | **Structural** | Fix it. Stop fitting it. Treat as a finding. |
| Values differ but agree after normalising by price or volatility | **Scale-dependent** | Normalise it and it becomes structural |
| Values differ and no normalisation reconciles them | **Asset-specific** | Re-fit per asset — and count the extra degrees of freedom |

**The crucial discipline:** the selection procedure must be **identical** across assets. If you tuned
harder on one asset, or looked at the result before choosing, the comparison is meaningless
(`cross-asset-generalisation-testing.md` §3).

**Also compare the *modal* selection across a walk-forward**, not a single fit. A parameter selected
in 48 of 48 rolling windows on one asset and 35 of 48 on another is far stronger evidence than two
single point estimates that happen to match.

## 3. Normalisation — how to make a parameter travel

Most parameters that look asset-specific are actually scale-dependent and become transferable once
expressed in the right units.

| Instead of… | Express as… | Why |
|---|---|---|
| Grid range `$60–$83` | Multiple of prior-period range, or ±k×σ | A dollar range is meaningless on a $60,000 asset |
| Stop at `$2.50` | k × ATR, or a percentage | Ports across price levels and volatility regimes |
| Position size `100 units` | Fraction of capital, or vol-targeted notional | Otherwise risk scales with price, not intent |
| Lookback `24 bars` | 24 bars **× the bar interval** = wall-clock lookback | A period without its interval is not a specification (`sampling-frequency-and-bar-aggregation.md` §2) |
| Threshold `$500 move` | Multiple of realized volatility | Absolute moves are not comparable across assets |

**The general rule: make the parameter dimensionless.** A ratio, a multiple of volatility, or a
fraction of capital travels; a quantity denominated in dollars or units does not.

**Volatility normalisation is the highest-leverage single change**, because assets differ in volatility
far more than in structure. Two assets with the same *shape* of behaviour and different amplitudes will
look like they need different parameters until you divide by σ.

**But normalisation is a hypothesis, not a guarantee — verify that it actually reconciles the
difference.** In the measured case (§4.1) dividing by the volatility ratio removed most of the gap and
left a residual of about 5 percentage points, pointing in *opposite* directions for two sleeves on the
same pair of assets. A parameter is scale-dependent only if the scale division genuinely reconciles it;
if a residual survives, part of the difference is asset-specific and normalising will hide that.

## 4. Measured: what travelled between SOL and BTC

Identical protocol, identical 48-month out-of-sample window (2022-08 → 2026-07), same selection
procedure on both assets (`empirical-backtest-findings-log.md` §9.7):

**Selected parameters** — these are what §2's test actually classifies:

| Parameter | SOL | BTC | Class |
|---|---|---|---|
| **Modal grid level count** | **10** (35/48 windows) | **10** (48/48 windows) | **Structural** |
| **Modal trend sampling** | **4-hourly** (26/48) | **4-hourly** (30/48) | **Structural** |
| Best blend weight | 0.65 | 0.75 | Near-agreement — weakly structural |

**Results, for context** — outcomes, not settings you choose, so the three-class taxonomy does **not**
apply to them:

| Result | SOL | BTC | |
|---|---|---|---|
| Sleeve correlation | −0.107 | −0.131 | agrees |
| Blend beats both sleeves | ✅ | ✅ | agrees |
| Grid worst month | −47.27% | −19.78% | see §4.1 |
| Trend worst month | −38.26% | −24.75% | see §4.1 |
| **Trend standalone mean** | **+4.49%** | **−1.00%** | **sign flips** |

**Two clean structural findings.** A **10-level grid was modal on both assets**, winning every one of
48 BTC windows. **4-hourly sampling was modal on both.** Neither was assumed; both were selected
independently per asset by the same procedure, and both landed in the same place. Under §2's test that
is as strong as this evidence gets.

**One genuinely asset-specific result.** Trend's standalone profitability **flipped sign**: +4.49% on
SOL, −1.00% on BTC. That is not a scaling artifact and no normalisation fixes it. **A strategy's edge
can be asset-specific even when its parameters agree** — the settings transferred, the profitability
did not.

**Scope:** two assets, one venue, 48 months. Enough to demonstrate the classification method and to
show that some parameters do transfer; **not** enough to claim 10 levels or 4-hour sampling is correct
in general.

### 4.1 Testing the scale hypothesis instead of assuming it

The obvious reading of the worst-month rows is "SOL is about twice as volatile, so its tails are about
twice as deep — pure scale." **That reading was measured and it is only partly right.**

Mean monthly realized volatility over the same 48 months (stdev of hourly log returns, scaled by
√hours-in-month): **SOL 25.03%, BTC 13.13% → σ_SOL/σ_BTC = 1.91.** Dividing SOL's tails by 1.91:

| | SOL raw | SOL ÷1.91 | BTC | Residual |
|---|---|---|---|---|
| Grid worst month | −47.27% | **−24.79%** | −19.78% | **5.01pp worse** than scale predicts |
| Trend worst month | −38.26% | **−20.06%** | −24.75% | **4.69pp better** than scale predicts |

**Normalisation removes most of the gap but not all of it, and the residuals point in opposite
directions.** The raw grid ratio is 2.39 and the raw trend ratio is 1.55; the volatility ratio, 1.91,
sits between them. So one sleeve's tail is deeper than volatility explains and the other's is
shallower. **The tails are therefore not purely scale** — there is an asset-specific component in both,
and it has a different sign per sleeve.

**This is the section's own method turned on itself, and it changed the answer.** The scale
classification was an assumption until it was computed; computing it downgraded "these converge" to
"these mostly converge, with a residual that does not." **Run the normalisation, do not assert it** —
a parameter or result is only scale-dependent if dividing by the scale actually reconciles it.

## 5. Parameter agreement as a diagnostic

**A parameter that agrees across assets is evidence the strategy is capturing something real.** A
parameter that must be re-fitted per asset is evidence you may be fitting noise per asset.

Use it as a model-selection criterion, not just a validation step:

- **Prefer the variant whose parameters agree across assets**, even at some cost in single-asset
  backtest return. Agreement is the scarcer and more informative property.
- **Count asset-specific parameters as degrees of freedom multiplied by asset count.** Three
  asset-specific parameters across four assets is twelve fitted values, and multiple-testing
  expectations should be adjusted accordingly (`algorithmic-and-quant-trading.md` §5.3).
- **A parameter that agrees on two assets and breaks on the third is the most informative outcome
  available** — it localises where the assumption fails, which is more useful than uniform agreement.

## 6. Designing for transferability

You can reduce how many parameters are asset-specific *by construction*:

1. **Express everything dimensionlessly** (§3). This is the single biggest lever.
2. **Derive scale parameters from the data at runtime** rather than fixing them — a grid range set from
   the prior period's range self-adjusts per asset, and is the same rule everywhere. It is *also* the
   no-lookahead discipline, so you get both properties from one design choice.
3. **Prefer ratios to absolutes** — fast/slow ratio rather than two independent periods.
4. **Volatility-target position sizing** rather than fixed notional, so exposure means the same thing
   on every asset (`trading-risk-management.md` §2).
5. **Fewer parameters.** Every parameter is a chance to be asset-specific. The transferability argument
   is one more reason simplicity wins.

## 7. Anti-patterns

1. **Porting a dollar-denominated parameter to a different price level.** A $60–$83 grid range on a
   $60,000 asset is not a strategy (§3).
2. **Re-fitting everything on the new asset and calling it validation.** That is N in-sample fits (§1).
3. **Assigning parameter classes by intuition** instead of by running the test (§2).
4. **Comparing raw drawdowns across assets** without normalising for volatility (§4).
5. **Quoting a single fit as "the selected parameter"** instead of the modal selection across a
   walk-forward (§2).
6. **Assuming agreeing parameters imply a universal edge.** SOL and BTC agreed on both structural
   parameters and nearly agreed on the third, and trend's profitability still flipped sign (§4).
7. **Asserting that a difference is "just scale" without dividing by the scale.** Measured, the
   normalisation left a ~5pp residual — in *opposite* directions for the two sleeves (§4.1).
8. **Ignoring the degrees-of-freedom cost of asset-specific parameters** in multiple-testing
   adjustments (§5).
9. **Fixing scale parameters at design time** rather than deriving them from data at runtime (§6).

## References

Internal: `references/cross-asset-generalisation-testing.md` (the rung ladder and what to hold fixed);
`references/empirical-backtest-findings-log.md` §9.7 (the measured SOL-vs-BTC comparison);
`references/sampling-frequency-and-bar-aggregation.md` §2 (period × interval);
`references/sleeve-weighting-and-objective-selection.md` (weights as parameters);
`references/trading-risk-management.md` §2 (volatility-targeted sizing);
`references/algorithmic-and-quant-trading.md` §5.3 (degrees of freedom, multiple testing).

**Evidence note.** The §4 and §4.1 tables are **first-party measurements**. Reproducing them takes two
steps, because `~/Downloads/sol-backtest-data/_scripts/run_walkforward_book.py` is **SOL-only as
shipped** — it has no symbol argument. The underlying `engine.load_bars()` does take
`symbol="BTCUSDT"`, and the BTC figures were produced by driving it with that symbol over the matched
2022-08 → 2026-07 window; the §4.1 volatility ratio is computed directly from
`spot/klines/1h/{SOL,BTC}USDT-1h-*.zip` as the stdev of hourly log returns scaled by √hours-in-month.
**Two assets, one venue, 48 months, two strategy families.** That supports the *method* in §2 and the
observation that some parameters transferred; it does **not** establish any specific value as
universal, and a third asset could break either structural finding. The three-class taxonomy in §1 and the normalisation table
in §3 are a **framework**, stated without external citation — they organise standard practice rather
than reporting a result. **No parameter value here is a recommendation.**
