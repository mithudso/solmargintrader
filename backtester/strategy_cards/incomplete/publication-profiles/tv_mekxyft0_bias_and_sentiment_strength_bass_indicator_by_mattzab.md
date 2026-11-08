---

id: tv_profile_mekxyft0

name: "Bias And Sentiment Strength (BASS) Indicator by mattzab"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "BASS overlays several familiar momentum histograms and a volume-weighted price bias to give a quick visual view of directional agreement. It is not a weighted composite score: positive blue and negative red components can coexist, which the author calls a battle between bulls and bears. Purple volume-bias bars supply a separate conviction check, including warnings when bullish momentum lacks positive volume-weighted bias."

registry_key: null

runner: null

evaluation: null

---

# Bias And Sentiment Strength (BASS) Indicator by mattzab

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

BASS overlays several familiar momentum histograms and a volume-weighted price bias to give a quick visual view of directional agreement. It is not a weighted composite score: positive blue and negative red components can coexist, which the author calls a battle between bulls and bears. Purple volume-bias bars supply a separate conviction check, including warnings when bullish momentum lacks positive volume-weighted bias.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The independent volume-bias output is explicitly same-length VWMA minus SMA with length30; additional standard-indicator overlays require their own parameters.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Overlay MACD histogram, zero-centered RSI, slow-stochastic D-minus-K, Awesome Oscillator and an Alligator-derived expression.
- Compute volume bias as the difference between a VWMA and SMA of equal length; color it purple.

## Outputs and intended use

- Blue above zero suggests positive sentiment, red below zero negative; mixed colors call for caution. The author proposes bullish sentiment plus positive volume bias as long context.

## Parameters and stated settings

- RSI is centered at its conventional 50 line. Slow stochastic uses K 21, D 14 and K smoothing 14. Volume bias uses 30-period VWMA minus 30-period SMA.

## Failure modes and caveats

- Analytical: related momentum components are correlated and an overlay can obscure disagreement; the printed Alligator expression may retain a price-level term.

## Missing information and implementation boundary

- Standard-indicator defaults, source series, exact color aggregation and complete entry/exit rules are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
21 Period K, 14 Period D, and 14 Smoothing K.
```

### E2: parameters, readiness

```text
50 line on a normal RSI chart.
```

### E3: parameters, mechanism, readiness

```text
30 Period Volume-Weighted Moving Average Minus the 30 Simple Moving Average.
```

### E4: mechanism, risks, readiness

```text
(lips + teeth) + (teeth - jaw)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mekxyft0_bias_and_sentiment_strength_bass_indicator_by_mattzab](../../../strategy_research/tv_mekxyft0_bias_and_sentiment_strength_bass_indicator_by_mattzab.md)

## Source

https://www.tradingview.com/script/MEKxYFt0-Bias-And-Sentiment-Strength-BASS-Indicator-by-mattzab/

Publication ID: MEKxYFt0. Source SHA-256: 5376c58ccc4008c54ecf8744ac90e39c619ea79f208da0784ef2d3bad9b549f7. Raw-description SHA-256: 75bc983e5e5629a74a96ca7ca869783e6891301cd68c99d34fe36c22844d4213.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
