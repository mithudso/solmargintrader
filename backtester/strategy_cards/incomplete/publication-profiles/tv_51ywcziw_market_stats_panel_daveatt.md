---

id: tv_profile_51ywcziw

name: "Market Stats Panel [Daveatt]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Market Stats Panel brings a watchlist-style performance summary onto the chart. It combines recent horizon returns with year-by-year historical paths so a reader can inspect current performance and compare it with previous years. The panel supports both price-level and percentage views, addressing the different questions of absolute market level and relative change. The description focuses on visual reporting and historical comparison, not on a trading signal. Its current-year line updates as new observations arrive, while historical colored lines provide context for seasonal pattern inspection without proving that those patterns will repeat."

registry_key: null

runner: null

evaluation: null

---

# Market Stats Panel [Daveatt]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Stats Panel brings a watchlist-style performance summary onto the chart. It combines recent horizon returns with year-by-year historical paths so a reader can inspect current performance and compare it with previous years. The panel supports both price-level and percentage views, addressing the different questions of absolute market level and relative change. The description focuses on visual reporting and historical comparison, not on a trading signal. Its current-year line updates as new observations arrive, while historical colored lines provide context for seasonal pattern inspection without proving that those patterns will repeat.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The reported horizon-return bases and yearly normalization rules are absent.

- The reported horizon-return bases and yearly normalization rules are absent.

## How it works

- Collect monthly opens and timestamps through batched security requests, then arrange yearly paths as polylines.
- Calculate recent-horizon performance metrics and color positive/negative boxes.
- Scale axes, month labels and layout to the chosen years and price/percentage mode.

## Outputs and intended use

- Color-coded performance boxes summarize 1W, 1M, 3M, 6M, YTD and 1Y.
- Year-colored paths and absolute/percentage modes support historical comparison.

## Parameters and stated settings

- Start/end years, panel width, line thickness, box dimensions, spacing and position are adjustable.
- The author describes split historical requests covering indices 0–63 and 64–127; this is an implementation account, not verified current platform capacity.

## Failure modes and caveats

- Visual seasonal resemblance does not establish a forecast or trading edge.
- Data adjustments, partial periods and monthly sampling can alter the interpretation of the paths.

## Missing information and implementation boundary

- Exact return bases, adjustment treatment, missing-year handling and recent-period calculation rules are absent.
- No entry/exit, portfolio or risk-management method is supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical prices, monthly opens and timestamps are available as an OHLCV data class; actual history length and script implementation are unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose

```text
watchlist stats panel functionality directly to your charts.
```

### E2: parameters, outputs_and_use

```text
performance metrics (1W, 1M, 3M, 6M, YTD, 1Y)
```

### E3: parameters, mechanism, readiness

```text
The first request handles indices 0-63, while the second one takes care of indices 64-127.
```

### E4: mechanism, required_data

```text
batch of monthly open prices and timestamps
```

### E5: outputs_and_use

```text
Switch seamlessly between absolute prices and percentage returns
```

## Source

https://www.tradingview.com/script/51ywcZIw-Market-Stats-Panel-Daveatt/

Publication ID: 51ywcZIw. Source SHA-256: 1290dd9793008e7bce874407521b5ef70398bff4d3402e737aa9527a1ce3ee63. Raw-description SHA-256: b063df50c69ef96afda182e624eba0972bd0eb3ba884500850f995892e45125f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
