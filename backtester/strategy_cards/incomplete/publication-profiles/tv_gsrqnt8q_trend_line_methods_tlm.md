---

id: tv_profile_gsrqnt8q

name: "Trend Line Methods (TLM)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Trend Line Methods draws two complementary channel estimates: one connects stored pivots, while the other fits boundaries through segment extremes over a fixed window. It supports discretionary structure analysis and explicitly provides neither trade signals nor risk management. Agreement between the channels is proposed as a reference zone, not independent statistical confirmation of support or resistance."

registry_key: null

runner: null

evaluation: null

---

# Trend Line Methods (TLM)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trend Line Methods draws two complementary channel estimates: one connects stored pivots, while the other fits boundaries through segment extremes over a fixed window. It supports discretionary structure analysis and explicitly provides neither trade signals nor risk management. Agreement between the channels is proposed as a reference zone, not independent statistical confirmation of support or resistance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Confirmed-pivot span channel is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For Pivot Span, connect oldest/latest stored pivot highs for the upper line and corresponding lows for the lower line.
- For the straight channel, divide a window into five segments, select each segment’s highest high/lowest low and fit separate regression-style lines through those representatives.
- With caller left/right pivot confirmation/count window,retain confirmed highs/lows. For each side connect oldest retained pivot(t0,p0) to latest(t1,p1):line(t)=p0+(p1-p0)*(t-t0)/(t1-t0). Require two distinct timestamps;caller defines ties. Update only when newly confirmed pivots enter. Five-point regression/style extras excluded.

## Outputs and intended use

- Compare recent-swing and broader-window boundaries and optional fill for planning within an existing trading process.
- Usable scope: Confirmed-pivot span channel. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Method toggles, pivot left/right counts, retained count, lookback/channel length, line style/thickness and colors are configurable; second method uses five segments.

## Failure modes and caveats

- Analytical: confirmed pivots lag, segment boundaries affect fitted slopes and the two methods share price data rather than provide independent evidence.

## Missing information and implementation boundary

- Exact regression estimator/time coordinates, segment remainder handling, pivot tie rules and defaults are not fully specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
divided into five segments of similar length.
```

### E2: mechanism, readiness

```text
oldest and most recent stored pivot highs
```

### E3: outputs_and_use, readiness

```text
does not generate trading signals
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
•	From the oldest and most recent stored pivot highs, it draws an upper trend line.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
•	From the oldest and most recent stored pivot lows, it draws a lower trend line.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
•	Pivot Left / Pivot Right – Number of bars to the left and right used to confirm pivot highs and lows. Larger values produce fewer but more significant swing points.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gsrqnt8q_trend_line_methods_tlm](../tv_gsrqnt8q_trend_line_methods_tlm.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/GsRqNT8Q-Trend-Line-Methods-TLM/

Publication ID: GsRqNT8Q. Source SHA-256: 1e665c451fe535adee39e76325d3d11f4d182438b983f5534f8c241f43f214da. Raw-description SHA-256: 5b2bca387654acd2c137fd94607976f536ebb746403cf0855c2282ec5e9d3d4c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
