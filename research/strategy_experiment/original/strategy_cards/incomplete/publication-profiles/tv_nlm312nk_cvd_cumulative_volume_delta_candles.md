---

id: tv_profile_nlm312nk

name: "CVD - Cumulative Volume Delta Candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Cumulative Volume Delta Candles approximates directional volume from intrabars and displays its accumulated path as candles. It aims to expose within-bar pressure and longer reset-period progression more precisely than assigning each whole chart candle a single sign. Users can compare CVD direction, wicks and price disagreement, while choosing a precision/history tradeoff. The method remains an approximation rather than bid/ask transaction classification. Reset choices define independent analysis chunks, so a trend across a reset cannot be interpreted as uninterrupted accumulated flow."

registry_key: null

runner: null

evaluation: null

---

# CVD - Cumulative Volume Delta Candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Cumulative Volume Delta Candles approximates directional volume from intrabars and displays its accumulated path as candles. It aims to expose within-bar pressure and longer reset-period progression more precisely than assigning each whole chart candle a single sign. Users can compare CVD direction, wicks and price disagreement, while choosing a precision/history tradeoff. The method remains an approximation rather than bid/ask transaction classification. Reset choices define independent analysis chunks, so a trend across a reset cannot be interpreted as uninterrupted accumulated flow.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Intrabar direction and flat-bar fallback, signed-volume aggregation, candle open/close and configurable reset modes define the principal CVD computation. Exact automatic precision selection is an optional data-selection caveat.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Sign intrabar volume by close versus open; for dojis use previous intrabar close, then last known polarity if still unchanged.
- Sum signed intrabars for each chart-bar delta and accumulate through the reset period.
- Build candle open from prior CVD close, close from aggregate delta and wicks from intrabar delta extremes.

## Outputs and intended use

- CVD candles, optional total-intrabar-volume candles, divergence coloring, reset background and LTF/coverage information box support flow analysis.

## Parameters and stated settings

- Reset choices: none, fixed HTF, fixed time, regular-session start or stepped HTF.
- Stepped mapping is sub-minute→1H, below 3H→1D, at most 12H→1W, below 1W→1M, otherwise 1Y.
- Precision options range from broad coverage to one-minute intrabars; total-volume candles default off.

## Failure modes and caveats

- Intraday/EOD and realtime/historical volume feeds can differ.
- Finer intrabars reduce historical chart coverage; missing activity affects totals.
- Candle polarity does not measure actual aggressor-side volume.

## Missing information and implementation boundary

- Exact LTF selection, reset default/timezone, intrabar-extreme construction and trade rules are absent.

## Data requirements

Required inputs: lower-timeframe ohlcv, session/timezone metadata.

Repository input-class support: unavailable or unresolved. Requires historical intrabars with volume and sufficient depth; chart OHLCV alone cannot reconstruct the CVD candles.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
last known polarity is used.
```

### E2: parameters

```text
None[/b]: Calculations do not reset.
```

### E3: parameters

```text
<  1min        1H
     <  3H          1D
     <= 12H         1W
     <  1W          1M
     >= 1W          1Y
```

### E4: parameters

```text
Most precise, 1min intrabars
```

### E5: parameters

```text
They are turned off by default
```

### E6: mechanism, risks

```text
sum of all intrabar ​​volume rather than the ​volume of the bar
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_doji](../../../strategy_research/tv_method_doji.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_nlm312nk_cvd_cumulative_volume_delta_candles](../tv_nlm312nk_cvd_cumulative_volume_delta_candles.md)

## Source

https://www.tradingview.com/script/NlM312nK-CVD-Cumulative-Volume-Delta-Candles/

Publication ID: NlM312nK. Source SHA-256: 206f01b6c3cfbe3062e9d793b2242a8ada9064ce79ff637f85b16bc74595736a. Raw-description SHA-256: 7063628c2e63b1eeb3b2afd2d28d32fd7b1e91ba40dd47c40a3078ec086386dc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
