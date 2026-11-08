---

id: tv_profile_69wrttlx

name: "Correlation [array's]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Demonstrate a compact array-and-loop approach to comparing market correlations while avoiding inconsistent behavior of the built-in correlation function inside a local loop."

registry_key: null

runner: null

evaluation: null

---

# Correlation [array's]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Demonstrate a compact array-and-loop approach to comparing market correlations while avoiding inconsistent behavior of the built-in correlation function inside a local loop.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: Synchronization of symbols, return transformation, matrix layout, numerical edge cases and trading rules are absent.

- Synchronization of symbols, return transformation, matrix layout, numerical edge cases and trading rules are absent.

## How it works

- The author uses array covariance and standard deviation as the basis for a correlation workaround and loops over the selected data. The saved prose describes the approach but does not provide its exact formula or missing-value treatment.

## Outputs and intended use

- Use the resulting correlation display to inspect co-movement among selected symbols. This is an implementation-oriented analytical example rather than a prescribed pairs trade.

## Parameters and stated settings

- Symbols, timeframe, lookback, display colors and limits are configurable; exact defaults and supported symbol count are not stated.

## Failure modes and caveats

- Correlation depends on sampling interval and window. Raw price correlation and return correlation have different interpretations, and the description does not identify which is used.

## Missing information and implementation boundary

- Synchronization of symbols, return transformation, matrix layout, numerical edge cases and trading rules are absent.

## Data requirements

Required inputs: aligned price series for selected symbols.

Repository input-class support: unavailable or unresolved. The publication requires a selected multi-symbol dataset. No symbol universe or aligned historical series is established in the saved source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The Pine correlation function doesn't work consistently in a local scope (loop), so I had to work around it
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Inspired by @ZenAndTheArtOfTrading's Correlation Meter (using array.covariance and array.stdev) and
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Symbols, timeframe, look-back period, colors and limits can be changed
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_69wrttlx_correlation_array_s](../tv_69wrttlx_correlation_array_s.md)

## Source

https://www.tradingview.com/script/69wrTtLX-Correlation-array-s/

Publication ID: 69wrTtLX. Source SHA-256: f7bb2b0efbb150d368ee1275ff45df55ec1f271a0dd5f0640dd2e2854e5b5079. Raw-description SHA-256: 3702fb9fce1e3b29c113f16defb1c3b86694a31c00d068a7e6cef44b6270d4a0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
