---

id: tv_profile_ewwysggk

name: "Smooth Theil-Sen"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Smooth Theil-Sen replaces the discrete median of pairwise slopes with a Gaussian-weighted center of the sorted slope distribution. It aims to retain much of robust-regression behavior while making the displayed trend line less jumpy as the sample changes. This is a smoothing modification of the estimator rather than a claim that it exactly preserves the conventional median’s robustness."

registry_key: null

runner: null

evaluation: null

---

# Smooth Theil-Sen

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Smooth Theil-Sen replaces the discrete median of pairwise slopes with a Gaussian-weighted center of the sorted slope distribution. It aims to retain much of robust-regression behavior while making the displayed trend line less jumpy as the sample changes. This is a smoothing modification of the estimator rather than a claim that it exactly preserves the conventional median’s robustness.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Intercept estimator, kernel truncation/normalization, sample pairing/time coordinates, defaults and edge-case handling are missing.

- Intercept estimator, kernel truncation/normalization, sample pairing/time coordinates, defaults and edge-case handling are missing.

## How it works

- Compute slopes between all pairs in the lookback, sort them and apply Gaussian weights centered on the median position.
- Combine the resulting smoothed slope with an intercept calculation to plot regression values.

## Outputs and intended use

- Use the smoother line to inspect trend changes while balancing visual continuity against resistance to outliers.

## Parameters and stated settings

- Lookback and Gaussian-kernel standard deviation control sample size and smoothing; tight kernels approximate median steps, wider kernels smooth more. Numeric defaults are not provided.

## Failure modes and caveats

- The author acknowledges reduced outlier resistance and computation cost; analytical: Gaussian weighting over order statistics changes the estimator’s breakdown behavior.

## Missing information and implementation boundary

- Intercept estimator, kernel truncation/normalization, sample pairing/time coordinates, defaults and edge-case handling are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
median slope between all pairs of points
```

### E2: mechanism, readiness

```text
Gaussian kernel around the center of the sorted lists
```

### E3: missing_information, readiness

```text
combined with an intercept calculation
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ewwysggk_smooth_theil_sen](../tv_ewwysggk_smooth_theil_sen.md)

## Source

https://www.tradingview.com/script/ewWysgGk-Smooth-Theil-Sen/

Publication ID: ewWysgGk. Source SHA-256: 27d3d100d80669d4983ada396c42f1c9fe0aa78a022a31609ee3fbec1e78bf1a. Raw-description SHA-256: 070e3d59cc603f9b61c5516a4581562237597481c5b3f1edeb1df90f4efa6779.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
