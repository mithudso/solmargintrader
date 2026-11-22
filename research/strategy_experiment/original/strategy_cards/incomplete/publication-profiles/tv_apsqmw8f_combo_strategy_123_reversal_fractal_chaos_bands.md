---

id: tv_profile_apsqmw8f

name: "Combo Strategy 123 Reversal & Fractal Chaos Bands"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Combine a reversal-style price/stochastic condition with fractal-band trend context to produce a cumulative color signal."

registry_key: null

runner: null

evaluation: null

---

# Combo Strategy 123 Reversal & Fractal Chaos Bands

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine a reversal-style price/stochastic condition with fractal-band trend context to produce a cumulative color signal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Signal combination, stochastic smoothing, fractal definition, bar-close timing, stops/exits and position sizing are missing.

- Signal combination, stochastic smoothing, fractal definition, bar-close timing, stops/exits and position sizing are missing.

## How it works

- The first component proposes buying after two days of higher closes while a nine-day slow stochastic is below fifty, and selling after two days of lower closes while a nine-day fast stochastic is above fifty. The second component uses high/low fractal bands and their slope to describe trend versus chop.

## Outputs and intended use

- The actual publication says it changes bar colors. Its strategy discussion does not establish that this saved study submits orders or that the two components' agreement rule is fully specified.

## Parameters and stated settings

- The disclosed stochastic horizon is nine days with midpoint fifty. Fractal lookback is selected by the trader; other defaults are omitted.

## Failure modes and caveats

- The slow-stochastic buy and fast-stochastic sell descriptions are asymmetric and must not be silently normalized. Fractal recognition may be delayed and combined signals may conflict.

## Missing information and implementation boundary

- Signal combination, stochastic smoothing, fractal definition, bar-close timing, stops/exits and position sizing are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature uses ordinary OHLCV, including lower-timeframe history where selected. This establishes data class only, not a verified implementation or cache.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
during 2 days and the meaning of 9-days Stochastic Slow Oscillator is lower than 50.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
during 2 days and the meaning of 9-days Stochastic Fast Oscillator is higher than 50.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- This script to change bars colors.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_apsqmw8f_combo_strategy_123_reversal_fractal_chaos_bands](../tv_apsqmw8f_combo_strategy_123_reversal_fractal_chaos_bands.md)

## Source

https://www.tradingview.com/script/ApsQmW8f-Combo-Strategy-123-Reversal-Fractal-Chaos-Bands/

Publication ID: ApsQmW8f. Source SHA-256: df243c10966135067d8c93e14f7bae32c146c41c12a007b07e53a83448bea7ad. Raw-description SHA-256: 2add72485f5bd7fa39d9a698d2ee97fa555a2eb9727bc5029484e96a96df68fa.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
