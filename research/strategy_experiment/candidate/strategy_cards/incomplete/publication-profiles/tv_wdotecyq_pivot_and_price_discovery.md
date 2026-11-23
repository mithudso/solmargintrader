---

id: tv_profile_wdotecyq

name: "Pivot and Price Discovery"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Pivot and Price Discovery combines a sampled regression model with distribution moments and pivot-momentum annotations. It aims to estimate a short forward range and provide context for possible approaching pivots. The description suggests that skew/kurtosis inform interpretation but does not supply a calibrated pivot probability model, so projected deviations should be treated as model context rather than guaranteed bounds."

registry_key: null

runner: null

evaluation: null

---

# Pivot and Price Discovery

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Pivot and Price Discovery combines a sampled regression model with distribution moments and pivot-momentum annotations. It aims to estimate a short forward range and provide context for possible approaching pivots. The description suggests that skew/kurtosis inform interpretation but does not supply a calibrated pivot probability model, so projected deviations should be treated as model context rather than guaranteed bounds.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Sampling method, regression estimator, momentum threshold, triangle formula, deviation factor and default lookback are absent.

- Sampling method, regression estimator, momentum threshold, triangle formula, deviation factor and default lookback are absent.

## How it works

- Fit an unspecified population-sampled linear regression, summarize mean/variance/skew/kurtosis and draw momentum-continuation references for detected pivots.
- Extend a triangle from the latest index by selected standard-deviation distances over a short horizon.

## Outputs and intended use

- Red marks reducing pivots with momentum, gray continues that reference until an increasing momentum pivot cancels it; moves outside the triangle are proposed as possible pivot precursors.

## Parameters and stated settings

- Projection spans two periods. Author examined timeframes above five minutes and warns a one-hour window at ten-minute bars gives only six observations.

## Failure modes and caveats

- Analytical: small samples make moments unstable, extended sessions alter distributions and projected sigma distances do not establish event probabilities.

## Missing information and implementation boundary

- Sampling method, regression estimator, momentum threshold, triangle formula, deviation factor and default lookback are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
over 2 periods.
```

### E2: parameters, readiness

```text
greater than 5 minutes.
```

### E3: parameters, readiness

```text
1 hr at 10m timescale will be a lookback length of 6
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wdotecyq_pivot_and_price_discovery](../tv_wdotecyq_pivot_and_price_discovery.md)

## Source

https://www.tradingview.com/script/wDotecYq-Pivot-and-Price-Discovery/

Publication ID: wDotecYq. Source SHA-256: b122bbad43d26fe0296de35c5ef0396292af41e6973a8c11534330f88d73b607. Raw-description SHA-256: fb5505b709a62c4e27e9df430aeeb52e2baffe14cfb6c71713da4ac3b120fc90.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
