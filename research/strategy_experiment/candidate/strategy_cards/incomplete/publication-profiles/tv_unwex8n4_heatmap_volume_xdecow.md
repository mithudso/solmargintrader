---

id: tv_profile_unwex8n4

name: "Heatmap Volume [xdecow]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Make unusually high or low traded volume visible directly on volume bars and price candles."

registry_key: null

runner: null

evaluation: null

---

# Heatmap Volume [xdecow]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Make unusually high or low traded volume visible directly on volume bars and price candles.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The rolling window, threshold boundaries, zero-variance handling and any alert rules are unspecified.

- The rolling window, threshold boundaries, zero-variance handling and any alert rules are unspecified.

## How it works

- Measure how far volume lies from average volume in standard-deviation units and use that relative position to assign heat-map zones.

## Outputs and intended use

- Color both candles and volume bars to emphasize relative participation. The author recommends neutral wick and border colors for readability.

## Parameters and stated settings

- No average type, lookback, zone cutoffs or default palette is disclosed.

## Failure modes and caveats

- Volume spikes can reflect auctions, sessions or feed changes rather than informed directional buying. Standardized volume is unstable when variance is small.

## Missing information and implementation boundary

- The rolling window, threshold boundaries, zero-variance handling and any alert rules are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; this does not establish implementation parity or complete historical coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This indicator colors the volume bars and candles according to the volume traded.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
how many standard deviations the volume are distant from the average volume?
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_unwex8n4_heatmap_volume_xdecow](../tv_unwex8n4_heatmap_volume_xdecow.md)

## Source

https://www.tradingview.com/script/unWex8N4-Heatmap-Volume-xdecow/

Publication ID: unWex8N4. Source SHA-256: 233be0a0397b8f47a05d2338095bd9de70f6e13b24a28ab87af53773a8e80c52. Raw-description SHA-256: 9f5f8ff5ff795992af8381fff194f26800c8327700afc9d4ceb637a4a1f2726f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
