---

id: tv_profile_in9ftv45

name: "Divergence for many indicator v3"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Divergence for Many Indicators compares the latest pivot with the developing current bar across several familiar technical measures. It aims to show potential momentum disagreement earlier than a prior higher-timeframe-completion approach. On finding a new divergence it draws a line and removes the previous one. The author’s no-latency claim therefore means ongoing evaluation, not that pivots are known instantly or that marks never change. Red/lime signals are possible reversal context, not demonstrated forecasts."

registry_key: null

runner: null

evaluation: null

---

# Divergence for many indicator v3

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Divergence for Many Indicators compares the latest pivot with the developing current bar across several familiar technical measures. It aims to show potential momentum disagreement earlier than a prior higher-timeframe-completion approach. On finding a new divergence it draws a line and removes the previous one. The author’s no-latency claim therefore means ongoing evaluation, not that pivots are known instantly or that marks never change. Red/lime signals are possible reversal context, not demonstrated forecasts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Pivot and divergence inequalities/confirmation rules are unspecified.

## How it works

- Detect pivot references and compare current price/indicator values with the latest pivot on each bar.
- Search enabled indicators for divergence and replace older lines when new matches appear.

## Outputs and intended use

- Red negative and lime positive divergence lines support discretionary reversal inspection.

## Parameters and stated settings

- Ten indicators: RSI,MACD,histogram,Stochastic,CCI,Momentum,OBV,Diosc,VWMACD,CMF; user selects enabled ones.

## Failure modes and caveats

- Current-bar comparisons and removed/replaced lines can repaint.
- Several correlated divergences do not independently confirm a reversal.

## Missing information and implementation boundary

- Pivot lengths/confirmation, regular/hidden criteria, indicator settings, line replacement order and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Named technical indicators and pivots use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
10 predefined indicators
```

### E2: mechanism, readiness

```text
between last Pivot point and current bar
```

### E3: mechanism, risks

```text
draws line and removes old one.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_in9ftv45_divergence_for_many_indicator_v3](../tv_in9ftv45_divergence_for_many_indicator_v3.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_method_rsi_divergence](../../../strategy_research/tv_method_rsi_divergence.md)

## Source

https://www.tradingview.com/script/iN9FTv45-Divergence-for-many-indicator-v3/

Publication ID: iN9FTv45. Source SHA-256: c14c1c638668700a471b1b3f258125c907143066265c28744e5251fcc8df8a03. Raw-description SHA-256: 30a5849909f2252cc70c5ba584d7607ed692f295732d649f51dd65c26d717bf0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
