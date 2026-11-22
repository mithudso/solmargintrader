---

id: tv_profile_ppjps450

name: "Neglected Volume by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Neglected Volume combines relative-volume coloring with several price/volume diagnostics so traders can inspect whether movement is accompanied by unusual participation. It distinguishes long-baseline volume anomalies from short-baseline candle shading, then adds OBV momentum, optional acceleration, divergence, correlation and optional money flow. The source’s institutional-versus-retail narratives are interpretations rather than participant-identification measurements."

registry_key: null

runner: null

evaluation: null

---

# Neglected Volume by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Neglected Volume combines relative-volume coloring with several price/volume diagnostics so traders can inspect whether movement is accompanied by unusual participation. It distinguishes long-baseline volume anomalies from short-baseline candle shading, then adds OBV momentum, optional acceleration, divergence, correlation and optional money flow. The source’s institutional-versus-retail narratives are interpretations rather than participant-identification measurements.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Adapted OBV momentum normalization, smoothing and divergence rules are absent.

- Adapted OBV momentum normalization, smoothing and divergence rules are absent.

## How it works

- Compare volume with a long moving-average/standard-deviation baseline for relative-volume colors and with a shorter volume average for dark/light price-bar shading.
- Compute OBV momentum and optional acceleration with least-squares smoothing, use its momentum as a divergence oscillator and compare price/OBV correlation.
- Optionally display Chaikin Money Flow as a close-location-weighted volume companion.

## Outputs and intended use

- Use the coordinated displays to inspect confirmation, exhaustion or divergence alongside price; do not read volume alone as a complete strategy.

## Parameters and stated settings

- Relative-volume threshold defaults to a Fibonacci-golden-ratio standard-deviation offset without an explicit numeric value. Correlation guides are +0.5 and -0.5; lengths/defaults are not listed.

## Failure modes and caveats

- The author notes volume represents the reporting venue; analytical: volume spikes or divergences cannot establish institutions’ intent or guarantee leading signals.

## Missing information and implementation boundary

- Exact lengths, normalization of adapted indicators, divergence confirmation, smoothing defaults and execution rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
default value is set to Fibonacci golden ration standard deviation away from its moving average.
```

### E2: parameters, readiness

```text
values set to 0.5 and -0.5.
```

### E3: mechanism, readiness

```text
Momentum [/b]and Acceleration (optional) of OBV is calculated
```

### E4: risks, readiness

```text
numerical presentation may differ from their regular use
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_ppjps450_neglected_volume_by_dgt](../tv_ppjps450_neglected_volume_by_dgt.md)

## Source

https://www.tradingview.com/script/PpjPs450-Neglected-Volume-by-DGT/

Publication ID: PpjPs450. Source SHA-256: 218bf7ef1a346f46ccd0279d0156457c768badcb7580d1378797d1c853872c8f. Raw-description SHA-256: 81292c60840d5e3fb927ab2bb5364d36385d5d23e534ee9f6d261f36b7dff598.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
