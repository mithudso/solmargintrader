---

id: tv_profile_zr7ztqm1

name: "Renko RSI"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Calculate RSI on a custom Renko engine while displaying the result on a time-based chart."

registry_key: null

runner: null

evaluation: null

---

# Renko RSI

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Calculate RSI on a custom Renko engine while displaying the result on a time-based chart.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Renko reversal rules, ATR period, threshold defaults, RSI recursion and alert confirmation are absent.

- Renko reversal rules, ATR period, threshold defaults, RSI recursion and alert confirmation are absent.

## How it works

- Build Renko state from closes or highs/lows with traditional or ATR-based brick sizing. Round dynamic brick sizes to the instrument tick increment and update ATR brick size only when the Renko close changes. Apply the author's own RSI algorithm to that state.

## Outputs and intended use

- Alerts cover crossings in both directions through overbought and oversold levels. Use them as Renko-momentum observations; no complete execution plan is supplied.

## Parameters and stated settings

- RSI length defaults to two. Price source and brick-scaling method are selectable; the rounding example maps 0.00124 to 0.001 for a 0.001 minimum tick.

## Failure modes and caveats

- The author calls it non-repainting, but the saved prose and unavailable code do not verify that property. OHLC bars can hide the intrabar order of brick formation.

## Missing information and implementation boundary

- Renko reversal rules, ATR period, threshold defaults, RSI recursion and alert confirmation are absent.

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
For example if mintick value is 0.001 and brick size (ATR/Percentage) is 0.00124 then box size becomes 0.001.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
box size changes only when Renko closing price changed.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
RSI length is 2 by default, you can set as you wish.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_renko](../tv_method_renko.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_zr7ztqm1_renko_rsi](../tv_zr7ztqm1_renko_rsi.md)

## Source

https://www.tradingview.com/script/Zr7Ztqm1-Renko-RSI/

Publication ID: Zr7Ztqm1. Source SHA-256: 7357cee1eef878e4b9b179d1f2a68e35e38a4593b815a46dd03aeb1b63165f33. Raw-description SHA-256: f9fcd5254091831a568917ca383db7ccad8f0b69a092dc5319768f834b976c6b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
