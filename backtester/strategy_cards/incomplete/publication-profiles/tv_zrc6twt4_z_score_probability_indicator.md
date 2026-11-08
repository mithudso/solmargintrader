---

id: tv_profile_zrc6twt4

name: "Z-Score Probability Indicator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Relate a rolling price Z-score to corresponding price levels and an abbreviated normal-distribution cumulative table."

registry_key: null

runner: null

evaluation: null

---

# Z-Score Probability Indicator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Relate a rolling price Z-score to corresponding price levels and an abbreviated normal-distribution cumulative table.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The conventional Z-score concept is understandable, but the source-specific summarized-table/zone computation and probability interpretation remain ambiguous.

- Price source and dispersion convention
- Summarized-table/zone mapping
- No defined temporal retracement-probability model

## How it works

- Estimate mean and standard deviation over a selected sample, display standardized distance and map standardized levels back into price. Add an optional SMA of the Z-score and shade distribution zones; a summary table highlights the current zone.

## Outputs and intended use

- Use the display to inspect relative price extension. The author interprets cumulative distribution values as retracement probabilities, but a marginal normal CDF is not a future path/hitting probability.

## Parameters and stated settings

- Lookback defaults seventy-five; SMA is initially enabled with independently adjustable length. Zone fills, table and smoothing display can be toggled.

## Failure modes and caveats

- The text incorrectly treats a negative 2.31 Z with CDF 0.0104 as a majority-below/overbought example. Normality, stationarity and summarized-table approximation also limit interpretation.

## Missing information and implementation boundary

- Exact price source, standard-deviation convention, table averaging and zone boundaries are not supplied. No forecast horizon or transition model justifies retracement probabilities.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; code parity and complete market coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
It is defaulted to 75
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The SMA is optional but defaults to on.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Z-Score of -2.31
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
0.0104 probability zone
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
probability that SPY retraces to a Z-Score of 2 is around 0.9800
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zrc6twt4_z_score_probability_indicator](../tv_zrc6twt4_z_score_probability_indicator.md)

## Source

https://www.tradingview.com/script/zrc6tWT4-Z-Score-Probability-Indicator/

Publication ID: zrc6tWT4. Source SHA-256: db209b29af5d1d0154cf7c68ee2d16f434ca2f8abcb4be855b692ca482416d13. Raw-description SHA-256: 6fac2dabdee3c7e883a4765d56b0bccfe855844b49850fa79cc89caf4a12eb9d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
