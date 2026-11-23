---

id: tv_profile_5kgra3dl

name: "Dynamic Volume Clusters with Retest Signals (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Identify frequently revisited price regions and mark later boundary retests, combining adaptive levels with a volume-oriented visual emphasis."

registry_key: null

runner: null

evaluation: null

---

# Dynamic Volume Clusters with Retest Signals (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Identify frequently revisited price regions and mark later boundary retests, combining adaptive levels with a volume-oriented visual emphasis.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The main clustering, smoothing and retest equations are opaque; settings alone do not define reproducible output.

- VPMA/Kalman equations and defaults
- Cluster touch/density/zone calculation
- Retest crossing/reversal state machine

## How it works

- Derive a lookback high/low range, construct adaptive clusters with a VPMA and Kalman smoothing, assess touch density and flag boundary crossings followed by reversal within a permitted retest window.

## Outputs and intended use

- Bright lines and blue candles indicate dense historical clustering; faded levels and red/green candles indicate lower-memory directional territory. Triangles mark potential continuation or reversal retests.

## Parameters and stated settings

- Range lookback, zone width percentage, retest display/minimum/maximum bars, cluster period, confirmation and start/peak touch requirements are inputs. Numerical defaults and volume equations are absent.

## Failure modes and caveats

- Frequent price visits do not prove resting orders or guarantee barriers. Adaptive smoothing may relocate levels, and the same retest can support opposing discretionary interpretations.

## Missing information and implementation boundary

- VPMA, Kalman state/noise parameters, density/touch test, level placement, brightness normalization and reversal confirmation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the stated input class; missing equations are specification gaps and do not mean missing raw OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Uses a dynamic moving average (VPMA) to maintain adaptive cluster levels.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Integrates a Kalman Filter
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
price crosses a cluster boundary and then reverses.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Price Cluster Start/Peak
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5kgra3dl_dynamic_volume_clusters_with_retest_signals_zeiierman](../tv_5kgra3dl_dynamic_volume_clusters_with_retest_signals_zeiierman.md)
- [tv_method_kalman_filter](../tv_method_kalman_filter.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/5kgRA3dl-Dynamic-Volume-Clusters-with-Retest-Signals-Zeiierman/

Publication ID: 5kgRA3dl. Source SHA-256: 49c0952743112ebbb0f0b8c71103903552376ba83fefcfa7bf6a50fd090bc5f5. Raw-description SHA-256: 9057cec96585e5831453d6ac460a048bbab5116cf0c505c09b5a3459bea3b539.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
