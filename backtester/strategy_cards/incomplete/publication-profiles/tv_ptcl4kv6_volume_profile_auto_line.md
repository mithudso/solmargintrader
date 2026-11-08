---

id: tv_profile_ptcl4kv6

name: "Volume Profile Auto [line]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Build a volume-at-price-style display incrementally within each higher-timeframe period using line thickness to represent accumulated volume."

registry_key: null

runner: null

evaluation: null

---

# Volume Profile Auto [line]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Build a volume-at-price-style display incrementally within each higher-timeframe period using line thickness to represent accumulated volume.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Price-bin boundaries, volume allocation across a candle range, automatic timeframe logic and POC ties are unspecified.

- Price-bin boundaries, volume allocation across a candle range, automatic timeframe logic and POC ties are unspecified.

## How it works

- Start a box and several price-level lines at the higher-timeframe boundary. As lower-timeframe candles arrive, inspect position and volume and add volume to the corresponding left-side line.

## Outputs and intended use

- Thicker lines represent more volume at their level. Yellow identifies the current period's maximum-volume line and red marks the previous period's POC.

## Parameters and stated settings

- Parts controls line count, Max Width caps thickness and Automatic Settings chooses a higher timeframe. The source illustrates 5,15,25 and 50 parts but does not identify a default.

## Failure modes and caveats

- Line thickness is a display approximation, not exchange volume-at-price detail. Developing periods accumulate data and can change the leading level.

## Missing information and implementation boundary

- Price-bin boundaries, volume allocation across a candle range, automatic timeframe logic and POC ties are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature uses ordinary OHLCV, including lower-timeframe history where selected. This establishes data class only, not a verified implementation or cache.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
the volume is added to the left line, so when you see a thicker line, this means at that level there is more volume traded.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
'Parts' -> amount of lines (left of box)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The yellow line is the max volume line of that period, last period has a red line (POC), also referring the max.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ptcl4kv6_volume_profile_auto_line](../tv_ptcl4kv6_volume_profile_auto_line.md)

## Source

https://www.tradingview.com/script/pTCl4kV6-Volume-Profile-Auto-line/

Publication ID: pTCl4kV6. Source SHA-256: f9472f48408697d6fe2b2f5c49b5828d4981d254555c10e605ff13d82da3625f. Raw-description SHA-256: b4ed788add7d4b10ea0629d53c6ed3f2f81fcb7ce81092bca25020e1e7187a63.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
