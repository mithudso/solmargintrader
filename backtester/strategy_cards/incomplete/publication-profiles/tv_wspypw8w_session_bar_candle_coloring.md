---

id: tv_profile_wspypw8w

name: "Session Bar/Candle Coloring"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Apply session-specific candle styling to emphasize selected market hours and distinguish bullish, bearish or neutral candles."

registry_key: null

runner: null

evaluation: null

---

# Session Bar/Candle Coloring

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Apply session-specific candle styling to emphasize selected market hours and distinguish bullish, bearish or neutral candles.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The main styling workflow is clear, but session/partial-bar membership and neutral-state definitions are missing for exact reproduction.

- Session timezone and partial-bar inclusion
- Neutral candle criterion

## How it works

- Select an intraday session and weekdays, then recolor enabled body, border, wick and/or chart background according to candle state. Manual chart-style input accommodates bars, candles and transformed chart types.

## Outputs and intended use

- Highlight regular/pre-postmarket sessions, midnight-containing bars or indecisive candles. Hiding/recoloring is visual only and does not remove underlying market data or generate a trading signal.

## Parameters and stated settings

- Session/day selection, component colors, Chart Style and Portion of bar in session are configurable. The indicator is not intended for daily or higher charts.

## Failure modes and caveats

- The author says old candles may be unavailable for some bar-portion modes and chart type cannot always be detected automatically. Incorrect manual style/session settings can misrepresent the intended segment.

## Missing information and implementation boundary

- The session timezone, partial-bar inclusion modes and exact neutral-candle criterion are in tooltips/code rather than the readable description.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class; code parity and cached-history coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
define the intraday trading session
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Body, Borders, Wick, and/or Background.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
not intended to function on Daily or higher timeframes
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Portion of bar in session
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_heikin_ashi](../../tv_method_heikin_ashi.md)
- [tv_method_renko](../tv_method_renko.md)

## Source

https://www.tradingview.com/script/WsPypw8w-Session-Bar-Candle-Coloring/

Publication ID: WsPypw8w. Source SHA-256: 50ae3ca85a60811dfffe239d46149eac911e6269312c4072b99997732a7a26c1. Raw-description SHA-256: 43bd121fc1c0f42f15c7a1e217b98026148848788528a934da0a4a921057947d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
