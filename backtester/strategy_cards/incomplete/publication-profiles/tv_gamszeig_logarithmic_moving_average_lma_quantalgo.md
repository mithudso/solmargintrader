---

id: tv_profile_gamszeig

name: "Logarithmic Moving Average (LMA) [QuantAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Logarithmic Moving Average converts a logarithmically weighted price average into a trend-quality-adjusted slope oscillator. Its aim is to favor recent data while distinguishing cleaner directional movement from weaker drift. Optional log-return momentum further amplifies agreement; this is a designed weighting rule rather than evidence of statistical significance or higher continuation probability."

registry_key: null

runner: null

evaluation: null

---

# Logarithmic Moving Average (LMA) [QuantAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Logarithmic Moving Average converts a logarithmically weighted price average into a trend-quality-adjusted slope oscillator. Its aim is to favor recent data while distinguishing cleaner directional movement from weaker drift. Optional log-return momentum further amplifies agreement; this is a designed weighting rule rather than evidence of statistical significance or higher continuation probability.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** LMA/ten-bar slope is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Weight closing prices by inverse squared log of age plus steepness, normalize into an average and measure its percentage slope over a fixed lag.
- Multiply slope by a half-base/half-R-squared trend-quality factor; optionally apply a same-direction momentum multiplier.
- For ages i=0..N-1,w_i=1/log(i+steepness)^2;LMA=sum(w_i*close[i])/sum(w_i). Require i+steepness>0 and not1. Slope=100*(LMA-LMA[10])/LMA[10] for nonzero lagged value. Final quality/momentum/smoothing excluded.

## Outputs and intended use

- Positive/negative values convey bullish/bearish momentum, zero crosses suggest regime transitions and threshold zones flag stronger readings; gradient/bar colors and latest classification aid inspection.
- Usable scope: LMA/ten-bar slope. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Slope uses a ten-bar lag. Long/short thresholds default +0.5/-0.5; source calls ±1 strong extremes. Period, steepness, smoothing and momentum controls lack full defaults.

## Failure modes and caveats

- Analytical: log weights need valid domain/normalization, trend-quality weighting is not calibrated predictive confidence, and optional amplification changes scale.

## Missing information and implementation boundary

- R-squared calculation window, steepness bounds, momentum annualization/multiplier, smoothing and full defaults are not fully disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
w = 1.0 / math.pow(math.log(i + steepness), 2)
```

### E2: mechanism, parameters, readiness

```text
lmaSlope = (lma - lma[10]) / lma[10] * 100
```

### E3: mechanism, readiness

```text
signal = lmaSlope * (0.5 + rSquared * 0.5)
```

### E4: parameters, readiness

```text
default 0.5
```

### E5: parameters, readiness

```text
default -0.5
```

### E6: parameters, readiness

```text
±1.0
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
The indicator's core innovation lies in its logarithmic weighting system, where weights are calculated using the formula: [pine]w = 1.0 / math.pow(math.log(i + steepness), 2)[/pine] The steepness parameter controls how aggressively recent data is prioritized over historical data, creating a dynamic weight decay that can be fine-tuned for different trading styles. This logarithmic approach provides more nuanced weight distribution compared to exponential moving averages, offering better responsiveness while maintaining stability.
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
The LMA calculation combines multiple sophisticated components. First, it calculates the logarithmic weighted average of closing prices. Then it measures the slope of this average over a 10-period lookback: [pine]lmaSlope = (lma - lma[10]) / lma[10] * 100[/pine] The system also incorporates trend quality assessment using R-squared correlation analysis of log-transformed prices, measuring how well the price data fits a linear trend model over the specified period.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gamszeig_logarithmic_moving_average_lma_quantalgo](../../tv_gamszeig_logarithmic_moving_average_lma_quantalgo.md)

## Source

https://www.tradingview.com/script/gaMszEIG-Logarithmic-Moving-Average-LMA-QuantAlgo/

Publication ID: gaMszEIG. Source SHA-256: 632a7de0a43ba26a889947244e982a73891441b5a8e26245a64b65bde426f01c. Raw-description SHA-256: 06afa9604eb84cb87a2bc7aaf6e4bc27eccde919cfb0a82497395dfa035651f8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
