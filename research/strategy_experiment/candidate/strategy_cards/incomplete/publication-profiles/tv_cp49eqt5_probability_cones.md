---

id: tv_profile_cp49eqt5

name: "Probability Cones"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Project a distribution-shaped price envelope from an anchor and use departures from it to frame volatility and position-management questions."

registry_key: null

runner: null

evaluation: null

---

# Probability Cones

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Project a distribution-shaped price envelope from an anchor and use departures from it to frame volatility and position-management questions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Return transformation, drift, time-scaling law, distribution calibration and valid coverage probabilities are not specified.

- Return transformation, drift, time-scaling law, distribution calibration and valid coverage probabilities are not specified.

## How it works

- Sample history before an origin, select standard or Laplace distribution behavior and extrapolate upper/lower deviation cones. The anchor can remain fixed or follow price from a selected number of bars back.

## Outputs and intended use

- Inspect mean and deviation regions with an accompanying momentum measure. The author suggests reconsidering exits beyond the second deviation and avoiding new positions there, while explicitly denying a necessary mean-reversion assumption.

## Parameters and stated settings

- Lookback, forecast bars, anchor behavior, visible cone sets, individual upper/lower deviations, line styles and fills are configurable. Calendar-period origins are recommended.

## Failure modes and caveats

- The author cites normal-style 68/95/99.7 percent coverage, but that does not apply identically to Laplace distributions or guarantee empirical market containment. The text also suggests reversal propensity while denying guaranteed mean reversion.

## Missing information and implementation boundary

- Return transformation, drift, time-scaling law, distribution calibration and valid coverage probabilities are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed feature uses ordinary price/volume history; this is input-class support rather than verified implementation or data-cache parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Forecast a Standard or Laplace distribution.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
About 68% of price stays within the first deviation cones.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
About 95% of price stays within the second deviation cones.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
About 99.7% of price stays within the third deviation cones.
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
There is no mean reversion assumption when price deviates.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cp49eqt5_probability_cones](../tv_cp49eqt5_probability_cones.md)

## Source

https://www.tradingview.com/script/Cp49eQt5-Probability-Cones/

Publication ID: Cp49eQt5. Source SHA-256: 8b51657dd8db5e55a3ace97c832cfea581b45ce7342f7ef0336206e9c00855c3. Raw-description SHA-256: c0a77fd8c0587b1d65ab6708a650889b03c6fbcbfe5cdc401a3f51ec08b541a5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
