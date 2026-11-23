---

id: tv_profile_lrdshlst

name: "Sniffer"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Sniffer searches historical chart windows for formations resembling a user-selected candle sequence. It avoids a fixed named-pattern catalog by comparing feature vectors, so the same workflow can examine a single candle or a multi-candle structure. The resulting boxes provide historical analogues for further inspection; similarity is not a forecast or measured probability of a particular outcome. The user controls which features and distance definition matter, making the results dependent on the chosen representation."

registry_key: null

runner: null

evaluation: null

---

# Sniffer

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Sniffer searches historical chart windows for formations resembling a user-selected candle sequence. It avoids a fixed named-pattern catalog by comparing feature vectors, so the same workflow can examine a single candle or a multi-candle structure. The resulting boxes provide historical analogues for further inspection; similarity is not a forecast or measured probability of a particular outcome. The user controls which features and distance definition matter, making the results dependent on the chosen representation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Blocking calculation or data contracts remain.

- Feature normalization, sequence comparison and similarity scoring formulas are unspecified.

## How it works

- Map bar range, signed body, volume, directional head/tail wicks and their ratios into features; optional momentum and directional indicators expand the vector.
- Compare candidate sequences with the chosen input using cosine, Euclidean, Lorentzian, Manhattan or Pearson methods, then sort and retain top matches.

## Outputs and intended use

- White marks the input; green, yellow and red divide matches into upper, middle and lower thirds.
- Optional box text shows similarity percentages; adjust the input time range after changing timeframe.

## Parameters and stated settings

- The processing discussion says maximum 5000 bars, while final notes restrict displayed matches to 4500 bars.
- Top-match count, lookback, feature set and distance method are user inputs.

## Failure modes and caveats

- Feature scaling and correlated dimensions can dominate distances.
- The author reports array-bound errors during input setup; the two historical limits should not be conflated.

## Missing information and implementation boundary

- Vector normalization, sequence aggregation, indicator lengths and distance-to-percentage conversion are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the stated input class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
candles are back-tracked and degree of similarity is computed for every single bar(max-limit is 5000 bars).
```

### E2: parameters, risks

```text
Similarity matches will be shown only within last 4500 bars.
```

### E3: mechanism

```text
Different distance calculation methods are available to choose from, such as Cosine, Euclidean, Lorentzian, Manhattan, & Pearson
```

### E4: mechanism

```text
Range: Difference between high & low
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lrdshlst_sniffer](../tv_lrdshlst_sniffer.md)
- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_double_top_bottom](../tv_method_double_top_bottom.md)
- [tv_method_morning_evening_star](../tv_method_morning_evening_star.md)

## Source

https://www.tradingview.com/script/lrDsHLST-Sniffer/

Publication ID: lrDsHLST. Source SHA-256: b5ff650500d96d4d28b527e79beeb8dc0fe9582be8f2274529bb170b47b554b5. Raw-description SHA-256: a9c3c31c4c7c4496e12fda538d5de55638b0637ebfb90cbe21d54601fcd75a4a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
