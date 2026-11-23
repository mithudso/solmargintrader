---

id: tv_profile_yr3kt0ui

name: "Time-of-Day/Session Performance Stats [QuantAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Time-of-Day/Session Performance Stats ranks historical activity by hour and session to help traders focus on appropriate market windows. It separately measures range, volume, directional frequency and average open-to-close drift, avoiding the assumption that a high bullish bar count necessarily means positive average return. Session overlaps count in every involved session. The focus-hour plans are allocations of attention derived from rankings, not verified portfolio weights or a complete trading system. The author claims trailing-window overlays avoid repainting, but that implementation behavior is not independently established here."

registry_key: null

runner: null

evaluation: null

---

# Time-of-Day/Session Performance Stats [QuantAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Time-of-Day/Session Performance Stats ranks historical activity by hour and session to help traders focus on appropriate market windows. It separately measures range, volume, directional frequency and average open-to-close drift, avoiding the assumption that a high bullish bar count necessarily means positive average return. Session overlaps count in every involved session. The focus-hour plans are allocations of attention derived from rankings, not verified portfolio weights or a complete trading system. The author claims trailing-window overlays avoid repainting, but that implementation behavior is not independently established here.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for raw-range Activity, mean Volume, directional-bar Bias and mean open-to-close Drift by chosen hour/session buckets, plus their individual rankings. Aggregated edge/percentile ties, focus allocations and overlay timing remain outside this scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Assign usable historical bars to local-hour and enabled-session buckets under lookback/max-bar limits.
- Narrow ordinary statistics: for each local-hour/session bucket, average raw High−Low bar range for Activity and average bar volume for Volume. Bias=100×count(Close>Open)/(count(Close>Open)+count(Close<Open)), excluding flat bars. Drift is the mean open-to-close percentage change, 100×(Close−Open)/Open. Rank individual Activity/Volume/Bias/Drift boards by their respective values, and sessions by mean raw range per bar; equal-score ordering is unspecified.
- Average range/volume, exclude flat bars from bullish share, calculate mean percentage drift and combine percentile ranks into an aggregate.
- Discard underpopulated hours and rank sessions by average range per bar.

## Outputs and intended use

- Five ranking boards, session/focus panels, historical overlays and hour/session-transition alerts support scheduling research.

## Parameters and stated settings

- Four sessions and 24 hours; five boards. Mix top-two uses 80/20, conservative top-three 50/30/20; aggressive top-one and avoid lowest-range hour.
- Timezone, windows, weekday filtering, inclusion mode, minimum count and lookback are adjustable.
- Above one-hour chart interval warns of missing buckets; examples recommend 5/15/30m or 1H.
- Choose raw-price range mode to avoid the optional percent-of-close range convention. Caller supplies lookback days, hard bar ceiling, minimum bucket count, timezone, enabled sessions/custom HHMM-HHMM windows and bar/weekday inclusion settings; no numeric defaults for these are supplied.

## Failure modes and caveats

- Aggregated directional-edge definition is absent and can change rankings.
- Timezone/DST, partial bars and overlapping sessions affect samples.
- Historical rank leadership does not guarantee future activity or profitability.

## Missing information and implementation boundary

- Exact range-percentage denominator timing, edge formula, percentile ties, lookback defaults and overlay update cutoff are absent.

## Data requirements

Required inputs: intraday ohlcv, timezone/session configuration.

Repository input-class support: unavailable or unresolved. Requires adequate hourly/subhourly historical coverage and selected session boundaries; availability is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Five ranking boards
```

### E2: parameters

```text
80/20 weights
```

### E3: parameters

```text
50/30/20 weights
```

### E4: parameters

```text
higher than 1 hour
```

### E5: parameters

```text
5m, 15m, 30m, or 1h
```

### E6: mechanism, readiness

```text
mean percentile of range, volume, and directional edge
```

### E7: mechanism, parameters, readiness

```text
Range can be measured in percent of close or in raw price units.
```

### E8: mechanism, readiness

```text
Activity (average range), Volume (when the symbol reports it), Bias (percentage of directional bars that closed higher), Drift (mean close-minus-open percentage)
```

### E9: mechanism, readiness

```text
Flat bars are excluded
```

### E10: mechanism, readiness

```text
Orders hours by mean percentage change from open to close.
```

### E11: mechanism, parameters

```text
Hours that do not meet a minimum bar-count threshold are dropped from every ranking
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_yr3kt0ui_time_of_day_session_performance_stats_quantalgo](../../../strategy_research/tv_yr3kt0ui_time_of_day_session_performance_stats_quantalgo.md)

## Source

https://www.tradingview.com/script/Yr3kT0uI-Time-of-Day-Session-Performance-Stats-QuantAlgo/

Publication ID: Yr3kT0uI. Source SHA-256: 956800b7ab947f4e590fdbe684e50ef3967ed9ef6faa1e4cba6c13b210221cc5. Raw-description SHA-256: 58cf0e065f9e819711776549604ae7f1444dc8ac3db7f30bb2b3755d94def9d8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
