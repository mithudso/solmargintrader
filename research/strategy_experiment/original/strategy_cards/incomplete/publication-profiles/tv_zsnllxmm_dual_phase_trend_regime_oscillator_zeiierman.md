---

id: tv_profile_zsnllxmm

name: "Dual-Phase Trend Regime Oscillator (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Dual-Phase Trend Regime Oscillator selects a fast or slow price-time-correlation oscillator according to a volatility regime. It aims to preserve stability during calmer conditions and responsiveness when volatility rises. The active correlation-derived value is normalized for a shared midpoint interpretation, but switching between horizons can itself change the apparent trend state."

registry_key: null

runner: null

evaluation: null

---

# Dual-Phase Trend Regime Oscillator (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dual-Phase Trend Regime Oscillator selects a fast or slow price-time-correlation oscillator according to a volatility regime. It aims to preserve stability during calmer conditions and responsiveness when volatility rises. The active correlation-derived value is normalized for a shared midpoint interpretation, but switching between horizons can itself change the apparent trend state.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Median-cluster algorithm, volatility-history length, correlation normalization, refit timing and hysteresis are not specified.

- Median-cluster algorithm, volatility-history length, correlation normalization, refit timing and hysteresis are not specified.

## How it works

- Estimate standard deviation of price changes, smooth it and use median clustering over volatility history to classify low/high states.
- Choose slow correlation-based oscillator in low volatility or fast in high volatility, normalize and compare with midpoint.

## Outputs and intended use

- Read bullish/bearish/neutral regime colors and triangle changes; compare the fast line’s pullback with a steadier slow context.

## Parameters and stated settings

- Output spans 0–1 with neutral threshold 0.5. Inputs include both oscillator lengths, volatility refit interval, immediate volatility window and SMA smoothing; defaults are not listed.

## Failure modes and caveats

- Analytical: volatility clustering and horizon switching can whipsaw, and price-time correlation measures fitted direction rather than return predictability.

## Missing information and implementation boundary

- Median-cluster algorithm, volatility-history length, correlation normalization, refit timing and hysteresis are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
normalized between 0 and 1
```

### E2: parameters, readiness

```text
neutral threshold (0.5)
```

### E3: mechanism, readiness

```text
performs median clustering
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zsnllxmm_dual_phase_trend_regime_oscillator_zeiierman](../tv_zsnllxmm_dual_phase_trend_regime_oscillator_zeiierman.md)

## Source

https://www.tradingview.com/script/zSNlLXMM-Dual-Phase-Trend-Regime-Oscillator-Zeiierman/

Publication ID: zSNlLXMM. Source SHA-256: eb71587d05b1f708e7538dc8e2acff626dc919815b56f857539f66a6b25c1224. Raw-description SHA-256: 76c98ca5ff44b41fcdb8e5ac752517159a680994211096927bf943a7d2f6a4ae.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
