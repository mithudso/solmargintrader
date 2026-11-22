---

id: tv_profile_bdk3oefq

name: "TASC 2025.11 The Points and Line Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Points and Line Chart transforms regularly sampled prices into an irregular price-movement display. Its aim is to compress long histories and clarify support/resistance or classic chart patterns while retaining actual source closes instead of always snapping them to fixed point intervals. The resulting chart is a separate interpretation of regular candles; the source advises hiding the underlying series rather than reading both as though they share the same time layout. A companion histogram preserves information about accumulated volume or elapsed source bars between plotted points."

registry_key: null

runner: null

evaluation: null

---

# TASC 2025.11 The Points and Line Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Points and Line Chart transforms regularly sampled prices into an irregular price-movement display. Its aim is to compress long histories and clarify support/resistance or classic chart patterns while retaining actual source closes instead of always snapping them to fixed point intervals. The resulting chart is a separate interpretation of regular candles; the source advises hiding the underlying series rather than reading both as though they share the same time layout. A companion histogram preserves information about accumulated volume or elapsed source bars between plotted points.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Point acceptance, scaling tables and reversal/intrabar ordering rules are missing.

- Point acceptance, scaling tables and reversal/intrabar ordering rules are missing.

## How it works

- Filter movements using point/figure-style scaling by default, with ATR and percentage alternatives, and require a reversal amount in steps.
- Plot actual closes by default; alternatives use directional highs/lows or close-filtered point-size intervals.
- Construct optional OHLC drawings from price action between accepted points and aggregate volume/bar counts.

## Outputs and intended use

- Line or candle display, hover details and volume/elapsed-bar histogram support compact market-structure inspection.
- Overlay/separate-pane and None options control each display.

## Parameters and stated settings

- Reversal Amount, Scale size Method and P&L Method are configurable.
- Published limits are 10,000 line points, 500 candle/tooltip points and 3,333 histogram points.
- The Days setting counts source bars and represents days only on 1D charts.

## Failure modes and caveats

- Irregular spacing compresses elapsed time and can conceal path-dependent execution risk.
- Synthetic candle OHLC should not be treated as ordinary time-bar fills.

## Missing information and implementation boundary

- Exact scaling tables, ATR length, percentage defaults, point acceptance and intrabar ordering rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The source explicitly transforms standard regular-series candles; OHLCV supplies the disclosed data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, purpose, readiness

```text
plots the closing price from RTS data.
```

### E2: parameters

```text
10,000 P&L points.
```

### E3: parameters

```text
up to 500 points.
```

### E4: parameters

```text
up to 3,333 points.
```

### E5: parameters, risks

```text
represents days only if the chart uses the "1D" timeframe.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bdk3oefq_tasc_2025_11_the_points_and_line_chart](../tv_bdk3oefq_tasc_2025_11_the_points_and_line_chart.md)
- [tv_method_renko](../tv_method_renko.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/BDk3oEFQ-TASC-2025-11-The-Points-and-Line-Chart/

Publication ID: BDk3oEFQ. Source SHA-256: 1828645ec131258e628276b05fdd1c879addeda24439be2b4c41bd55f2766768. Raw-description SHA-256: da3e222b8a526c660fcfc48ccc983fdb8cc1b4a7361526f5061e0f0795729317.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
