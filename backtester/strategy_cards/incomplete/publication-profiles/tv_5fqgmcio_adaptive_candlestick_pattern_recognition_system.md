---

id: tv_profile_5fqgmcio

name: "Adaptive Candlestick Pattern Recognition System"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Recognize configurable candlestick formations and summarize their subsequent returns by market-range location. Adaptive label colors communicate historical pattern behavior rather than assigning textbook bullish/bearish labels unconditionally."

registry_key: null

runner: null

evaluation: null

---

# Adaptive Candlestick Pattern Recognition System

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Recognize configurable candlestick formations and summarize their subsequent returns by market-range location. Adaptive label colors communicate historical pattern behavior rather than assigning textbook bullish/bearish labels unconditionally.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Elementary candle predicates/classic event returns is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Classic mode measures next-open to a selected future close after pattern detection. Breakout mode waits for a close at/beyond pattern high or low within a configurable confirmation window; nonconfirming patterns lose labels and are excluded.
- Prior trend comes from price relative to a chosen average or shorter versus longer averages, sampled before the pattern. Returns partition by higher-timeframe price-range location and update arrays of mean, median, deviation and positive/neutral/negative counts.
- Nested patterns can be overridden by larger formations and stop contributing returns. Target mode deliberately changes that behavior. Adaptive coloring compares pattern statistics across the matrix, optionally clipping at fixed tolerance limits.
- Range engulfing:second.high>=first.high AND second.low<=first.low;body engulfing:second body interval contains first body interval. Caller inclusive toggle chooses equality versus strict endpoints. Doji:abs(close-open)<=caller_tolerance*(high-low). On fixed supplied detections,classic forward return=100*(selected_future_close/next_open-1),measured only after future close matures. Full85-pattern detection,trend variants,confidence and override timing remain excluded.

## Outputs and intended use

- Pattern labels/tooltips show names, range partition and historical statistics; switches/target mode limit visible formations while enabled patterns can continue accumulating observations.
- The author encourages parameter experimentation, while warning historical conditional returns and confidence displays do not guarantee future behavior.
- Usable scope: Elementary candle predicates/classic event returns. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Recognizes85 patterns spanning one to five candles. Breakout confirmation allows one to five candles; detection has a one-candle offset.
- Default range partitions use yearly high/low: top20%, middle80%–33%, bottom33%. Extensive body/range/wick, engulfing, gap and equality tolerances, two averages and sample/return horizons control detection.

## Failure modes and caveats

- Selection, overlapping returns and adaptive color comparisons create multiple-testing and sample-dependence risks. Labels require future outcome maturity and must not be mistaken for contemporaneously known performance.
- Target mode can retain otherwise overridden patterns and duplicate returns; disabling component dojis affects composite patterns. Equal average lengths force MA1 even with different types.

## Missing information and implementation boundary

- Complete logical definitions and defaults for all patterns, confidence-interval calculation and return/override update timing are not provided.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV supports candlestick geometry, range partitions and subsequent-return observations; the missing pattern logic is a specification rather than raw-data gap.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
recognizes 85 different candlestick patterns ranging from one to five candles
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
from one to five
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
this script has an offset of 1 by default.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
the 'Upper' partition is the top 20%
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
the 'Middle' partition is 80% to 33%
```

### E6: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
the 'Lower' partition covers the trading range within 33%
```

### E7: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
potentially leading to duplicate returns being included
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
RANGE: If the second candle's high-low range completely covers the high-low range of the prior candle, this is recognized as 'engulfing'.
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
BODY: If the second candle's open-close completely covers the open-close of the previous candle, this is recognized as 'engulfing'. [b](SEE LIMITATIONS)[/b]
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
    [*] Doji Tolerance - How large the body of a candle may be compared to the range to be considered a 'Doji'.
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
        percentReturn = ( (close - open[ i_PnLSample ] ) / open[ i_PnLSample ] ) * 100%
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5fqgmcio_adaptive_candlestick_pattern_recognition_system](../tv_5fqgmcio_adaptive_candlestick_pattern_recognition_system.md)
- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_doji](../../tv_method_doji.md)
- [tv_method_engulfing](../../tv_method_engulfing.md)
- [tv_method_hammer](../tv_method_hammer.md)
- [tv_method_morning_evening_star](../tv_method_morning_evening_star.md)
- [tv_method_shooting_star](../tv_method_shooting_star.md)
- [tv_method_three_soldiers_crows](../tv_method_three_soldiers_crows.md)

## Source

https://www.tradingview.com/script/5FQgMCiO-Adaptive-Candlestick-Pattern-Recognition-System/

Publication ID: 5FQgMCiO. Source SHA-256: 889e463f21cb36e6d48d2cf877d287b741190dbffdd4f559a2076f3c51a5b3e8. Raw-description SHA-256: fbd84d8760e90bdce2bcfa34c1d184cb1fee68ad3bfa96f06f365753d88958f4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
