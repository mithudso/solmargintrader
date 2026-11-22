---

id: tv_profile_uvby6vlf

name: "[MAD] Gann o Maticus"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Draw resetting Gann price-time boxes and curved geometric references using calendar periods or selected astronomical cycle boundaries."

registry_key: null

runner: null

evaluation: null

---

# [MAD] Gann o Maticus

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Draw resetting Gann price-time boxes and curved geometric references using calendar periods or selected astronomical cycle boundaries.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The main arc and astronomical event algorithms are undisclosed despite detailed configuration.

- Arc/coordinate equations
- Ephemeris and cycle-event computation
- Pivot/base-source/update contracts

## How it works

- Set horizontal extent by a timeframe or planetary event and vertical range from prior-cycle pivots/range,Donchian,ATR,standard-deviation or percentile bounds. Draw arcs from four corners,diagonals and changing pivot-level markers; astro mode shows last/next event and duration.

## Outputs and intended use

- Use geometric curves as discretionary potential reaction references. Planetary timing is a chosen segmentation scheme,not evidence of a causal financial relationship or validated forecasting edge.

## Parameters and stated settings

- Defaults include daily cycle,Moon/high latitude,Classic Pivots R3-to-S1,cleanup on; Donchian20,ATR14×2,StdDev20×2,percentile50 with10/90 bounds and minimum height0.5ATR. Several styling/arc families are configurable.

## Failure modes and caveats

- The description inconsistently calls StdDev center an SMA while Base Source discusses close/HL2/EMA for both band types. Astro ephemeris precision and event timing matter,particularly for long or unsupported Moon cycles.

## Missing information and implementation boundary

- Arc equations/normalization,classic pivot formulas,astronomical calculations,base-source inconsistency and update/freeze semantics are missing.

## Data requirements

Required inputs: ohlcv, planetary ephemeris/event times for astro mode.

Repository input-class support: unavailable or unresolved. Calendar/local-price modes use OHLCV,but the full astro feature set requires astronomical calculations/data not established by the description.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Timeframe / Cycle[/b] (Default: 1 Day)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Astro Planet[/b] (Default: Moon)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Astro Cycle[/b] (Default: High Latitude)
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Upper Pivot[/b] (Default: R3)
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Lower Pivot[/b] (Default: S1)
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Donchian Len[/b] (Default: 20)
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
ATR Len[/b] (Default: 14)
```

### E8: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
ATR Mult[/b] (Default: 2.0)
```

### E9: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
StdDev Len[/b] (Default: 20)
```

### E10: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Pct Len[/b] (Default: 50)
```

### E11: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Low %[/b] (Default: 10)
```

### E12: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
High %[/b] (Default: 90)
```

### E13: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Min Height (ATR Mult)[/b] (Default: 0.5)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_gann](../tv_method_gann.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_uvby6vlf_mad_gann_o_maticus](../tv_uvby6vlf_mad_gann_o_maticus.md)

## Source

https://www.tradingview.com/script/UVBy6VlF-MAD-Gann-o-Maticus/

Publication ID: UVBy6VlF. Source SHA-256: 56689c0b7eafa7264fdb467eb98bbe062398a1f68e326562afc4513abd822931. Raw-description SHA-256: 1c8fa749d2176bc0623d8a31a710d64ec5a7e0d74a78a30a8fe8fa155bbad03c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
