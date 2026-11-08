---

id: tv_profile_n0f50jkv

name: "Relative Volume at Time"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Relative Volume at Time compares current participation with historical participation at the same offset inside a chosen time unit. It addresses recurring intraday or weekly volume cycles that an ordinary rolling average can obscure. Users can compare either cumulative activity since the anchor or a single matched-offset bar. The normalized result supports comparisons across markets, while the directional variant signs volume by bar direction rather than claiming to observe actual buying and selling."

registry_key: null

runner: null

evaluation: null

---

# Relative Volume at Time

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Relative Volume at Time compares current participation with historical participation at the same offset inside a chosen time unit. It addresses recurring intraday or weekly volume cycles that an ordinary rolling average can obscure. Users can compare either cumulative activity since the anchor or a single matched-offset bar. The normalized result supports comparisons across markets, while the directional variant signs volume by bar direction rather than claiming to observe actual buying and selling.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The main relative-volume calculation and parameterized variants are explicitly defined.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Divide cumulative volume since a unit begins by the mean cumulative volume through the same offset in prior units; alternatively divide one bar by the mean of matching-offset prior bars.
- Select automatic, fixed or time-of-day anchors. Automatic units step from minute/hour/day through week/month/year according to chart resolution.
- Apply Hull smoothing, optional sign by up/down bar, and fixed, mean-plus/minus-standard-deviation or historical high/low thresholds.

## Outputs and intended use

- Display raw/current versus historical columns, relative columns, smoothed relative volume or signed relative volume.
- Color-state transitions create markers and alerts; the source leaves the individual eight selectable conditions unnamed.

## Parameters and stated settings

- Fixed threshold defaults to 2.0; fixed channel lookback defaults to 100.
- Lookbacks exceeding 5000 chart bars are adjusted; only the latest 500 value labels display.

## Failure modes and caveats

- Realtime volume is incomplete until bar close. Daily and intraday feeds can disagree.
- Volume alone has no price direction or guarantee of substantial movement.

## Missing information and implementation boundary

- Eight optional coloring predicates, missing-offset handling and zero-volume denominator handling are not enumerated; these do not prevent the core matched-volume computation.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The calculation uses chart OHLCV rather than an external data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
current volume[/i] = the cumulative volume since the beginning of the timeframe unit
```

### E2: mechanism

```text
past volume[/i] = the mean of volume during that same relative period of time in the past [i]n[/i] timeframe units.
```

### E3: parameters

```text
The default value is 2.0.
```

### E4: parameters

```text
Its default is 100.
```

### E5: parameters

```text
Only the last 500 values will be shown.
```

### E6: parameters

```text
greater than 5000 bars.
```

### E7: risks

```text
realtime bars must be complete for the relative volume value to be confirmed.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_n0f50jkv_relative_volume_at_time](../../tv_n0f50jkv_relative_volume_at_time.md)

## Source

https://www.tradingview.com/script/n0f50JKv-Relative-Volume-at-Time/

Publication ID: n0f50JKv. Source SHA-256: 44e8ec3100c7c2254dcc00187d22df9f6038b2b80f389ec3eb592bd240e5cf80. Raw-description SHA-256: 0c62ce6de51fd2026410f099b78ea7349a88d3bb782a4b521b07cccbdfe8c499.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
