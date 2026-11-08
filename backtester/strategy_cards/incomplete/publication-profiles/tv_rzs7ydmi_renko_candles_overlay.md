---

id: tv_profile_rzs7ydmi

name: "Renko Candles Overlay"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Overlay Renko-style bricks on an ordinary chart with explicit distinction between confirmed and developing bricks."

registry_key: null

runner: null

evaluation: null

---

# Renko Candles Overlay

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Overlay Renko-style bricks on an ordinary chart with explicit distinction between confirmed and developing bricks.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Reversal-brick rules, source prices, tick rounding, default periods and intrabar sequencing are absent.

- Reversal-brick rules, source prices, tick rounding, default periods and intrabar sequencing are absent.

## How it works

- Choose fixed, percentage or ATR-derived brick sizes. Dynamic sizes update when new bricks are added, so successive bricks can have different sizes. Fit the displayed brick set into the visible chart area.

## Outputs and intended use

- Show next-brick thresholds with lines/labels, optionally recolor ordinary bars by brick direction and render unconfirmed live bricks differently. These thresholds describe chart construction rather than guaranteed execution prices.

## Parameters and stated settings

- Methods include ATR, ATR/2, ATR/4, percent and traditional. Corresponding periods, fixed size, percentage and brick width are configurable. The author describes approximately 280 visible candles, not a universal history limit.

## Failure modes and caveats

- Unconfirmed live bricks can change before the time candle closes. Historical OHLC may not preserve intrabar path, and adaptive size changes complicate comparison with conventional fixed Renko.

## Missing information and implementation boundary

- Reversal-brick rules, source prices, tick rounding, default periods and intrabar sequencing are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class. Code parity, complete history and forward performance remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Method: [/i]the option for brick scaling method:[i] ATR, ATR/2, ATR/4, Percent, Traditional
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Brick size is calculated/updated when new bricks added.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
approximately 280 candles
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
unconfirmed bricks shown in different color
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_renko](../tv_method_renko.md)
- [tv_rzs7ydmi_renko_candles_overlay](../tv_rzs7ydmi_renko_candles_overlay.md)

## Source

https://www.tradingview.com/script/rZs7YdMI-Renko-Candles-Overlay/

Publication ID: rZs7YdMI. Source SHA-256: 9c920fa5704c0789f06371df88e06e5a5f189699d6eb3950829521f0358c3b46. Raw-description SHA-256: 8bb97ef58f2aced7dd7e18b5e01aec1a61526e8141e04a36567badec0eb3af3e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
