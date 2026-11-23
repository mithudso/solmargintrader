---

id: tv_profile_xfr7xhqz

name: "CM MACD Custom Indicator - Multiple Time Frame - V2"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "CM MACD MTF V2 updates the presentation and alert handling of a multi-timeframe MACD study. It allows users to separate the MACD/signal lines, histogram and price-bar highlighting, while alert messages include the context needed to identify a cross. The description is a release-note list rather than a formula reference, so its exact underlying MACD parameters cannot be recovered from this page alone."

registry_key: null

runner: null

evaluation: null

---

# CM MACD Custom Indicator - Multiple Time Frame - V2

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

CM MACD MTF V2 updates the presentation and alert handling of a multi-timeframe MACD study. It allows users to separate the MACD/signal lines, histogram and price-bar highlighting, while alert messages include the context needed to identify a cross. The description is a release-note list rather than a formula reference, so its exact underlying MACD parameters cannot be recovered from this page alone.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** MACD moving-average types/lengths and timeframe alignment are absent.

- MACD moving-average types/lengths and timeframe alignment are absent.

## How it works

- Display MACD, signal and histogram with optional trend-dependent line/bar colors and platform-managed timeframe selection.
- Trigger configured cross-up/cross-down alerts with symbol, timeframe and closing-price information.

## Outputs and intended use

- Use the plotted relationship and bar-close alerts for monitoring rather than interpreting every intrabar fluctuation as a confirmed cross.

## Parameters and stated settings

- MACD/signal visibility, histogram visibility, colors, trend bar highlights and alerts are selectable. Alerts are preset to bar close; lengths and timeframe defaults are not stated.

## Failure modes and caveats

- Analytical: higher-timeframe developing values may differ from chart-bar confirmation; the bar-close alert setting alone does not establish non-repainting behavior.

## Missing information and implementation boundary

- MACD average types/lengths, trend-color condition, timeframe alignment, alert activation details beyond release notes and exit/risk logic are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, outputs_and_use, readiness

```text
Alerts are Pre-Set to only Alert on Bar Close
```

### E2: outputs_and_use, readiness

```text
Show Symbol, TimeFrame, Closing Price, MACD Crosses Up & MACD Crosses Down Signals in Alert
```

### E3: mechanism, readiness

```text
Switched MTF Logic to turn ON/OFF automatically
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_xfr7xhqz_cm_macd_custom_indicator_multiple_time_frame_v2](../tv_xfr7xhqz_cm_macd_custom_indicator_multiple_time_frame_v2.md)

## Source

https://www.tradingview.com/script/XFr7xHqZ-CM-MACD-Custom-Indicator-Multiple-Time-Frame-V2/

Publication ID: XFr7xHqZ. Source SHA-256: aa21d0248402b3ab68848de726655051707ad77ba539511c8bdacdf1efc1b39b. Raw-description SHA-256: 7c3a04b3624d1da1572624a1122e5b2f9e173acae97f4d6ea906e7a6fefc6104.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
