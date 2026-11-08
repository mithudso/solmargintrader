---

id: tv_profile_daukfrmd

name: "Hurst Diamond Notation Pivots"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Mark historical cycle peaks and troughs using Hurst-style diamond notation and use their spacing to frame possible future turning windows."

registry_key: null

runner: null

evaluation: null

---

# Hurst Diamond Notation Pivots

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Mark historical cycle peaks and troughs using Hurst-style diamond notation and use their spacing to frame possible future turning windows.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Precise pivot tests, supported cycle set, dominant-period estimator and uncertainty bounds for forecasts are absent.

- Precise pivot tests, supported cycle set, dominant-period estimator and uncertainty bounds for forecasts are absent.

## How it works

- Detect highs/lows over selected cycle lookbacks, then back-offset diamond markers to the earlier pivot location after the lookback has elapsed. A rainbow scan line/circle visualizes the developing search.

## Outputs and intended use

- Use confirmed pivot intervals for timing hypotheses rather than entries. Axis labels show detection cycle length. An example extrapolates roughly 76 bars from a prior pivot within an 80-bar nominal cycle.

## Parameters and stated settings

- Lookback/cycle length and wavelength colors are implied; the rainbow color scheme is a disclosed default.

## Failure modes and caveats

- The source claims non-repainting but also explicitly describes substantial confirmation lag and backward placement. That claim is not independently verified, and back-offset diamonds were unavailable at the pivot time.

## Missing information and implementation boundary

- Precise pivot tests, supported cycle set, dominant-period estimator and uncertainty bounds for forecasts are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the disclosed calculation class; this is not a verified implementation or historical-feed coverage claim.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
They are offset by their lookback and thus will not 'paint' until after they happen so anticipate accordingly.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
if the average/dominant number of bars in an 80-bar pivot point period/cycle is 76, then a trader might forecast that the next pivot could occur 76-ish bars after the last confirmed pivot.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Please use it for forecasting instead of entry signals.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_daukfrmd_hurst_diamond_notation_pivots](../tv_daukfrmd_hurst_diamond_notation_pivots.md)

## Source

https://www.tradingview.com/script/DaukfrmD-Hurst-Diamond-Notation-Pivots/

Publication ID: DaukfrmD. Source SHA-256: 3f7ea5f70d499a0876c9ea763bd1f1485511230f8424f38fbe79a87b450ae831. Raw-description SHA-256: 7b50b1059ec17a55dc4af7e1c64382f8f323709197c2c1d2720cfd95de3506e8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
