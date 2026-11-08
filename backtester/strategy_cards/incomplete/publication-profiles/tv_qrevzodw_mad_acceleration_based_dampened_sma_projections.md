---

id: tv_profile_qrevzodw

name: "[MAD] Acceleration based dampened SMA projections"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This projection study extrapolates a smoothed input using its latest slope and average second difference, then draws a family of curves with different acceleration dampening factors. It also serves as an educational example of nested arrays and user-defined types. The curves are deterministic what-if paths for a moving-average-like series, not probability bands or independently validated forecasts."

registry_key: null

runner: null

evaluation: null

---

# [MAD] Acceleration based dampened SMA projections

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This projection study extrapolates a smoothed input using its latest slope and average second difference, then draws a family of curves with different acceleration dampening factors. It also serves as an educational example of nested arrays and user-defined types. The curves are deterministic what-if paths for a moving-average-like series, not probability bands or independently validated forecasts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Explicit slope, acceleration and quadratic dampened projection expressions define the principal scenario paths with caller-selected lengths/factors.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate a simple moving average baseline, first difference for slope and average second difference over an acceleration window.
- Create several quadratic paths from initial value, slope and dampened acceleration, storing each path’s points/color/factor in a structured array.
- Optionally delete prior polylines before drawing new projections; an offset can anchor an earlier observation.

## Outputs and intended use

- Compare the fan of differently curved scenarios and optionally retain old projections for inspection.

## Parameters and stated settings

- The code initializes nine curves. Inputs include SMA length, acceleration window, source, offset, initial/growth dampening, prediction length and history cleanup; no numeric defaults are listed.

## Failure modes and caveats

- Analytical: quadratic acceleration extrapolation can diverge quickly and the family has no calibrated probability interpretation. Prose calls SMA smoothed and simple inconsistently.

## Missing information and implementation boundary

- Exact source preprocessing, defaults, valid offsets and treatment of missing history are not fully specified.

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
array_size = 9
```

### E2: mechanism, readiness

```text
sma_slope = src_input - src_input[1]
```

### E3: mechanism, readiness

```text
initial_value + initial_slope * delta + 0.5 * damp_factor * acceleration * delta * delta
```

### E4: mechanism, readiness

```text
start_factor + (index - middle) * growth_factor
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qrevzodw_mad_acceleration_based_dampened_sma_projections](../tv_qrevzodw_mad_acceleration_based_dampened_sma_projections.md)

## Source

https://www.tradingview.com/script/QREVZoDw-MAD-Acceleration-based-dampened-SMA-projections/

Publication ID: QREVZoDw. Source SHA-256: d16d298e716c9851f7fe624c19e819a1912d03c64eb96cf72fe6779a2605a490. Raw-description SHA-256: 3c78da7a05cf459562913e64e71842259112e2d32bc6e439b3bc9a821a85638b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
