---

id: tv_profile_ksmls0hh

name: "Supertrend Parameter Sensitivity 3D [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Supertrend Parameter Sensitivity evaluates a grid of ATR lengths and multipliers to reveal parameter robustness. It aims to distinguish an isolated best historical result from a neighborhood of comparatively strong results, reducing reliance on a single optimized peak. Each grid cell maintains an independent always-in-market long/short Supertrend simulation. The tool visualizes historical diagnostics rather than delivering a deployable optimization guarantee. Even a broad good-performing region can be an artifact of the selected market period."

registry_key: null

runner: null

evaluation: null

---

# Supertrend Parameter Sensitivity 3D [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Supertrend Parameter Sensitivity evaluates a grid of ATR lengths and multipliers to reveal parameter robustness. It aims to distinguish an isolated best historical result from a neighborhood of comparatively strong results, reducing reliance on a single optimized peak. Each grid cell maintains an independent always-in-market long/short Supertrend simulation. The tool visualizes historical diagnostics rather than delivering a deployable optimization guarantee. Even a broad good-performing region can be an artifact of the selected market period.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Exact strategy/fill and metric conventions are not disclosed.

## How it works

- Run independent Supertrend states and flip long/short at direction changes for each length/multiplier pair.
- Calculate selected trade metric and project it as a surface/heatmap.
- Identify best individual cell and highest-average local neighborhood.

## Outputs and intended use

- 3D surface, metric heatmap, result-distribution histogram and trade-count tooltips support sensitivity research.

## Parameters and stated settings

- 100 combinations in10×10 grid; stable-area neighborhood3×3; nine performance metrics.
- Length/multiplier starts/steps, primary plot settings, metric and visual geometry are configurable.

## Failure modes and caveats

- Selection on the same history creates multiple-testing bias.
- Costs, fill delay and open trades can materially change rankings.

## Missing information and implementation boundary

- Exact Supertrend recurrence/ATR convention, simulation fills/costs, metric edge cases, grid defaults and boundary-neighborhood handling absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Grid calculations and synthetic trades use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
100 simultaneous Supertrend backtests
```

### E2: parameters

```text
10x10 matrix
```

### E3: parameters

```text
3x3 parameter window
```

### E4: parameters

```text
9 different metrics
```

### E5: mechanism, readiness

```text
Always-in-Market
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ksmls0hh_supertrend_parameter_sensitivity_3d_luxalgo](../tv_ksmls0hh_supertrend_parameter_sensitivity_3d_luxalgo.md)
- [tv_method_trailing_stop](../../tv_method_trailing_stop.md)

## Source

https://www.tradingview.com/script/kSMLs0Hh-Supertrend-Parameter-Sensitivity-3D-LuxAlgo/

Publication ID: kSMLs0Hh. Source SHA-256: 757075782a3968eeae26854cb9c817c74a24236977ae6c2d8e8e6315d6fb1f29. Raw-description SHA-256: bf0e6917766708ea04501b4fc079004c6724b9a47641598b0f6b35a56392fd0a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
