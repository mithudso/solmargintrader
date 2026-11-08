---

id: tv_profile_x8mujqgt

name: "BjCandlePatterns"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "BjCandlePatterns supplies reusable Japanese-candlestick predicates, helper measurements and optional labels for financial scripts. It spans single-bar shapes, engulfing and harami formations, gaps, stars, multi-bar continuation structures and soldiers/crows. The author intentionally omits trend and average-size filters in some patterns so callers can apply their own context. Consequently, a true predicate indicates a geometric candidate, not a complete setup or demonstrated reversal probability."

registry_key: null

runner: null

evaluation: null

---

# BjCandlePatterns

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

BjCandlePatterns supplies reusable Japanese-candlestick predicates, helper measurements and optional labels for financial scripts. It spans single-bar shapes, engulfing and harami formations, gaps, stars, multi-bar continuation structures and soldiers/crows. The author intentionally omits trend and average-size filters in some patterns so callers can apply their own context. Consequently, a true predicate indicates a geometric candidate, not a complete setup or demonstrated reversal probability.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for explicit wick/body/range/percentage/midpoint and strict real-body gap helpers. Full pattern catalog and contradictory lowestBody/gapUp semantics remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow unambiguous candle helpers: TopWick=H−max(O,C), BottomWick=min(O,C)−L, Body=abs(C−O), Range=H−L, BodyPct=100×Body/Range for Range>0, and MidBody=(O+C)/2. Body-up-gap means min(O_t,C_t)>max(O_(t−1),C_(t−1)); body-down-gap means max(O_t,C_t)<min(O_(t−1),C_(t−1)), i.e. no overlap. Equality is not a strict gap; this scope does not adopt the contradictory gapUp/lowestBody descriptions.
- Return Boolean pattern detections with configurable body/wick proportions for selected shapes.
- Expose wick length, absolute body, body extremes, range, body percentage, midpoint and gap tests.
- Separate detection functions from label helpers and a high/low wrapping box function.

## Outputs and intended use

- Combine predicates with caller-supplied trend, size and risk filters.
- Optional labels identify detections; helper outputs support custom candlestick logic.

## Parameters and stated settings

- Doji body defaults to 5% and opposite-wick ratio to 2. Hammer/star body defaults 33% and opposite wick 5%.
- Spinning-top wick default 34%; long-shadow default 75%; soldiers/crows wick default 5%. Labels default false and engulfing wick filtering defaults disabled.
- Supply valid OHLC and require positive range for BodyPct. These helper outputs have no lookback defaults; body-gap helpers compare current and preceding candles.

## Failure modes and caveats

- Several no-argument pattern predicates lack geometric rules in the prose.
- gapUp documentation incorrectly repeats a down-gap definition; lowestBody description incorrectly says highest.

## Missing information and implementation boundary

- Exact multi-bar inequalities, gap tolerances, zero-range behavior and contradictory helper semantics require code.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the default data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Default is 5.0 (5%)
```

### E2: parameters

```text
Default is 2
```

### E3: parameters

```text
Default is 33%.
```

### E4: parameters

```text
Default is 5%.
```

### E5: parameters

```text
Default is 34%
```

### E6: parameters

```text
Default is 75%
```

### E7: parameters

```text
Default is 5%
```

### E8: parameters

```text
Default is false
```

### E9: parameters

```text
Default is 0% (Disables wick detection).
```

### E10: risks

```text
some patterns are without filters such as comparisons to average candle sizing, or trend detection
```

### E11: missing_information

```text
[b]gapUp()[/b] returns true if there is a gap down
```

### E12: mechanism, parameters, readiness

```text
distance from the top of the candle body to its high
```

### E13: mechanism, parameters, readiness

```text
distance from the bottom of the candle body to its low
```

### E14: mechanism, parameters, readiness

```text
distance between the top and the bottom of the candle body
```

### E15: mechanism, parameters, readiness

```text
percentage of body size to the overall candle size
```

### E16: mechanism, parameters, readiness

```text
center point of the distance bewteen the body low and the body high
```

### E17: mechanism, parameters, readiness

```text
gap up and no overlap in the real bodies of the current candle and the preceding candle
```

### E18: mechanism, parameters, readiness

```text
gap down and no overlap in the real bodies of the current candle and the preceding candle
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_doji](../../../strategy_research/tv_method_doji.md)
- [tv_method_engulfing](../../../strategy_research/tv_method_engulfing.md)
- [tv_method_hammer](../tv_method_hammer.md)
- [tv_method_harami](../tv_method_harami.md)
- [tv_method_morning_evening_star](../tv_method_morning_evening_star.md)
- [tv_method_three_soldiers_crows](../tv_method_three_soldiers_crows.md)

## Source

https://www.tradingview.com/script/x8mUJqGT-BjCandlePatterns/

Publication ID: x8mUJqGT. Source SHA-256: 844f6510428b18e5938c933f8551e73dc03a741024555a350c003a8f48aa1fe9. Raw-description SHA-256: 7de9ddf45a7aa64c1a8a49f7e2a2a3bcb4f306896282d8dc6252789248bad312.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
