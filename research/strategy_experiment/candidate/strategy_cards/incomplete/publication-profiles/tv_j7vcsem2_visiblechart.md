---

id: tv_profile_j7vcsem2

name: "VisibleChart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "VisibleChart calculates statistics over the chart viewport, including a volume-weighted price reference. Its financial purpose is explicit through visible OHLCV, average/median prices and VWAP, even though many functions also support generic drawing placement. It aims to let research overlays follow the currently inspected price history. Scrolling or zooming changes the sample and recalculates all bars, so these outputs are viewport-conditioned summaries, not stable historical trading signals. Correct final extrema are known only after the rightmost visible bar has been processed."

registry_key: null

runner: null

evaluation: null

---

# VisibleChart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

VisibleChart calculates statistics over the chart viewport, including a volume-weighted price reference. Its financial purpose is explicit through visible OHLCV, average/median prices and VWAP, even though many functions also support generic drawing placement. It aims to let research overlays follow the currently inspected price history. Scrolling or zooming changes the sample and recalculates all bars, so these outputs are viewport-conditioned summaries, not stable historical trading signals. Correct final extrema are known only after the rightmost visible bar has been processed.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source defines a reproducible parameterized computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Filter bars between viewport opening timestamps and accumulate visible OHLCV/extrema/indices.
- Compute average, median and volume-weighted source values over visible bars.
- Expose percentage-based price/time/index positions and conditional value arrays.

## Outputs and intended use

- Reusable visible-range summaries and VWAP support chart research/drawing.

## Parameters and stated settings

- Average/median default source close; VWAP defaults hlc3. whenVisible condition defaults true and length all values.
- Percentage positioning example50 means midpoint.

## Failure modes and caveats

- Viewport selection introduces hindsight if used as a trading signal.
- Functions must execute every bar and not assume visible right edge equals dataset end.

## Missing information and implementation boundary

- Extrema tie and zero-volume handling are not specified; chartXIndexPct return prose mistakenly repeats timestamp semantics.

## Data requirements

Required inputs: ohlcv, viewport left/right timestamps.

Repository input-class support: unavailable or unresolved. OHLCV supplies values, but the selected viewport is user-provided and not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
volume-weighted average for visible chart bars.
```

### E2: parameters

```text
Default is `hlc3`.
```

### E3: parameters

```text
Default is `close`.
```

### E4: parameters

```text
default is `true`.
```

### E5: parameters

```text
default is all values.
```

### E6: parameters

```text
50 is halfway
```

## Source

https://www.tradingview.com/script/j7vCseM2-VisibleChart/

Publication ID: j7vCseM2. Source SHA-256: a7ca5b02d13675df9797a452f529e44393e8836efdc5cc3bf06f74351cc04cbf. Raw-description SHA-256: 4892c6a97c2d48b2794390b0370c1a2f5d596efb3ae0ebf3412c7baf95dc94bb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
