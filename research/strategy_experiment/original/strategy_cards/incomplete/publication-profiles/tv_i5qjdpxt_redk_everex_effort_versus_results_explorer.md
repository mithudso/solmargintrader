---

id: tv_profile_i5qjdpxt

name: "RedK EVEREX - Effort Versus Results Explorer"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare relative volume effort with relative price-movement result and aggregate their directional balance into a flow-strength oscillator."

registry_key: null

runner: null

evaluation: null

---

# RedK EVEREX - Effort Versus Results Explorer

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare relative volume effort with relative price-movement result and aggregate their directional balance into a flow-strength oscillator.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The author explicitly relies on an undisclosed custom normalization and flow formula, preventing reproducible computation.

- Normalize mapping and price-strength definition
- RROF equation and smoothing
- No-volume fallback and state triggers

## How it works

- Normalize per-bar volume and price strength against a selected lookback with a custom Normalize function. Draw stacked bands, then combine normalized effort/result into a Relative Rate of Flow index with optional smoothing, signal and longer bias view.

## Outputs and intended use

- Compression appears as strong volume with weak price response, ease of movement as the opposite. RROF crossings/alerts identify bullish/bearish strength changes; the author says it measures strength rather than price level or momentum.

## Parameters and stated settings

- Band scale defaults100 with each component up to50; alternatives200/400 change display zoom. RROF spans±100. Average type, lookbacks, smoothing, single/dual periods and timeframe are configurable, with no numerical defaults.

## Failure modes and caveats

- The custom normalization can materially alter ratios around extreme volume. No-volume instruments use price alone, which changes interpretation; selected TSLA examples are not independent validation.

## Missing information and implementation boundary

- Price-strength components, normalization mapping, flow-combination equation, smoothing and exact state/alert criteria are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed features use OHLCV; missing custom calculations are specification gaps, not missing raw market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
scale of the band is initially set to 100 (each band can occupy up to 50)
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
changed in the settings to 200 or 400
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
+100/-100 oscilator
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
proprietary "Normalize" function
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
in instruments with no volume data, only price data will be used.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_i5qjdpxt_redk_everex_effort_versus_results_explorer](../tv_i5qjdpxt_redk_everex_effort_versus_results_explorer.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_spread_analysis](../tv_method_volume_spread_analysis.md)
- [tv_method_wyckoff](../tv_method_wyckoff.md)

## Source

https://www.tradingview.com/script/I5qJDPxT-RedK-EVEREX-Effort-Versus-Results-Explorer/

Publication ID: I5qJDPxT. Source SHA-256: d8f52ca1bd8e690b3512fd34b89dae200adb14b6352b18f645a233dba1591ad8. Raw-description SHA-256: 3b4aaf8c9007397bbbd332b54b0f48c2d91275a066c1a2d3b41e393227b7b1f9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
