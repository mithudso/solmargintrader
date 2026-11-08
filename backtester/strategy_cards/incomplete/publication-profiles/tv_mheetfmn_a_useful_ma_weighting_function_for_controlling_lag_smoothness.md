---

id: tv_profile_mheetfmn

name: "A Useful MA Weighting Function For Controlling Lag & Smoothness"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Offer explicit control over moving-average lag and smoothness through a beta-distribution-shaped weighting function."

registry_key: null

runner: null

evaluation: null

---

# A Useful MA Weighting Function For Controlling Lag & Smoothness

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Offer explicit control over moving-average lag and smoothness through a beta-distribution-shaped weighting function.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Discrete beta-weight construction, endpoint treatment, normalization, RSI length and default parameters are absent.

- Discrete beta-weight construction, endpoint treatment, normalization, RSI length and default parameters are absent.

## How it works

- Map the minus-lag control to beta and plus-lag to alpha. Adjust their relative values to skew weights toward newer/older observations, or equal values for symmetric weights. Color the output from RSI calculated on the average.

## Outputs and intended use

- Use the line to study smoothing/lag tradeoffs. Special parameter choices recover familiar SMA/WMA-like responses, allowing direct comparison rather than assuming one setting is universally better.

## Parameters and stated settings

- Length sets the window. Both shape controls equal one yield uniform SMA weights; minus-lag two and plus-lag one produce WMA. Equal symmetric controls imply lag (length-1)/2. The gradient has two hundred colors.

## Failure modes and caveats

- Reducing lag by emphasizing recent data generally changes noise response. Gradient RSI on a smoothed line is another derived measure, not independent confirmation.

## Missing information and implementation boundary

- Discrete beta-weight construction, endpoint treatment, normalization, RSI length and default parameters are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history; this establishes input class, not verified code, full history or profitability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
When [i]alpha = beta = 1[/i] the distribution is uniform
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
-Lag = 2[/i] and [i]+Lag = 1
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
its lag is equal to [i](length-1)/2
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the plot transition between 200 colors
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mheetfmn_a_useful_ma_weighting_function_for_controlling_lag_smoothness](../tv_mheetfmn_a_useful_ma_weighting_function_for_controlling_lag_smoothness.md)

## Source

https://www.tradingview.com/script/mheEtfmN-A-Useful-MA-Weighting-Function-For-Controlling-Lag-Smoothness/

Publication ID: mheEtfmN. Source SHA-256: dbbc08a42e52c9f50ba0aafb29c2ba0ac5ad170b99d2684bdb34223dbee3c62d. Raw-description SHA-256: ea9ca07ae08a357d6655a2486fab186a5756466f028567cdc7e5feeefbcb668a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
