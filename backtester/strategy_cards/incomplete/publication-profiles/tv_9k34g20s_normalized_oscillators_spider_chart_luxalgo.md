---

id: tv_profile_9k34g20s

name: "Normalized Oscillators Spider Chart [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Place several normalized oscillators into one radial display and summarize their average stance in a sentiment meter."

registry_key: null

runner: null

evaluation: null

---

# Normalized Oscillators Spider Chart [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Place several normalized oscillators into one radial display and summarize their average stance in a sentiment meter.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Normalization equations, correlation reference, missing-volume handling, averaging treatment of disabled inputs and entry/exit rules are not documented.

- Normalization equations, correlation reference, missing-volume handling, averaging treatment of disabled inputs and entry/exit rules are not documented.

## How it works

- Calculate selected RSI, stochastic K, correlation oscillator, MFI, Williams rank, upward-variation percentage, CMO and Aroon values. Normalize their displays into comparable spokes and average included readings for the meter.

## Outputs and intended use

- Use the spider shape to compare overbought/oversold conditions and disagreements without adding separate panes. A meter near fifty is described as ranging context, not proof of a stable range.

## Parameters and stated settings

- Hide individual spokes, use individual lengths or a global length, and adjust chart width/offset. Exact numerical defaults and threshold bands are absent.

## Failure modes and caveats

- Several inputs measure overlapping momentum, so the average does not represent independent votes. Normalization can conceal different statistical meanings or differing reaction speeds.

## Missing information and implementation boundary

- Normalization equations, correlation reference, missing-volume handling, averaging treatment of disabled inputs and entry/exit rules are not documented.

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
An overall sentiment closer to 50 would indicate a ranging market.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
This metric is based on the average value between each oscillator.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Users can control the length settings of each oscillator individually or use a global
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_9k34g20s_normalized_oscillators_spider_chart_luxalgo](../tv_9k34g20s_normalized_oscillators_spider_chart_luxalgo.md)

## Source

https://www.tradingview.com/script/9K34g20s-Normalized-Oscillators-Spider-Chart-LuxAlgo/

Publication ID: 9K34g20s. Source SHA-256: f511365e97b142cc5d6d76855693179bbe4fd93dd44b15d2f6a68b592c0775de. Raw-description SHA-256: 0f386ab68885e96848a0fa96ddc0d394ad7db93440f0be2b7ac666fc86c49f03.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
