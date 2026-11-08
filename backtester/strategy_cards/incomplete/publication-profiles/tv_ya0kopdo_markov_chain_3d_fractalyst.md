---

id: tv_profile_ya0kopdo

name: "Markov Chain [3D] | Fractalyst"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Markov Chain [3D] summarizes recent transitions among detected bullish, bearish and neutral regimes. Its animated state diagram is paired with a numeric bias output intended for connecting regime filters to separately specified systematic trading rules."

registry_key: null

runner: null

evaluation: null

---

# Markov Chain [3D] | Fractalyst

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Markov Chain [3D] summarizes recent transitions among detected bullish, bearish and neutral regimes. Its animated state diagram is paired with a numeric bias output intended for connecting regime filters to separately specified systematic trading rules.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The detected-state-to-bias mapping is explicit, but the core regime boundaries, normalization/smoothing and transition pseudocount remain undisclosed.

- Define normalized regime boundaries, price-return transform, normalization/smoothing and Laplace pseudocount.

## How it works

- Export detected Bull as +1, Neutral as 0 and Bear as -1. This is direct state encoding; transition-probability estimates visualize the observed transition history and are not specified as selecting that bias.
- The engine standardizes price returns or three equally weighted custom series with rolling Z-scores, classifies normalized values into market states and smooths combined custom classifications. On confirmed bars it counts transitions in a rolling matrix and applies Laplace smoothing to estimate conditional next-state probabilities.
- Spheres represent states, self-loops persistence and directed arrows state changes. The description also contains an extensive separate feature-export script: centered oscillators, moving-average displacement, directional comparisons, volume transforms and range/return volatility are plotted for selection as inputs. That code does not supply the Markov classification algorithm itself.

## Outputs and intended use

- Bias is +1 bullish, zero neutral and -1 bearish. A sample consumer enters long when bias equals one and closes otherwise. Probability arrows describe observed conditional transitions, while bias alone exports a hard state rather than the complete probability vector.

## Parameters and stated settings

- Lookback defaults to 100 and controls both detection and probability history. Custom mode accepts three selected series with equal weights. The included exporter defines common lengths 14, 20 and 50, and produces 52 numbered plots despite surrounding 45-plus branding.

## Failure modes and caveats

- Estimated transition frequencies can shift across regimes and do not guarantee the next state. Confirmed-bar updates are an author claim, not an independently verified non-repainting guarantee. Several exporter names do not match conventional definitions: its MAMA is an ordinary EMA and its Klinger is a difference of smoothed price-times-volume.

## Missing information and implementation boundary

- Regime Z-score thresholds, adaptive normalization, price-return convention, combined-state smoothing and Laplace pseudocount are undisclosed. Exported bias is explicitly the detected regime label; no transition-probability-to-bias algorithm is claimed.

## Data requirements

Required inputs: ohlcv, optional caller-selected indicator series.

Repository input-class support: available. Default price-return mode and the supplied technical-feature exporter use OHLCV. Arbitrary custom sources require their own separately specified data contracts.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, outputs_and_use, risks, readiness

```text
Lookback Period (default: 100)
```

### E2: mechanism, parameters, outputs_and_use, risks, readiness

```text
These will be normalized and combined (each with equal weight)
```

### E3: mechanism, parameters, outputs_and_use, risks, readiness

```text
using Laplace smoothing for numerical stability
```

### E4: mechanism, parameters, outputs_and_use, risks, readiness

```text
bias value (+1 for Bullish, -1 for Bearish, 0 for Neutral)
```

### E5: mechanism, parameters, outputs_and_use, risks, readiness

```text
length_14 = input.int(14
```

### E6: mechanism, parameters, outputs_and_use, risks, readiness

```text
length_20 = input.int(20
```

### E7: mechanism, parameters, outputs_and_use, risks, readiness

```text
length_50 = input.int(50
```

### E8: mechanism, parameters, outputs_and_use, risks, readiness

```text
Total Indicators: 52
```

### E9: mechanism, parameters, outputs_and_use, risks, readiness

```text
mama = ta.ema(close, length_20)
```

### E10: mechanism, parameters, readiness

```text
automatically exports a [b]bias value (+1 for Bullish, -1 for Bearish, 0 for Neutral)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_megaphone](../tv_method_megaphone.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)
- [tv_ya0kopdo_markov_chain_3d_fractalyst](../tv_ya0kopdo_markov_chain_3d_fractalyst.md)

## Source

https://www.tradingview.com/script/yA0KOPDO-Markov-Chain-3D-Fractalyst/

Publication ID: yA0KOPDO. Source SHA-256: b907cd8060e515a34cf4e3f634d2114529041d65478846d93c735579c28c7540. Raw-description SHA-256: 6b5e122f1c4e299d0326aff0e10f246ee74ec096a289230d740e5964b9abc269.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
