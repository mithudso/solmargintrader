---

id: tv_profile_drx2sbyv

name: "VIX Curve Pro - Real-Time Term Structure with Statistics"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "VIX Curve Pro displays volatility-index values across maturities as a spatial curve and summarizes their historical relationships. Its aim is to identify upward- versus downward-sloping volatility structures and whether current ratios sit near historical extremes. Traders can use that context for volatility or options research, but the curve is a comparison of maturity-specific volatility indexes, not a directly specified tradable futures portfolio. The author’s example contradicts the earlier regime definitions by calling short-term volatility below long-term volatility backwardation; this inconsistency must be resolved before relying on its labels."

registry_key: null

runner: null

evaluation: null

---

# VIX Curve Pro - Real-Time Term Structure with Statistics

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

VIX Curve Pro displays volatility-index values across maturities as a spatial curve and summarizes their historical relationships. Its aim is to identify upward- versus downward-sloping volatility structures and whether current ratios sit near historical extremes. Traders can use that context for volatility or options research, but the curve is a comparison of maturity-specific volatility indexes, not a directly specified tradable futures portfolio. The author’s example contradicts the earlier regime definitions by calling short-term volatility below long-term volatility backwardation; this inconsistency must be resolved before relying on its labels.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable narrowly for the raw maturity-ordered VIX curve, given external maturity series. Derived ratios/percentiles, regime labels and full feed-symbol mapping remain limitations; the contradictory backwardation example is preserved.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independent raw curve: obtain contemporaneous values for the supplied 9-day, 30-day, 3-month, 6-month and 1-year VIX maturity series, order those observations from shortest to longest maturity and connect their untransformed values as a curve. This does not require the optional ratio, percentile or regime predicates.
- Collect VIX values at several horizons and connect them as a maturity curve.
- Calculate historical ratio percentiles and lookback minimum, maximum, average and median statistics.
- Flag curve inversions and regime changes; flips can drive alerts.

## Outputs and intended use

- Curve, statistical tables, regime/inversion indicators and optional explanatory guide support volatility-context inspection.

## Parameters and stated settings

- Maturities are 9D, 30D, 3M, 6M and 1Y.
- Lookback and alert configuration are mentioned without numeric defaults.
- Raw curve maturity order is 9D, 30D, 3M, 6M, 1Y. Exact spatial spacing and the full feed-symbol mapping are not supplied.

## Failure modes and caveats

- The source’s example reverses its own contango/backwardation terminology.
- Index term structure does not directly determine futures roll yield or option execution outcomes.

## Missing information and implementation boundary

- Exact ratios, percentile convention, curve/regime predicate, index symbols for every maturity, lookback defaults and trading rules are absent.

## Data requirements

Required inputs: maturity-specific VIX index histories.

Repository input-class support: unavailable or unresolved. Requires synchronized external volatility-index series; ordinary chart OHLCV does not establish that coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, required_data

```text
different VIX maturities (9D, 30D, 3M, 6M, 1Y)
```

### E2: mechanism, readiness

```text
upward-sloping curve (contango)
```

### E3: mechanism

```text
downward-sloping curve (backwardation)
```

### E4: risks

```text
backwardation (short term vix is lower than long term)
```

### E5: outputs_and_use

```text
min/max/average/median values over lookback period
```

### E6: mechanism, parameters, readiness

```text
different VIX maturities (9D, 30D, 3M, 6M, 1Y) as a single curve.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_drx2sbyv_vix_curve_pro_real_time_term_structure_with_statistics](../tv_drx2sbyv_vix_curve_pro_real_time_term_structure_with_statistics.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/DRX2SbYV-VIX-Curve-Pro-Real-Time-Term-Structure-with-Statistics/

Publication ID: DRX2SbYV. Source SHA-256: 5d62e7b2f3a611daaf6576a421423237d1519c02281dc3632a3f460eed9570de. Raw-description SHA-256: 313a993724244258c55da4ef281a8da06d4a02524d9196ab091f75032588756f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
