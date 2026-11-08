---

id: tv_profile_7prbcbjk

name: "Stochastic Heat Map"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Stochastic Heat Map condenses momentum across many lookback horizons into a layered background and a composite oscillator. Shorter stochastics occupy lower rows and longer stochastics higher rows, so the reader can distinguish a short-term extreme from agreement across the full range of horizons. The average reading becomes a fast line with a slower follower, offering a simpler summary alongside the detailed heat map. Optional candle coloring carries that summary onto the main chart. The source presents momentum extremes as the key interpretation, without specifying reversal trades or treating every extreme as an immediate entry."

registry_key: null

runner: null

evaluation: null

---

# Stochastic Heat Map

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Stochastic Heat Map condenses momentum across many lookback horizons into a layered background and a composite oscillator. Shorter stochastics occupy lower rows and longer stochastics higher rows, so the reader can distinguish a short-term extreme from agreement across the full range of horizons. The average reading becomes a fast line with a slower follower, offering a simpler summary alongside the detailed heat map. Optional candle coloring carries that summary onto the main chart. The source presents momentum extremes as the key interpretation, without specifying reversal trades or treating every extreme as an immediate entry.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Stochastic-family lengths, Waves weighting and following-line smoothing are missing.

- Stochastic-family lengths, Waves weighting and following-line smoothing are missing.

## How it works

- Calculate a family of stochastic readings at incremented lengths and color each horizontal row by its value.
- Average the family into a fast oscillator and apply a slower following line.
- A Waves option changes the weighting/increment method.

## Outputs and intended use

- Stacked color rows show cross-horizon momentum extremes.
- Fast/slow lines and optional bar colors summarize the underlying readings.

## Parameters and stated settings

- The family contains 28 stochastic oscillators.
- MA smoothing method, theme, Increment, Smooth Fast, Smooth Slow, Paint Bars and Waves are inputs; numeric length defaults are absent.

## Failure modes and caveats

- Averaging highly correlated lookbacks does not provide independent confirmations.
- Momentum can remain extreme during trends, so heat-map saturation alone does not define a reversal.

## Missing information and implementation boundary

- Exact stochastic variants, starting length/increment defaults, Waves weighting, smoothing defaults and entry/exit predicates are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Stochastic price-range calculations and smoothing use OHLCV data; exact implementation is not available.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
A series of 28 stochastic oscillators
```

### E2: mechanism, outputs_and_use

```text
average of the 28 stochastics has been taken and then used to plot the fast oscillator line
```

### E3: outputs_and_use

```text
Lower lines are shorter term stochastics and higher lines are longer term stochastics.
```

### E4: parameters

```text
Waves: toggle method to weight/increment stochastics
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_7prbcbjk_stochastic_heat_map](../tv_7prbcbjk_stochastic_heat_map.md)

## Source

https://www.tradingview.com/script/7PRbCBjk-Stochastic-Heat-Map/

Publication ID: 7PRbCBjk. Source SHA-256: 0be385a05ac02bac007c2fb5484a8e5155b0259ca96a242b62c2e00158ef2670. Raw-description SHA-256: ee556c56dd22c3d6010ff11d6ead18b61bdd7062d1633e9f046ad4051389eecc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
