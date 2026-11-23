---

id: tv_profile_9uiewdmd

name: "Trend Following Moving Averages"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Trend Following Moving Averages colors a moving average according to whether its recent movement is large enough relative to the wider price range to count as a trend. It aims to answer a common chart-reading question: whether price is trending rather than merely oscillating. Instead of relying only on the average’s slope, the method compares the range occupied by the average with a longer price channel. Color intensity then conveys the estimated trend strength. The author’s claim of compatibility across timeframes is an intention of this normalization, not demonstrated invariance."

registry_key: null

runner: null

evaluation: null

---

# Trend Following Moving Averages

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trend Following Moving Averages colors a moving average according to whether its recent movement is large enough relative to the wider price range to count as a trend. It aims to answer a common chart-reading question: whether price is trending rather than merely oscillating. Instead of relying only on the average’s slope, the method compares the range occupied by the average with a longer price channel. Color intensity then conveys the estimated trend strength. The author’s claim of compatibility across timeframes is an intention of this normalization, not demonstrated invariance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the channel-width trend flag with chosen MA, trend window and percentage rate. Final color-intensity ratio and optional regression smoothing remain outside this narrow computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Construct a channel from the selected moving average’s highest and lowest values over a trend-check period.
- Let MAWidth be the maximum minus minimum of the selected MA over Period to Check Trend. Let PriceWidth be the highest high minus lowest low over 300 bars. The disclosed trend flag is MAWidth > (Trend Channel Rate % / 100) × PriceWidth. This flag is independently defined even though the subsequent intensity mapping is not.
- Optionally apply linear regression to reduce noise.

## Outputs and intended use

- The moving-average line becomes lighter/darker according to channel-relative strength.
- Use color as trend-regime context; no crossing entry or exit is specified.

## Parameters and stated settings

- Price channel spans 300 bars. MA choices are EMA, SMA, RMA, WMA and VWMA.
- Period to Check Trend and Trend Channel Rate % are adjustable; optional linear regression is said to add one or two bars of latency.
- The narrow trend flag takes a chosen MA type/length, Period to Check Trend and Trend Channel Rate %. No numeric defaults for these inputs are supplied; disable optional regression for this scope.

## Failure modes and caveats

- A long price-channel outlier can suppress the trend ratio after current conditions change.
- Noise reduction can delay detection, and the exact strength calculation is incompletely described.

## Missing information and implementation boundary

- MA length/default, exact strength ratio, regression window, direction coloring and order rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price extrema and selected moving averages, including volume-weighted variants, use OHLCV data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
highest and lowest point of last 300 bars
```

### E2: parameters

```text
EMA, SMA , RMA, WMA , VWMA
```

### E3: parameters, risks

```text
it may cause 1-2 bars latency.
```

### E4: outputs_and_use

```text
MA Line becomes lighter/darker
```

### E5: mechanism, readiness

```text
If the width of MA channel is greater than certain rate of price channel then it decides there is trend
```

### E6: parameters, mechanism

```text
"Period to Check Trend" is the period to create MA channel.
```

### E7: parameters

```text
"Trend Channel Rate %" is rate of price channel .
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_9uiewdmd_trend_following_moving_averages](../tv_9uiewdmd_trend_following_moving_averages.md)

## Source

https://www.tradingview.com/script/9UiewdMD-Trend-Following-Moving-Averages/

Publication ID: 9UiewdMD. Source SHA-256: 0303fe2c59cb350047b2daf0f8e26e8175f71a6f661f8d3b5d84b7e74cd28cbb. Raw-description SHA-256: 426f82d119c62141ac19b1880a79df6c33a9b493f2f48a3c2c77106acb24d6fc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
