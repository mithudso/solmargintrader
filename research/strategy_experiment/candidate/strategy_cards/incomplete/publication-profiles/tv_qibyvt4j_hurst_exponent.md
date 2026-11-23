---

id: tv_profile_qibyvt4j

name: "Hurst Exponent"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Estimate persistence or mean-reverting tendency in a market series using rescaled-range analysis across several sample sizes."

registry_key: null

runner: null

evaluation: null

---

# Hurst Exponent

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate persistence or mean-reverting tendency in a market series using rescaled-range analysis across several sample sizes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Input transformation, partition overlap, standard-deviation convention, regression weighting and degenerate-sample handling are unspecified.

- Input transformation, partition overlap, standard-deviation convention, regression weighting and degenerate-sample handling are unspecified.

## How it works

- Divide a chosen lookback into shorter samples, calculate rescaled range at each sample size and fit a power law by regressing log rescaled range against log sample size. The slope is the Hurst estimate.

## Outputs and intended use

- Interpret estimates above one-half as persistence and below one-half as a mean-reversion tendency, following the author's heuristic. Use it as regime context rather than a directional signal.

## Parameters and stated settings

- Select lookback and up to eight sample sizes; zero disables a sample. A start-date input limits computation when platform runtime limits are hit.

## Failure modes and caveats

- Finite samples, trends and changing volatility can bias R/S estimates. The interpretation is statistical tendency, not a guarantee that the next move follows a particular regime.

## Missing information and implementation boundary

- Input transformation, partition overlap, standard-deviation convention, regression weighting and degenerate-sample handling are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the disclosed input class; source code and historical data parity have not been validated.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The Hurst exponent is estimated by fitting the power law. Basically finding the slope of log(samples_size) to log(RS).
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]Values 0.5 to 1 - market trending
[*]Values 0 to 0.5 - market tend to mean revert
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Max 8 possible at the moment, if you want to use less use 0 in inputs.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qibyvt4j_hurst_exponent](../tv_qibyvt4j_hurst_exponent.md)

## Source

https://www.tradingview.com/script/QibYVT4J-Hurst-Exponent/

Publication ID: QibYVT4J. Source SHA-256: 9a0f9945f21614f0a50cbcefce0f2621612cc38056738cdc6c99bbf4cf754cea. Raw-description SHA-256: ad2adae242fd454a52a9e1ef24e0f656bb6a66875dee2a972f4b10e990f6f2c5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
