---
id: discount_to_anchor
name: Discount to a Fair-Value Anchor
kind: exposure-strategy
status: spec-only
family: mean-reversion
summary: Buy in proportion to the discount against a fair-value anchor. Documented as a duplicate of the existing mean-reversion family rather than registered.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  anchor_window: {default: 100, type: int, desc: "window of the moving anchor"}
  entry_discount: {default: 0.05, type: float, desc: "fractional discount to the anchor required to take exposure"}
presets: {}
---
# Discount to a Fair-Value Anchor

> **Deliberately not registered.** `data_available: true` — the data exists and this *could*
> be run today. It is not run because doing so would add a fifth name for a mechanism this
> repo already carries four names of, and would inflate the multiple-testing denominator
> without adding a hypothesis. That is a decision, not an omission.

## The proposed mechanism

```
discount_t = (anchor_t - price_t) / anchor_t
target_t   = f(discount_t)            exposure rises as the discount deepens
```

with the anchor being some fair-value reference — a slow moving average, an
Ornstein-Uhlenbeck long-run mean, a Kalman-filtered level, or a NAV where one genuinely
exists.

## Why it is not a distinct mechanism

Write the existing z-score rule and this one side by side, both as a distance from a moving
anchor divided by a scale:

```
zscore:            (price_t - MA_t) / stdev_t
bb_reversion:      (price_t - MA_t) / (k * stdev_t)
discount_to_anchor: (MA_t - price_t) / MA_t
```

All three are the same numerator over a different denominator. Sign is a convention;
`stdev`, `k * stdev` and `MA` are three choices of scale. **The mechanism is "price is far
below a trailing anchor, take exposure" in every case**, and the only thing that differs is
what "far" is measured in.

That distinction has already been tested here, and the result is the reason this card exists
rather than a registry entry. `research/RANKED_LISTS.md` finding 4 is a within-mechanism
natural experiment on exactly this axis:

| Configuration | OOS Sharpe | OOS return | OOS trades |
|---|---|---|---|
| `zscore_20_-2` | +0.699 | **+41.3%** | 10 |
| `bb_reversion_20_2` | +0.193 | **−4.8%** | 10 |

Provably the same mechanism from source, separated only by a standard-deviation convention —
a 2.6% difference in entry threshold. **Identical trade count, and a 46-percentage-point gap
in outcome.** Gate both with a regime filter and they become numerically identical to four
decimal places, because the gate suppresses exactly the bars where the threshold difference
lived.

The conclusion the repo drew from that is the one that applies here: whatever separated those
two rows was not a property of the mechanism. Adding a third denominator would produce a
third row in the same family, with its own arbitrary threshold, competing in a search whose
PBO at the daily horizons is **0.700** — above the 0.500 noise line, meaning selection by
in-sample rank is measurably worse than picking at random.

## What would make it distinct — and what would not

An anchor that carries **information the price series does not already contain** would be a
genuinely different hypothesis:

- **A NAV-style anchor where one actually exists.** For a pool token the redemption value is
  a fact about the pool, not a transform of the price. That case is already carded, as
  `jlp_vs_sol_relative_value.md`.
- **A cross-sectional anchor** — fair value from a peer basket rather than the asset's own
  history. That is a different mechanism, and it is carded as
  `pairs_cointegration.md` and `kalman_hedge_ratio.md`.
- **An on-chain valuation anchor** (realised price, MVRV) — carded as
  `mvrv_nupl_valuation.md`.

What would *not* make it distinct: any anchor computed from the asset's own trailing price.
A moving average, an EWMA, a VWAP, a linear-regression channel midpoint and an OU long-run
mean are all trailing summaries of the same series, and swapping between them changes the
scale, not the claim. `vwap_reversion` and `ou_half_life_sizing` already occupy two of those
slots.

So the honest reading is that the design space this idea points at is **already covered by
five registered or carded mechanisms**, and the remaining degrees of freedom are exactly the
ones finding 4 showed to be noise.

## The failure mode, recorded because it is the interesting part

**A trending-down anchor.** A trailing anchor follows price down, so "buy the discount"
becomes "buy every step of a bear market", and a convex sizing function `f` makes it
"buy progressively harder all the way down" — a martingale in everything but name. This is
not hypothetical for this asset: the project's own series runs from a $261.99 high to
roughly $73, and every mean-reversion configuration in the medium-horizon table lost money
across that leg unless it was gated.

The gate is what matters, not the anchor. `all(sma_regime+zscore)` and
`all(sma_regime+bb_reversion)` scored identically once gated, which says the regime filter
was doing the work and the reversion rule was interchangeable.

## Lookahead traps, if anyone does build it

1. **An anchor fitted on the full sample.** An OU long-run mean or a regression midpoint
   estimated over all bars encodes the future into every early bar. It must be re-estimated
   from visible bars only, per bar.
2. **A centred moving average.** A `center=True` rolling mean at bar *t* reads bars after
   *t*. It looks like an ordinary anchor and produces a spectacular result.
3. **Warm-up shorter than the anchor.** With `anchor_window` 100 the first usable bar is 100,
   not 1, and an anchor computed on a partial window is a different and much noisier
   statistic than the one documented.

## Likelihood of success: very-low

*Basis: base-rate. Not measured here — it was never run, deliberately. The rating comes from
the measured base rate of the family it belongs to, which is the honest source when the
mechanism is a restatement of things this repo has already evaluated 4 ways.*

At the medium horizon `zscore_20_-2` medians **+0.036** under CPCV with 52% of paths positive,
and `bb_reversion_20_2` medians **−0.114**. At the long horizon both median **+0.120** with
the highest parameter-perturbation ratio in the entire 72-configuration population (1.33 —
the only two above 1.0). Three independent flags already point at that pair: the algebra, the
46-point natural experiment, and the perturbation ratio.

A third denominator on the same numerator inherits that, and there is no reason to expect it
to inherit anything else.

## Research note

An external literature pass on discount-to-anchor construction was commissioned and did not
return within this session, so this card rests on the repo's own measured evidence rather
than on published results. That evidence is local, machine-verified against its own result
CSVs, and directly on point — but the absence of the literature review is stated here rather
than papered over. If it lands and contradicts this reading, this card should be revisited
rather than trusted.
