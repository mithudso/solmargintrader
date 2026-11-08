---

id: tv_profile_t1v41bl5

name: "Session Edge Profiler | Flux Charts"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Session Edge Profiler measures completed-session behavior and compares the developing session with its own weekday-filtered history. It aims to replace generic claims about Asia, London or New York with instrument-specific evidence. The dashboard covers range, volume, directional persistence, daily extremes and explicitly defined structural counts. Its alert identifies unusually large range rather than a directional trade. The source provides enough parameterized lifecycle and metric rules to reproduce a substantive session-statistics specification, while realistic execution and future profitability remain outside its purpose."

registry_key: null

runner: null

evaluation: null

---

# Session Edge Profiler | Flux Charts

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Session Edge Profiler measures completed-session behavior and compares the developing session with its own weekday-filtered history. It aims to replace generic claims about Asia, London or New York with instrument-specific evidence. The dashboard covers range, volume, directional persistence, daily extremes and explicitly defined structural counts. Its alert identifies unusually large range rather than a directional trade. The source provides enough parameterized lifecycle and metric rules to reproduce a substantive session-statistics specification, while realistic execution and future profitability remain outside its purpose.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source defines the financial computation and parameterized inputs sufficiently for a reproducible specification.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Track each enabled session’s OHLCV/events in New York time, commit completed records at the shifted trading-day boundary and filter history by selected weekday.
- Normalize session range by previous completed daily ATR; average normalized ranges and count historical values at/below the current normalized range for percentile.
- Bull means session close > session open. Continuation means its bullish/bearish direction matches the previous occurrence of that same session; exclude the first occurrence from the eligible denominator. Bull%=100×bull count/all sessions; Continuation%=100×matched count/eligible sessions. Volume share is session volume divided by summed completed enabled-session volume; daily-extreme flags compare session extremes with full trading-day extremes.
- At active-session bar t, bullish FVG is Low_t>High_(t−2), storing High_(t−2); bearish FVG is High_t<Low_(t−2), storing Low_(t−2). Later within the same session, invalidate/remove a bullish gap if close falls below its stored level or a bearish gap if close rises above its stored level. Survival%=100×(formed−invalidated)/formed at session end; later-session invalidation does not change that result.
- Confirm pivots with the chosen number of bars on each side. A subsequent close above a confirmed high or below a confirmed low increments the active-session swing-break counter and consumes that pivot so it cannot be counted again. A newly confirmed high above the previous tracked session high pivot increments HH; a newly confirmed low below the previous tracked session low pivot increments LL.

## Outputs and intended use

- Thirteen dashboard metrics, session boxes, live range/average/percentile label and high-percentile alert support session research.

## Parameters and stated settings

- Five default NY windows: Asia 19–02, London 02–08:30, NY AM 08:30–12, Lunch 12–13:30, PM 13:30–16. Day boundary 18:00 NY via six-hour shift.
- ATR length default 14, range 5–50; pivot strength default five each side, range 2–20. Weekdays default on, weekends off.
- Range alert exceeds 90th percentile. Tier cutoffs are 75/25 for percentile and 70/40 for FVG survival.

## Failure modes and caveats

- Live partial-session range is compared with complete historical sessions, so percentile is not time-of-session adjusted.
- Volume denominator is summed enabled completed sessions, not necessarily all market-day volume; overlaps can double-count.
- FVG survival means survival only until that session ends.

## Missing information and implementation boundary

- Tie/zero-denominator and interrupted-session edge cases need implementation choices; no trade-execution model is intended.

## Data requirements

Required inputs: intraday ohlcv, daily ATR history, New York timezone/session calendar.

Repository input-class support: unavailable or unresolved. The specification is substantive, but usable aligned intraday history/session coverage has not been established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Defaults: Asia 1900,0200, London 0200,0830, NY AM 0830,1200, NY Lunch 1200,1330, NY PM 1330,1600.
```

### E2: parameters

```text
shifting time forward by 6 hours
```

### E3: parameters

```text
18:00 NY time
```

### E4: parameters

```text
Range: 5 to 50. Default: 14.
```

### E5: parameters

```text
Range: 2 to 20. Default: 5.
```

### E6: parameters

```text
Range > 90th Percentile
```

### E7: parameters

```text
at or above 75
```

### E8: parameters

```text
at or below 25
```

### E9: parameters

```text
at or above 70
```

### E10: parameters

```text
at or above 40
```

### E11: mechanism, readiness

```text
counting how many past sessions have a normalized range less than or equal to the current value
```

### E12: mechanism, readiness

```text
current bar's low sits above the high from two bars ago
```

### E13: mechanism, readiness

```text
session volume divided by total day volume, multiplied by 100
```

### E14: mechanism, readiness

```text
Continuation is true when the previous occurrence of the same session was bullish in the same direction (both bullish or both bearish).
```

### E15: mechanism, readiness

```text
The very first occurrence in history has no previous reference and is excluded from the continuation calculation.
```

### E16: mechanism, readiness

```text
a bullish FVG forms when the current bar's low sits above the high from two bars ago, and a bearish FVG forms when the current bar's high sits below the low from two bars ago.
```

### E17: mechanism, readiness

```text
If price closes below a bullish FVG's level, or closes above a bearish FVG's level, the gap is treated as invalidated and removed from the active list
```

### E18: mechanism, readiness

```text
When a pivot high confirms and price subsequently closes above that pivot level, a bullish swing break fires and the pivot is consumed (cleared from active tracking).
```

### E19: mechanism, readiness

```text
When a new pivot high confirms with a level greater than the session's previous tracked pivot high, the session's HH counter increments.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fair_value_gap](../../tv_method_fair_value_gap.md)
- [tv_method_liquidity_sweep](../../tv_method_liquidity_sweep.md)
- [tv_t1v41bl5_session_edge_profiler_flux_charts](../../tv_t1v41bl5_session_edge_profiler_flux_charts.md)

## Source

https://www.tradingview.com/script/T1V41Bl5-Session-Edge-Profiler-Flux-Charts/

Publication ID: T1V41Bl5. Source SHA-256: 271860187f2b91e21efbb9120f6515c44d63f8f7293f1794534063488f34d545. Raw-description SHA-256: ca09c3ee289f020d7ca8fb5e884daeb982cc72257c406c387f1c24fa15fdc230.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
