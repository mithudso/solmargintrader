---

id: tv_profile_ebb5mw6b

name: "Extreme Trend Reversal Points [HeWhoMustNotBeNamed]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Extreme Trend Reversal Points restricts moving-average reversal candidates to strongly ordered multi-level smoothing states. It recursively smooths an average repeatedly, measures their relative ordering and highlights price crosses only when the averages are fully aligned. The author emphasizes that such a cross can be a pullback or a reversal, then offers discretionary confirmation and breakout-box examples rather than a guaranteed reversal system."

registry_key: null

runner: null

evaluation: null

---

# Extreme Trend Reversal Points [HeWhoMustNotBeNamed]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Extreme Trend Reversal Points restricts moving-average reversal candidates to strongly ordered multi-level smoothing states. It recursively smooths an average repeatedly, measures their relative ordering and highlights price crosses only when the averages are fully aligned. The author emphasizes that such a cross can be a pullback or a reversal, then offers discretionary confirmation and breakout-box examples rather than a guaranteed reversal system.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Recursive SMA references is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Build recursively averaged levels and count relative pair ordering to form trend strength.
- Use percentile boundaries around the median for range/extreme classifications and mark price/average crosses in fully aligned trends.
- L1=SMA(source,length);Ln=SMA(previous recursive level,length). Previous level means L[n-1] in recursion,not a lagged bar. Caller chooses length/level count; strength,percentile and final trigger rules excluded.

## Outputs and intended use

- Inspect color-coded trend strength and triangle reversal candidates; proposed confirmations include waiting for range color or stop entries around pivots.
- Usable scope: Recursive SMA references. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Strength range is 0 to Level*(Level-1)/2. Inputs include levels, average settings, Range/Extreme Percentiles and Percentile History.
- A discretionary box example adds one ATR and uses reward ratios 1:1 for trend side and 1:1.5 for reversal side.

## Failure modes and caveats

- Analytical: recursive smoothing increases lag, and a cross against a fully ordered trend can repeatedly fail before reversal.

## Missing information and implementation boundary

- Average type/defaults, exact ordering population, percentile calculation and price-cross reference are not fully defined; pivot-box selection remains discretionary.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
0 to Level*(Level-1)/2
```

### E2: parameters, readiness

```text
1 ATR additional distance
```

### E3: parameters, readiness

```text
1:1 for bullish (trend side) and 1:1.5 for bearish side (reversal side)
```

### E4: mechanism, readiness

```text
price crosses the moving average while in complete trend
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
🎯 Recursive Multi Level Moving Averages
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
Using moving average crossover for identifying the change in trend is very common. However, this method can give lots of false signals during the ranging markets. In this algorithm, we try to find the extreme trend by looking at fully aligned multi-level moving averages and only look at moving average crossover when market is in the extreme trend - either bullish or bearish. These points can mean long term downtrend or can also cause a small pullback before trend continuation. In this discussion, we will also check how to handle different scenarios.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ebb5mw6b_extreme_trend_reversal_points_hewhomustnotbenamed](../tv_ebb5mw6b_extreme_trend_reversal_points_hewhomustnotbenamed.md)
- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/eBB5mW6b-Extreme-Trend-Reversal-Points-HeWhoMustNotBeNamed/

Publication ID: eBB5mW6b. Source SHA-256: 86a8c66c62eaf3f6e2f8795e92b4e1515b37ea09078794321757cfb00d094cdf. Raw-description SHA-256: d46dcc5f2299ddb2b82639a894b1335c9b5063612161b3bf19fde9adcc94bd50.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
