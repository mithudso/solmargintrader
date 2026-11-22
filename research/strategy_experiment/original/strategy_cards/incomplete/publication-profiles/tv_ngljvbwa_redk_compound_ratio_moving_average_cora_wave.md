---

id: tv_profile_ngljvbwa

name: "RedK Compound Ratio Moving Average (CoRa_Wave)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "CoRa Wave gives more recent observations geometrically increasing weights to create a responsive moving average. Its aim is to reduce the influence of the oldest observations while retaining a finite-window average that can be used for trend and swing tracking. An accelerator changes how aggressively weights favor recent prices, and optional smoothing moderates the response. The author proposes crossover use, including equal-length lines on open and close, but provides no full trading system. Low-lag language describes intent and examples rather than a measured guarantee."

registry_key: null

runner: null

evaluation: null

---

# RedK Compound Ratio Moving Average (CoRa_Wave)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

CoRa Wave gives more recent observations geometrically increasing weights to create a responsive moving average. Its aim is to reduce the influence of the oldest observations while retaining a finite-window average that can be used for trend and swing tracking. An accelerator changes how aggressively weights favor recent prices, and optional smoothing moderates the response. The author proposes crossover use, including equal-length lines on open and close, but provides no full trading system. Low-lag language describes intent and examples rather than a measured guarantee.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for a parameterized geometric-weight moving average using disclosed compound-ratio equations with caller-chosen endpoints/window. Actual endpoint defaults, accelerator and automatic/manual smoothing remain outside the usable scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independent unaccelerated, unsmoothed geometric-weight MA: choose positive start weight P, endpoint A and t weight steps. Compute r=(A/P)^(1/t)−1; index the oldest sample as j=0 and set w_j=P×(1+r)^j. Return sum(w_j×source_j)/sum(w_j) over the selected window. This is a normalized weighted average using the disclosed weight sequence, not a reconstruction of undocumented accelerator/smoothing defaults.
- Apply an accelerator to emphasize recent observations and optional automatic/manual smoothing.

## Outputs and intended use

- A price-tracking MA supports trend observation or caller-defined crossovers.

## Parameters and stated settings

- Default resolution is chart timeframe and source hlc3.
- Multiplier zero produces SMA; source says effects are strongest around 1–5 then diminish.
- Example comparison length is 20; actual length/smoothing defaults are absent.
- Narrow geometric-weight scope requires chosen window, positive endpoint weights P and A, with t the number of weight steps; the source gives no endpoint defaults. Disable added acceleration and smoothing for this scope.

## Failure modes and caveats

- Greater recent-price weighting increases sensitivity to noise.
- The prose’s contrast with EMA should not be read as proof of uniquely geometric weighting or universal lag reduction.

## Missing information and implementation boundary

- Start/end weight choices, exact accelerator/smoothing formulas, confirmation timing and entry/exit rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Weighted chart prices and smoothing are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Weight at time t         A = P(1 + r)^t
```

### E2: parameters

```text
multiplier of 0
```

### E3: parameters

```text
between 1 and 5
```

### E4: parameters

```text
same as chart" and hlc3
```

### E5: parameters

```text
same length (20)
```

### E6: mechanism, parameters, readiness

```text
Compound Weight ratio    r = (A/P)^1/t - 1
Weight at time t         A = P(1 + r)^t
                           = Start_val * (1 + r) ^ index
index in the above formula is 0 for the furthest point out
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ngljvbwa_redk_compound_ratio_moving_average_cora_wave](../tv_ngljvbwa_redk_compound_ratio_moving_average_cora_wave.md)

## Source

https://www.tradingview.com/script/NgLjvBWA-RedK-Compound-Ratio-Moving-Average-CoRa-Wave/

Publication ID: NgLjvBWA. Source SHA-256: 6f3d594bb5ca3e54385db040052be15c331203d6637c85ff5402bad854066317. Raw-description SHA-256: 23a5a699f4ecd51d59a636bc70b6ed0781862433c63e9c3eb8f55a523d9728fa.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
