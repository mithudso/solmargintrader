---

id: tv_profile_vnzbp63l

name: "Zigzag Trend/Divergence Detector"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Combine trend direction and zigzag-based oscillator divergence into a compact sentiment view for managing pullbacks or extended moves."

registry_key: null

runner: null

evaluation: null

---

# Zigzag Trend/Divergence Detector

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine trend direction and zigzag-based oscillator divergence into a compact sentiment view for managing pullbacks or extended moves.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Combination mapping appears in an external image, not readable source text. Supertrend parameters, pivot rules and actionable entry/exit thresholds remain missing.

- Combination mapping appears in an external image, not readable source text. Supertrend parameters, pivot rules and actionable entry/exit thresholds remain missing.

## How it works

- Use supertrend for trend bias, a selected oscillator and price zigzag pivots to compare consecutive same-direction swings. Combine divergence type/direction with trend bias into continuation, divergence, hidden-divergence or indeterminate states.

## Outputs and intended use

- Display chart/table history and optional supertrend candle coloring. Confirmed-pivots mode ignores the developing pivot; alerts are described as a possible future feature, not a current guarantee.

## Parameters and stated settings

- RSI is the default oscillator. Alternatives include CCI, CMO, COG, ADX, MACD components, MFI, momentum, ROC, TSI, Williams and normalized channel measures. Zigzag and oscillator settings are configurable.

## Failure modes and caveats

- The author warns that oscillator pivots may not coincide with price pivots and that some divergence calculations can be incorrect. Developing pivots can revise sentiment.

## Missing information and implementation boundary

- Combination mapping appears in an external image, not readable source text. Supertrend parameters, pivot rules and actionable entry/exit thresholds remain missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed feature class; this does not establish implementation parity or complete data coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Default used is RSI.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
If you check "Use confirmed pivots", then unconfirmed pivot will be ignored
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Oscillators does not always make pivots at same bar as price. Due to this some the divergence calculation may not be correct.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
C - Continuation
D - Divergence
H - Hidden Divergence
I - Indeterminate
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_vnzbp63l_zigzag_trend_divergence_detector](../tv_vnzbp63l_zigzag_trend_divergence_detector.md)

## Source

https://www.tradingview.com/script/vnzbp63L-Zigzag-Trend-Divergence-Detector/

Publication ID: vnzbp63L. Source SHA-256: 3661b9bb36720582209bf0f0155ac69841efe1803c781f2f45c7bb1196e2abc8. Raw-description SHA-256: aeb03c292d0021cdf6ba6ecc5631c3014faaadfec68b6ae48b0bcf46af4306b9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
