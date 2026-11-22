---

id: tv_profile_8owcuqfq

name: "Multi-Distribution Volume Profile (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Test how alternative assumptions about intrabar volume location change a trend-independent price profile and its interpreted value regions."

registry_key: null

runner: null

evaluation: null

---

# Multi-Distribution Volume Profile (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Test how alternative assumptions about intrabar volume location change a trend-independent price profile and its interpreted value regions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for close/open point-allocation profiles and maximum-volume-row POC with caller lookback, level count and row-boundary/tie conventions; advanced distributions, center band and fade engines remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow Close/Open Only mode: over the caller-selected Bars Included lookback, find the total high–low span and divide it into the selected Price Levels. Assign each bar’s entire volume to the row containing its close or open, accumulate row totals and select the highest-volume row as POC. The caller must choose boundary-equality and tied-maximum conventions because the prose does not specify them.
- Divide lookback range into rows, distribute each candle's volume through selected uniform/body/wick/point/weighted or named statistical shapes and normalize weights to conserve volume. Select highest-volume POC and a central cumulative-volume band; optionally color by activity, recency, volatility, dwell/reversal density or inverse volume.

## Outputs and intended use

- Use profile variation as a sensitivity analysis of modeling assumptions, not discovery of actual tick distribution. Bull/bear row splits and fade metrics provide descriptive context for rotations, breakouts and possible low-activity regions.

## Parameters and stated settings

- Controls include build mode, bars, levels, side/offset, gradient metric, decay, thickness and center percentage. The text gives sixty-eight percent only as an example; distribution shape parameters/defaults are absent.

## Failure modes and caveats

- Different assumed kernels can create different apparent support/resistance from identical candles. Candle-derived directional profiles are not actual trade aggression, and low modeled volume is not proof of absent orders.

## Missing information and implementation boundary

- Named distribution parameterization, discrete overlap integration, central-band selection around POC, bull/bear classification and fade formulas are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV, including selected lower-timeframe history, supports the described data class. Missing computation details are separate specification gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
normalized so the total volume remains consistent
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Range Uniform – volume spread evenly across the full high–low range.
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
e.g., 68%
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Gaussian, Lognormal, Cauchy, Laplace
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Gamma, Beta, Chi-Square, Student-t, F-Shape
```

### E6: mechanism, parameters, readiness

```text
Midpoint / Close / Open Only – allocate volume entirely into one price row (pinpoint modeling).
```

### E7: mechanism, parameters, readiness

```text
The row with the highest total volume becomes the Point of Control (POC)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8owcuqfq_multi_distribution_volume_profile_zeiierman](../tv_8owcuqfq_multi_distribution_volume_profile_zeiierman.md)

## Source

https://www.tradingview.com/script/8owCUqFq-Multi-Distribution-Volume-Profile-Zeiierman/

Publication ID: 8owCUqFq. Source SHA-256: a3f77fde8469ea1b1b48e4d9c2dcb59f02674c91c994a0c58b0b62e4e0100cbb. Raw-description SHA-256: daa9acbb6db8ac04556cc3bd353435a287f15fa674d810c0230c6405579c95e4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
