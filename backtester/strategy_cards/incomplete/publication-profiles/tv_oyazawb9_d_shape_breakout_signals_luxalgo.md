---

id: tv_profile_oyazawb9

name: "D-Shape Breakout Signals [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Create curved support/resistance shapes from swing pairs, mark their first breakout and derive a conditional trailing reference from broken shapes."

registry_key: null

runner: null

evaluation: null

---

# D-Shape Breakout Signals [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Create curved support/resistance shapes from swing pairs, mark their first breakout and derive a conditional trailing reference from broken shapes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Arc coordinate formula, exact breach test, pivot timing, trend reversal of the stop and execution assumptions are missing.

- Arc coordinate formula, exact breach test, pivot timing, trend reversal of the stop and execution assumptions are missing.

## How it works

- Construct a semi-circular arc from the distance between two swings and a configurable width. Mark one upper/lower breakout per shape or a neutral event at its right boundary. On directional breakouts, consider eligible midlines nearest close for a trailing level that only tightens with the trend.

## Outputs and intended use

- Green/red dots show upper/lower breaks and blue a neutral completion. The trailing line may be used as an entry or stop reference but is a plotted level, not a broker order.

## Parameters and stated settings

- Swing length, D-width, included swing direction, minimum retained patterns, historical arc/midline visibility, colors and labels are configurable. No numerical defaults are supplied.

## Failure modes and caveats

- The prose repeats the same swing-low-to-high sequence for both initial colors, an unresolved contradiction. Swing confirmation and curved geometry can create delayed signals; neutral breaks do not update the stop.

## Missing information and implementation boundary

- Arc coordinate formula, exact breach test, pivot timing, trend reversal of the stop and execution assumptions are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The feature uses ordinary chart history as its financial input class; source-code behavior and market coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Only one breakout per D-shape can occur.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The Stop-Loss line won't be updated when a "Neutral Breakout" occurs.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the potential new Stop-Loss value must be higher than the previous TSL value
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
initially be colored green when a Swing Low is followed by a Swing High, and red when a Swing Low is followed by a Swing High.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_trailing_stop](../../tv_method_trailing_stop.md)
- [tv_oyazawb9_d_shape_breakout_signals_luxalgo](../tv_oyazawb9_d_shape_breakout_signals_luxalgo.md)

## Source

https://www.tradingview.com/script/oYAzaWB9-D-Shape-Breakout-Signals-LuxAlgo/

Publication ID: oYAzaWB9. Source SHA-256: 61408a32b08a52ab5fd4925b587c6e1cbda52a0f21375458be232eef41115c96. Raw-description SHA-256: 4ace3b0c44a79122f36bae43263255206d686d76f8f685197779b742fd1a370f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
