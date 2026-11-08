---

id: tv_profile_mketjg7e

name: "Periodic Linear Regressions [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Periodic Linear Regressions fits price from a period anchor to the current observation and optionally resets at each selected interval. It offers a refitted straight-line view or a causal sequence of fitted endpoints, plus residual-error envelopes. The distinction matters: the static line redraws the past fit as the sample grows, while rolling mode retains the endpoint observed on each bar."

registry_key: null

runner: null

evaluation: null

---

# Periodic Linear Regressions [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Periodic Linear Regressions fits price from a period anchor to the current observation and optionally resets at each selected interval. It offers a refitted straight-line view or a causal sequence of fitted endpoints, plus residual-error envelopes. The distinction matters: the static line redraws the past fit as the sample grows, while rolling mode retains the endpoint observed on each bar.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source defines anchor boundaries, regression endpoints and RMSE bands with caller-selected parameters.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Fit linear regression from the current periodic anchor or first available bar; static mode displays the latest full fit and rolling mode joins successive endpoints.
- Compute residual RMSE and scale it by Multiple for upper/lower extremities.

## Outputs and intended use

- Inspect anchored trend direction and possible channel reactions; colors follow slope in static mode or output change in rolling mode.

## Parameters and stated settings

- Static needs at least two observations; rolling display begins at the third. Controls include method, periodic/first-bar anchor, anchor interval, source, band Multiple and visuals; no numeric defaults are given.

## Failure modes and caveats

- Static mode is explicitly prone to repainting; analytical: growing-window fits and anchor selection change trend context, while residual bands are not guaranteed future coverage.

## Missing information and implementation boundary

- Exact period/session boundary treatment, numerical fit details, warmup handling and display defaults are not supplied but the core anchored computation is defined.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
root mean squared error (RMSE) between the price and calculated linear regression.
```

### E2: parameters, readiness

```text
linear regression needs at least two values
```

### E3: parameters, readiness

```text
from the 3rd bar
```

### E4: risks, readiness

```text
static method line is prone to repainting
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_mketjg7e_periodic_linear_regressions_luxalgo](../../../strategy_research/tv_mketjg7e_periodic_linear_regressions_luxalgo.md)

## Source

https://www.tradingview.com/script/mKEtjG7e-Periodic-Linear-Regressions-LuxAlgo/

Publication ID: mKEtjG7e. Source SHA-256: 3557d963bceab9388bf86bdc6ece34cd2128508973af5084db143f45cb1f2a63. Raw-description SHA-256: b80a8e8b7921e5453ae541df17837215e6c8830913783f18de80659ccb8236ef.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
