---

id: tv_profile_c2fzxjii

name: "EVaR Indicator and Position Sizing"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Explore a Tsallis/q-exponential tail-risk proxy and use its normalized level to vary suggested exposure and stop references."

registry_key: null

runner: null

evaluation: null

---

# EVaR Indicator and Position Sizing

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Explore a Tsallis/q-exponential tail-risk proxy and use its normalized level to vary suggested exposure and stop references.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The displayed variational form does not specify the altered q-MGF, numerical optimization, normalization or sizing/stop rules.

- q-MGF/optimization definition
- Normalization and confidence interpretation
- Allocation/stop equations and account inputs

## How it works

- Estimate returns over a lookback, approximate a moment-generating function with q-exponentials, derive a confidence-dependent EVaR-like value, scale it into zero-to-one and reduce allocation as normalized risk rises.

## Outputs and intended use

- Show a risk curve and matrix of allocation, dollars, quantity, stop distance and projected stop loss. These are model suggestions, not verified protection against black swans or a guarantee of constant risk.

## Parameters and stated settings

- Lookback, q and confidence are configurable. Suggested q lies 1.5-2.0, with risk zones separated at 0.3,0.5 and 0.7. Numerical account-sizing defaults are not disclosed.

## Failure modes and caveats

- Substituting q-exponentials changes the usual entropic-risk formulation; the author's superiority and extreme-event-frequency claims are unvalidated. Rolling normalization can make a low reading coexist with large absolute risk.

## Missing information and implementation boundary

- Return/sign conventions, q-exponential domain, optimization bounds, normalization, equity/leverage inputs, sizing and stop equations are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculations use ordinary OHLCV; missing equations are specification gaps, not missing external market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
EVAR_α(X) = inf_{z>0} {z * log(1/α * M_X(1/z))}
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
q-parameter controls tail sensitivity—higher values (1.5-2.0)
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Reference lines at 0.3, 0.5, and 0.7
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Position Sizing: Inversely modulated based on normalized EVAR
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_c2fzxjii_evar_indicator_and_position_sizing](../tv_c2fzxjii_evar_indicator_and_position_sizing.md)
- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/c2fZXJII-EVaR-Indicator-and-Position-Sizing/

Publication ID: c2fZXJII. Source SHA-256: 67ab2df060446138a54262c13893019319ad6e9172dcfd51366fd49f25d1afbe. Raw-description SHA-256: 3a1267c1d88dab1f59e041ea291d67c0f3d79672feef8d8fc001d2e3167ace73.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
