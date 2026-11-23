---

id: tv_profile_jpbq3j0s

name: "T-Virus Sentiment [hapharmonic]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Blend several technical conditions into a stylized sentiment gauge while separately depicting estimated volume pressure."

registry_key: null

runner: null

evaluation: null

---

# T-Virus Sentiment [hapharmonic]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Blend several technical conditions into a stylized sentiment gauge while separately depicting estimated volume pressure.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Some bands are explicit, but overlapping/vague component states and volume-pressure/percent mappings prevent a reproducible composite.

- Complete nonoverlapping scoring priority
- Score-to-percent and pressure equations
- Component defaults and vague-strength tolerances

## How it works

- Score RSI,EMA alignment,MACD,ADX/DI,Ichimoku,Bollinger position and OBV from one-to-five and average them into an Active-percent gauge. Use visible-range or fixed-lookback volume pressure for bubbles; mascot is green only when both sentiment and buy pressure exceed half.

## Outputs and intended use

- Indicator labels occupy five sentiment zones inside a vial/helix and tooltips explain component placement. It is explicitly a confluence dashboard rather than a direct buy/sell system; artistic styling does not remove its financial purpose.

## Parameters and stated settings

- RSI score bands use80/70/30/20,EMA lengths9/21/50/100/200/250 and ADX references20/25/40. Visible-range pressure is default; mascot test uses50%,with suggested75/25 extreme sentiment context. Underlying lengths and display are configurable.

## Failure modes and caveats

- The score mixes contrarian RSI oversold-is-bullish logic with trend-following components, so agreement has no universal interpretation. Several rules overlap or use vague near/strong criteria; viewport pressure changes with zoom.

## Missing information and implementation boundary

- Exact five-score-to-percent mapping,buy-pressure formula,tie/priority rules,near-zero/MA tolerances,MACD acceleration and complete indicator defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV supports the disclosed technical inputs; missing scoring/algorithm contracts are separate specification gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
average from 7 different technical analysis tools
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
score from 1 (strong bearish pressure) to 5
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
both[/b] be above 50%
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
multiple EMAs (9, 21, 50, 100, 200, 250)
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
RSI > 80
```

### E6: purpose, mechanism, outputs_and_use, parameters, readiness

```text
20 ≤ ADX < 25
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jpbq3j0s_t_virus_sentiment_hapharmonic](../tv_jpbq3j0s_t_virus_sentiment_hapharmonic.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/jpbq3J0S-T-Virus-Sentiment-hapharmonic/

Publication ID: jpbq3J0S. Source SHA-256: a0839cc5b3712ceb0edd797c48947900ca80302e7155d2f617b79cc1cf8c83c6. Raw-description SHA-256: c88083442c9da73e054e8f973eb79d786a58176500443593384dc3d07d58d9de.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
