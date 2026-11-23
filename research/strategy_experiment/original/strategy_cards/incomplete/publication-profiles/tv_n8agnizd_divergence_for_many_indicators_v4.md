---

id: tv_profile_n8agnizd

name: "Divergence for Many Indicators v4"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Locate regular and hidden divergences between price and a collection of technical indicators or an externally supplied indicator."

registry_key: null

runner: null

evaluation: null

---

# Divergence for Many Indicators v4

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Locate regular and hidden divergences between price and a collection of technical indicators or an externally supplied indicator.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Indicator defaults, exact divergence geometry/line-validity tests, pivot delay and risk/execution rules are absent.

- Indicator defaults, exact divergence geometry/line-validity tests, pivot delay and risk/execution rules are absent.

## How it works

- On each candle compare against prior pivot points, gating positive searches on rising close and indicator values and negative searches on both falling. Scan RSI, MACD components, stochastic, CCI, momentum, OBV, VWMACD, CMF or a selected external series.

## Outputs and intended use

- Plot divergence lines/labels, show indicator names or counts, optionally retain only the latest positive/negative examples and alert separately for each regular/hidden direction.

## Parameters and stated settings

- The described search spans the last sixteen pivots within one hundred bars. Pivot period, close-versus-high/low source, divergence types, selected indicators and styles are configurable; a fifteen-period pivot example is illustrative.

## Failure modes and caveats

- Pivot detection creates confirmation lag. Multiple indicator matches often share the same price information, and an external series may itself repaint or depend on unavailable inputs.

## Missing information and implementation boundary

- Indicator defaults, exact divergence geometry/line-validity tests, pivot delay and risk/execution rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supplies the described input class; this does not verify code parity, complete historical data or measured returns.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
last 16 Pivot Points
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
16 pivot points that is in last 100 bars
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
for positive divergences first it checks if closing price is higher than last closing price and indicator value is higher than perious value
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
related external indicator must be added before enabling this option
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_n8agnizd_divergence_for_many_indicators_v4](../tv_n8agnizd_divergence_for_many_indicators_v4.md)

## Source

https://www.tradingview.com/script/n8AGnIZd-Divergence-for-Many-Indicators-v4/

Publication ID: n8AGnIZd. Source SHA-256: 4072aa09b9453ca90d4128cf328e98ddc66ce71ddc51764dd2091d334ff6364b. Raw-description SHA-256: 6a8700fc6ec9299184ef793d5fb80394f6f3ea04dadac7b269d826510894d04e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
