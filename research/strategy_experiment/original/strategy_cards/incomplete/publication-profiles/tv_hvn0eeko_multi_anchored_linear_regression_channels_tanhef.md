---

id: tv_profile_hvn0eeko

name: "Multi-Anchored Linear Regression Channels [TANHEF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Multi-Anchored Linear Regression Channels chooses lookback windows from price, indicator, time, event or statistical anchors, then fits selectable regression/deviation models. It aims to make channels adaptable to different research questions rather than assume one fixed least-squares window. Users can combine channel-position and correlation conditions for marks/alerts. The description explains model families but omits their implementation details, particularly regularization and weighted robust fitting. Event-based anchors also require external release/corporate-action data. This is a configurable analytical engine, not one fully defined strategy."

registry_key: null

runner: null

evaluation: null

---

# Multi-Anchored Linear Regression Channels [TANHEF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Multi-Anchored Linear Regression Channels chooses lookback windows from price, indicator, time, event or statistical anchors, then fits selectable regression/deviation models. It aims to make channels adaptable to different research questions rather than assume one fixed least-squares window. Users can combine channel-position and correlation conditions for marks/alerts. The description explains model families but omits their implementation details, particularly regularization and weighted robust fitting. Event-based anchors also require external release/corporate-action data. This is a configurable analytical engine, not one fully defined strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the fixed-length unweighted OLS center line/slope/endpoints on a chosen source. Full multi-model bands, bias and anchor searches remain outside this scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow fixed-length Standard/linear-scale fit with zero regression bias: for N chosen source observations y_j ordered oldest to newest at x_j=j, compute b=Σ((x−mean(x))(y−mean(y)))/Σ((x−mean(x))²), a=mean(y)−b mean(x), and endpoints a and a+b(N−1). This expands the source-named unweighted ordinary least squares procedure; no deviation bands or anchor-search algorithm is implied.
- Select dynamic/fixed anchor lengths within min/max/step constraints.
- Fit OLS or regularized/robust/Bayesian trend with optional recent/old-data bias.
- Construct selected residual/range/percentage bands and compare price position plus Pearson R with user criteria.

## Outputs and intended use

- Up to three channels/bands, parameter/statistics table and configurable signal marks/alerts support confluence research.

## Parameters and stated settings

- Seven regression families and eight deviation options described; positive/negative bias favors recent/older data.
- Position0/50/100 denotes lower/center/upper; R range±1. Example length100/bias+1 gives about7x newest weight.
- Step1 checks each candidate; event/session/time/external anchor choices configurable.
- Choose Fixed/Length anchor, Standard regression, linear scale, zero bias and N≥2 with sufficient nonmissing data. Source supplies no numeric N default; exclude regularized/robust/Bayesian methods, biased deviations and dynamic anchors.

## Failure modes and caveats

- Searching best correlation/slope windows can overfit.
- ATR-labeled residual measure is not conventional true-range ATR.
- Last-bar-only optimization differs from historical signal computation.

## Missing information and implementation boundary

- Regularization priors/penalties, IRLS iterations, exact bias weights, anchor searches, deviations and defaults are absent.

## Data requirements

Required inputs: ohlcv, earnings/dividends/splits for event anchors, external series when selected.

Repository input-class support: unavailable or unresolved. Price-only modes use OHLCV, but full selectable event/external data contract and chosen mode are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
up to three distinct regression channels
```

### E2: parameters

```text
length 100, bias +1 gives the newest price ~7×
```

### E3: parameters

```text
0% = lower deviation, 50% = regression, 100% = upper deviation
```

### E4: parameters

```text
R varies between –1 and +1
```

### E5: parameters

```text
Step size[/b] (1)
```

### E6: mechanism, readiness

```text
Huber loss with iteratively reweighted least squares
```

### E7: mechanism, parameters, readiness

```text
Uses ordinary least squares to compute a simple linear trend by averaging the data and deriving a slope and endpoints over the lookback period.
```

### E8: mechanism, parameters, readiness

```text
Maximum:[/b] The highest allowed regression length (also fixed value of “Length” anchor).
```

### E9: mechanism, parameters, readiness

```text
near-zero maintains balance.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hvn0eeko_multi_anchored_linear_regression_channels_tanhef](../tv_hvn0eeko_multi_anchored_linear_regression_channels_tanhef.md)
- [tv_method_linear_regression_channel](../tv_method_linear_regression_channel.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/hVn0eEko-Multi-Anchored-Linear-Regression-Channels-TANHEF/

Publication ID: hVn0eEko. Source SHA-256: dc3b72a1c7f4c000fb458bcc3daa831047aaa41e59dfccf2baacc09ce2baeb3d. Raw-description SHA-256: c1fda8f4b87ac8c11ca557f415b9febbeef2b9c192a2fe07a0e5b3c0e425f8ee.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
