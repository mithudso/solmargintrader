---

id: tv_profile_cujanbts

name: "Kinetic Slippage Index (KSI)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Kinetic Slippage Index compares large price ranges with the amount of reported volume supporting them. The author interprets high readings as hollow movement and low readings as absorption, then suggests using extremes to inspect false breakouts, exhaustion or compression. These are hypotheses from bar-level range and volume; the indicator does not observe an actual order book, institutional identities or execution slippage."

registry_key: null

runner: null

evaluation: null

---

# Kinetic Slippage Index (KSI)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Kinetic Slippage Index compares large price ranges with the amount of reported volume supporting them. The author interprets high readings as hollow movement and low readings as absorption, then suggests using extremes to inspect false breakouts, exhaustion or compression. These are hypotheses from bar-level range and volume; the indicator does not observe an actual order book, institutional identities or execution slippage.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Range/volume denominator grouping and smoothing are ambiguous.

- Range/volume denominator grouping and smoothing are ambiguous.

## How it works

- Square True Range and divide using current volume and a longer-term volume EMA, according to the description; exact grouping is not provided.
- Compare the resulting oscillator with its own EMA signal and a spike threshold to color a histogram and mark extremes.

## Outputs and intended use

- A purple SPIKE prompts inspection for a reversal before fading a breakout. Extreme runs suggest tighter stops; compressed readings suggest waiting for a histogram/signal transition.

## Parameters and stated settings

- Defaults: ATR/Range Period 14, Volume EMA Period 20, Signal Line Period 9 and Spike Signal Level 50000.

## Failure modes and caveats

- Analytical: zero/poor volume can dominate the ratio, absolute thresholds may not transfer across instruments, and bar data cannot substantiate hidden institutional activity.
- A signal-line crossing indicates a change in this efficiency proxy, not necessarily the direction of price.

## Missing information and implementation boundary

- Exact denominator grouping, range smoothing, volume-unit normalization, zero-volume handling and direction confirmation are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
squaring the True Range and dividing it by the current Volume and its long-term EMA.
```

### E2: parameters, readiness

```text
ATR / Range Period (Default: 14)
```

### E3: parameters, readiness

```text
Volume EMA Period (Default: 20)
```

### E4: parameters, readiness

```text
Signal Line Period (Default: 9)
```

### E5: parameters, readiness

```text
Spike Signal Level (Default: 50000)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cujanbts_kinetic_slippage_index_ksi](../tv_cujanbts_kinetic_slippage_index_ksi.md)
- [tv_method_liquidity_sweep](../../../strategy_research/tv_method_liquidity_sweep.md)
- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/CUjAnbtS-Kinetic-Slippage-Index-KSI/

Publication ID: CUjAnbtS. Source SHA-256: 37ced88ade80ffee11d7edfd2907016da743b263933210b57782629c60fadf1c. Raw-description SHA-256: eb350fde5ef6d16987d2ea2aa58048f1bcf2b0476ae18ae8a0591580ca51d2d6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
