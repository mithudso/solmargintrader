---

id: tv_profile_a35ki2pb

name: "[PX] External Level"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "External Level converts another indicator’s event output into support/resistance annotations. It aims to decouple signal logic from drawing logic so a caller can use RSI, MACD, moving-average or volume events without rewriting the level renderer. The publication supplies a complete RSI extreme-cross event example and an explicit signed interface. It does not specify the exact price used for a new level, its retention or invalidation. Therefore the example signal stream is reproducible, while the full financial level-drawing behavior remains incomplete."

registry_key: null

runner: null

evaluation: null

---

# [PX] External Level

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

External Level converts another indicator’s event output into support/resistance annotations. It aims to decouple signal logic from drawing logic so a caller can use RSI, MACD, moving-average or volume events without rewriting the level renderer. The publication supplies a complete RSI extreme-cross event example and an explicit signed interface. It does not specify the exact price used for a new level, its retention or invalidation. Therefore the example signal stream is reproducible, while the full financial level-drawing behavior remains incomplete.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the complete supplied close-RSI14 threshold-event stream (+1 cross above70, −1 cross below30, zero otherwise). The separate level renderer remains incomplete.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Read external source values: +1 creates resistance, -1 creates support and zero creates no event.
- Independent supplied event example: r_t=RSI(close,14). Output +1.0 when r crosses above 70, −1.0 when r crosses below 30, otherwise 0.0. In crossing terms, upward event requires current r>70 with preceding r≤70; downward requires current r<30 with preceding r≥30. This event stream is defined without assuming the renderer level price.

## Outputs and intended use

- Event-based levels visualize selected points of interest rather than directly commanding trades.
- The independently reproducible output is the example RSI signed event stream; full support/resistance anchor/extension/invalidation behavior remains unspecified.

## Parameters and stated settings

- Example RSI length 14, overbought70 and oversold30; Source selects the external output.

## Failure modes and caveats

- Oversold/overbought crossings can persist within trends and are not automatic reversals.
- An external plot must preserve the signed interface; arbitrary indicator values are not compatible.

## Missing information and implementation boundary

- Level price anchor, line extension/retention, intrabar confirmation and invalidation rules are absent.

## Data requirements

Required inputs: ohlcv, external signed indicator output.

Repository input-class support: unavailable or unresolved. The included RSI example uses OHLCV, but actual external source and level-anchor contract must be selected.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
l = input(14, "RSI Length")
ob = input(70, "Overbought")
os = input(30, "Oversold")
```

### E2: mechanism, readiness

```text
crossover(r, ob) ? 1.0 : crossunder(r, os) ? -1.0 : 0.0
```

### E3: mechanism

```text
1.0, then the script prints a resistance level.
```

### E4: mechanism

```text
-1.0 a support level
```

### E5: mechanism, readiness

```text
r = rsi(close, l)
```

### E6: mechanism, readiness

```text
plot(crossover(r, ob) ? 1.0 : crossunder(r, os) ? -1.0 : 0.0, "Output", transp=100)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_a35ki2pb_px_external_level](../tv_a35ki2pb_px_external_level.md)

## Source

https://www.tradingview.com/script/a35KI2pb-PX-External-Level/

Publication ID: a35KI2pb. Source SHA-256: 16268c845563e331fbb396217dfd3df3b79a36590382c3e2ff9dce0b371a0bae. Raw-description SHA-256: 5c813c47494585a3ae4fe0890b36009e1e1727c6cc110e9f3db77bd41270a96e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
