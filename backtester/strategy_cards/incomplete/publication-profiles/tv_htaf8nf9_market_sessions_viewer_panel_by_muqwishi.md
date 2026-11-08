---

id: tv_profile_htaf8nf9

name: "Market Sessions & Viewer Panel [By MUQWISHI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Market Sessions & Viewer Panel aggregates price action within customizable sessions and shows their candles side by side. It helps compare session range and change while retaining colored session blocks on the working chart. A projected block end is an estimate of visual extent, not a forecast of future price or volume."

registry_key: null

runner: null

evaluation: null

---

# Market Sessions & Viewer Panel [By MUQWISHI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Sessions & Viewer Panel aggregates price action within customizable sessions and shows their candles side by side. It helps compare session range and change while retaining colored session blocks on the working chart. A projected block end is an estimate of visual extent, not a forecast of future price or volume.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Completed caller-session OHLCV/change is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Detect user-configured time blocks under a common timezone, aggregate session OHLC/volume and track current status.
- Render session candle/bar summaries with tooltips and draw boxes or candle-like blocks over their active periods; optionally extend drawings to estimated session ends.
- Within caller timezone/start/end aggregate first open,max high,min low,last close,sum volume. Change%=100*(last_close/first_open-1) for nonzero open. Projected end,DST,overlap and partial-session policies remain limitations.

## Outputs and intended use

- Compare session volatility and open-to-close change through the panel, sorting by most recent open or configured order.
- Usable scope: Completed caller-session OHLCV/change. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Up to four sessions can be named/timed/colored. Inputs include timezone, panel chart type/size/location, sort order, drawing style, borders and labels; no time defaults are listed.

## Failure modes and caveats

- Projected ends are stated not to work fully on seconds charts; analytical: timezone/DST and nontrading gaps can affect aggregation and visual ordering.

## Missing information and implementation boundary

- Timezone-library behavior, DST handling, end-time estimate, session overlaps and incomplete-session conventions are missing.

## Data requirements

Required inputs: ohlcv, user session names/times and timezone.

Repository input-class support: unavailable or unresolved. Session boundaries and timezone configuration must be supplied; price data alone does not define them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to four trading sessions
```

### E2: mechanism, outputs_and_use, readiness

```text
detailed OHLC and volume
```

### E3: risks, readiness

```text
doesn’t function fully on seconds-based timeframes
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
Each bar represents the price action during a session and includes the session status, session name, closing price, change(%) from open, and a tooltip that reveals detailed OHLC and volume when hovered over.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
Each bar represents the price action during a session and includes the session status, session name, closing price, change(%) from open, and a tooltip that reveals detailed OHLC and volume when hovered over.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_htaf8nf9_market_sessions_viewer_panel_by_muqwishi](../tv_htaf8nf9_market_sessions_viewer_panel_by_muqwishi.md)

## Source

https://www.tradingview.com/script/htAF8NF9-Market-Sessions-Viewer-Panel-By-MUQWISHI/

Publication ID: htAF8NF9. Source SHA-256: 36edfd3a699dc81df89f382fd1e1eb74db0d5a9af77a9da99689d50bcde3976f. Raw-description SHA-256: 5f8322a645dd5207f662f17895b88517d61077e8b512c7453405339ca7a76789.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
