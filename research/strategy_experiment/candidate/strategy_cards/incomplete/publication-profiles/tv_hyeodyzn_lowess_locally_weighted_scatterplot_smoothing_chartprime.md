---

id: tv_profile_hyeodyzn

name: "LOWESS (Locally Weighted Scatterplot Smoothing) [ChartPrime]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "LOWESS ChartPrime combines local-regression smoothing with an adaptive Gaussian moving average and pivot-break tracking. It seeks to show a smooth trend while retaining discrete structure events through pivot lines and consecutive-break counts. The randomly colored scatter points are a visualization choice, not additional predictive inputs."

registry_key: null

runner: null

evaluation: null

---

# LOWESS (Locally Weighted Scatterplot Smoothing) [ChartPrime]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

LOWESS ChartPrime combines local-regression smoothing with an adaptive Gaussian moving average and pivot-break tracking. It seeks to show a smooth trend while retaining discrete structure events through pivot lines and consecutive-break counts. The randomly colored scatter points are a visualization choice, not additional predictive inputs.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Gaussian weights/volatility mapping, LOWESS kernel/degree, right-pivot count, breakout reset and color rules are not fully specified.

- Gaussian weights/volatility mapping, LOWESS kernel/degree, right-pivot count, breakout reset and color rules are not fully specified.

## How it works

- Construct a volatility-adapted Gaussian average using ATR and standard deviation, then smooth it with weighted local regression.
- Detect pivots using left/right counts, draw their levels and monitor price crossovers for breakout counting.

## Outputs and intended use

- Inspect smoothed-line direction/color, broken pivot levels and optional streak count; scatter spread provides qualitative volatility context.

## Parameters and stated settings

- Length defaults 30, Pivot Length left-bar input 5, Count Breaks false and Gaussian Scatterplot true. Right-bar count/default is not disclosed.

## Failure modes and caveats

- Analytical: pivot markers require confirmation and adaptive/local smoothing still lags; random colors have no stable signal meaning.

## Missing information and implementation boundary

- Gaussian weights/volatility mapping, LOWESS kernel/degree, right-pivot count, breakout reset and color rules are not fully specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
default: 30
```

### E2: parameters, readiness

```text
default: 5
```

### E3: parameters, readiness

```text
default: false
```

### E4: parameters, readiness

```text
default: true
```

### E5: mechanism, readiness

```text
Gaussian weighting with volatility adaptation using ATR and standard deviation.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hyeodyzn_lowess_locally_weighted_scatterplot_smoothing_chartprime](../tv_hyeodyzn_lowess_locally_weighted_scatterplot_smoothing_chartprime.md)

## Source

https://www.tradingview.com/script/hyeoDyZn-LOWESS-Locally-Weighted-Scatterplot-Smoothing-ChartPrime/

Publication ID: hyeoDyZn. Source SHA-256: 4a783be6b97a2be1f91d2d4ac8818f925381a371b177d3672c919e3a968071f2. Raw-description SHA-256: 2471d2805000d56e1c4694c4b6801f8dae5d95b51fdd9c74fcea3ca7d7ba2139.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
