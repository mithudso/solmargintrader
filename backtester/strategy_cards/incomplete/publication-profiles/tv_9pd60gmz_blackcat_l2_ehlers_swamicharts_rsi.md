---

id: tv_profile_9pd60gmz

name: "[blackcat] L2 Ehlers SwamiCharts RSI"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Display a family of modified RSI calculations across lookbacks as a heatmap to reveal how momentum interpretation varies with horizon."

registry_key: null

runner: null

evaluation: null

---

# [blackcat] L2 Ehlers SwamiCharts RSI

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Display a family of modified RSI calculations across lookbacks as a heatmap to reveal how momentum interpretation varies with horizon.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Roofing coefficients, RSI ratio construction, period range, color mapping and trade/risk rules are missing.

- Roofing coefficients, RSI ratio construction, period range, color mapping and trade/risk rules are missing.

## How it works

- Apply a roofing filter to price before computing RSI-like ratios, then smooth each ratio with a SuperSmoother. Maintain array histories explicitly for each lookback because the described implementation predates automatic array-history behavior.

## Outputs and intended use

- Use the heatmap to compare short/long horizon states, potential cycles and changes in context. The named MyRSI1 output is an Ehlers-style modified RSI, not necessarily standard RSI on closes.

## Parameters and stated settings

- The SuperSmoother is ten bars. Lookback-range bounds, roofing settings and display thresholds are not stated in the saved description.

## Failure modes and caveats

- Multiple periods are correlated views of the same series. Filter lag and horizon choice can make visually strong patterns appear only after a move develops; fidelity claims are author assertions.

## Missing information and implementation boundary

- Roofing coefficients, RSI ratio construction, period range, color mapping and trade/risk rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary OHLCV supports the disclosed calculation class; this does not establish source-code parity or verified historical coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The RSI is computed relative to the output of the roofing filter rather than price closes
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
After the computation of the ratio, the indicator is smoothed in a SuperSmoother filter
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
coefficients for the 10-bar SuperSmoother filter
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_9pd60gmz_blackcat_l2_ehlers_swamicharts_rsi](../tv_9pd60gmz_blackcat_l2_ehlers_swamicharts_rsi.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/9Pd60GmZ-blackcat-L2-Ehlers-SwamiCharts-RSI/

Publication ID: 9Pd60GmZ. Source SHA-256: 41151d82ba4111609277ed398fb60f409f772f486269a510a67914ea1d46b098. Raw-description SHA-256: 51814ae4cf59cf754fab6228a9a515e4b1135cb0ba4b9c246e77e596f0c9357c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
