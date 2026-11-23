---

id: tv_profile_fqmvaak9

name: "Volume Profile [Makit0]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Makit0 Volume Profile plots session value references for discretionary stock/futures analysis, originally motivated by regular-session ES levels. It aims to show where session volume concentrated and to retain key auction references on the chart. Its value area surrounds the most heavily traded region, while session extremes and midpoint provide broader context. Crucially, the author says this implementation uses the current chart’s candles rather than finer intrabar data. Therefore its profile is resolution-dependent and should not be assumed to match a built-in tick- or lower-timeframe profile."

registry_key: null

runner: null

evaluation: null

---

# Volume Profile [Makit0]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Makit0 Volume Profile plots session value references for discretionary stock/futures analysis, originally motivated by regular-session ES levels. It aims to show where session volume concentrated and to retain key auction references on the chart. Its value area surrounds the most heavily traded region, while session extremes and midpoint provide broader context. Crucially, the author says this implementation uses the current chart’s candles rather than finer intrabar data. Therefore its profile is resolution-dependent and should not be assumed to match a built-in tick- or lower-timeframe profile.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for session HIGH/LOW/MID reference lines with disclosed CT session windows and supported chart intervals. Volume distribution, POC and value-area construction remain outside this narrow range-line scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independent session-range output: within the chosen CT session, track the maximum chart-bar high and minimum chart-bar low and draw HIGH, LOW and their midpoint (HIGH+LOW)/2. Use chart resolution compatible with session boundaries; these lines do not depend on volume allocation, POC or value-area calculations.
- Allocate session candle volume across price levels, identify maximum-volume POC and determine the value-area boundaries.
- Compute session high, low and midpoint and optionally extend all reference lines.
- Restrict processing/display to supported minute charts and selected session hours.

## Outputs and intended use

- POC, VAH/VAL and high/low/mid lines plus optional out-of-session shading support auction-context analysis.

## Parameters and stated settings

- Value area contains 70% of session volume. Supported minutes are 1,2,3,5,10,15,30.
- Sessions: RTH 08:30–15:15 CT default; GLOBEX 17:00–08:30; FULL 17:00–15:15.
- History defaults to one 12-hour period; levels/shading default on and line extension off.
- Narrow session-range scope uses RTH 08:30–15:15 CT (default), GLOBEX 17:00–08:30 CT, or FULL 17:00–15:15 CT; Show Range defaults true. MID is the range midpoint, not volume-weighted value.

## Failure modes and caveats

- Coarser chart resolution changes estimated price-volume distribution.
- Session definitions and daylight-saving alignment must match the instrument; many extended levels can obscure charts.

## Missing information and implementation boundary

- Exact volume allocation, bin size, value-area expansion/ties, holiday handling and trade rules are absent.

## Data requirements

Required inputs: ohlcv, session/calendar definitions.

Repository input-class support: available. The source explicitly uses current-resolution OHLCV rather than lower-timeframe data; session timestamps are ordinary metadata.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
70% of the session volume
```

### E2: parameters

```text
1, 2, 3, 5, 10, 15 and 30 minutes
```

### E3: parameters

```text
RTH (8:30 to 15:15 CT), GLOBEX (17:00 to 8:30 CT) and FULL (17:00 to 15:15 CT)
```

### E4: parameters

```text
1 period by default
```

### E5: parameters

```text
Extension: Extend all the plotted lines to the right. false by default
```

### E6: mechanism, risks

```text
it gets the data from the current chart resolution.
```

### E7: mechanism, parameters, readiness

```text
Show Range (Session High, Low & Mid): show/hide session HIGH, LOW & MID lines. true by default
```

### E8: parameters, readiness

```text
RTH (8:30 to 15:15 CT), GLOBEX (17:00 to 8:30 CT) and FULL (17:00 to 15:15 CT) sessions. RTH by default
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fqmvaak9_volume_profile_makit0](../tv_fqmvaak9_volume_profile_makit0.md)
- [tv_method_market_profile](../tv_method_market_profile.md)

## Source

https://www.tradingview.com/script/FQmVaaK9-Volume-Profile-Makit0/

Publication ID: FQmVaaK9. Source SHA-256: e727b229032f124fc288fb6e920569c7174d93555a33742af131de553758cb97. Raw-description SHA-256: 550a7df05c4de1e5672be03de547f1d17c775588838ac57d2084f264b0a120d3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
