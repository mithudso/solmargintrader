---

id: tv_profile_i4xznaoy

name: "STD-Filtered, N-Pole Gaussian Filter [Loxx]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "STD-Filtered N-Pole Gaussian Filter generalizes an Ehlers-style recursive smoother to selectable higher orders and adds a standard-deviation noise gate. It aims to suppress small fluctuations while retaining a smoother trend reference, with filtering optionally applied to price, the Gaussian output or both. The source warns that very high orders lose useful numerical precision despite leaving the input unbounded."

registry_key: null

runner: null

evaluation: null

---

# STD-Filtered, N-Pole Gaussian Filter [Loxx]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

STD-Filtered N-Pole Gaussian Filter generalizes an Ehlers-style recursive smoother to selectable higher orders and adds a standard-deviation noise gate. It aims to suppress small fluctuations while retaining a smoother trend reference, with filtering optionally applied to price, the Gaussian output or both. The source warns that very high orders lose useful numerical precision despite leaving the input unbounded.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Alpha from critical period, unambiguous generalized coefficients, deviation window/gate equation, initialization and signal conditions remain unspecified.

- Alpha from critical period, unambiguous generalized coefficients, deviation window/gate equation, initialization and signal conditions remain unspecified.

## How it works

- Apply a generalized multipole Gaussian recursive filter, then optionally standard-deviation-filter the source/output to reduce small changes.
- Use special stage initialization and provide signals, alerts and bar coloring, whose exact conditions are not described.

## Outputs and intended use

- Inspect the smoothed series and optional event/color outputs as context rather than a self-contained execution strategy.

## Parameters and stated settings

- Pole count defaults to 5; the author describes about 15 as a practical precision boundary. Noise filtering defaults to one standard deviation, with price/both/GMA/none modes.

## Failure modes and caveats

- High-order coefficients lose precision; analytical: stronger smoothing/gating can delay or suppress relevant moves, and lower-lag claims are conditional design comparisons.

## Missing information and implementation boundary

- Alpha from critical period, unambiguous generalized coefficients, deviation window/gate equation, initialization and signal conditions remain unspecified.

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
default is set to 5 poles
```

### E2: parameters, risks, readiness

```text
practical mathematical maximum is 15 poles
```

### E3: parameters, readiness

```text
by default it will filter 1 standard deviation.
```

### E4: parameters, readiness

```text
filter selections (price, both, GMA, none)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_i4xznaoy_std_filtered_n_pole_gaussian_filter_loxx](../tv_i4xznaoy_std_filtered_n_pole_gaussian_filter_loxx.md)

## Source

https://www.tradingview.com/script/i4xZNAoy-STD-Filtered-N-Pole-Gaussian-Filter-Loxx/

Publication ID: i4xZNAoy. Source SHA-256: f5b2dcd7784401792a537b07a55b7aecbc63e763920d249a89faab7ac642e736. Raw-description SHA-256: d18ff8da35c959d3d105678236b1ccad40e8ec227eae25ed59ff69456aa4625e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
