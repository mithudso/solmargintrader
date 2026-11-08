---

id: tv_profile_fletgfxw

name: "[SS] Linear Modeler"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Linear Modeler extrapolates a regression-based price path and ranges at selected candle horizons, with historical reliability summaries. It aims to pair a target with a timeframe and an empirical-looking success reading instead of presenting an unqualified projection. The author suggests comparing targets with other range tools and interpreting price action before acting. The source’s reliability examples are illustrative chart claims, not reproduced measurements. Most importantly, the backtest event defining a target hit or range success is absent, so the percentages cannot be treated as calibrated probabilities."

registry_key: null

runner: null

evaluation: null

---

# [SS] Linear Modeler

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Linear Modeler extrapolates a regression-based price path and ranges at selected candle horizons, with historical reliability summaries. It aims to pair a target with a timeframe and an empirical-looking success reading instead of presenting an unqualified projection. The author suggests comparing targets with other range tools and interpreting price action before acting. The source’s reliability examples are illustrative chart claims, not reproduced measurements. Most importantly, the backtest event defining a target hit or range success is absent, so the percentages cannot be treated as calibrated probabilities.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core regression/range equations and reliability outcome definition are undisclosed.

## How it works

- Fit an unspecified linear time-series regression and project central targets/ranges to future bar horizons.
- Evaluate historical projections through an unspecified reliability/backtest procedure.

## Outputs and intended use

- Target/range table, projected lines and optional labels support scenario planning.

## Parameters and stated settings

- Forecast length, Display Chart and Plot Label are controls.
- Examples show ten/twenty/fifty-candle horizons; author prefers displayed historical readings90–100%, explicitly without guarantee.

## Failure modes and caveats

- Linear extrapolation can fail after regime changes.
- Historical hit rates depend on target tolerance, path and selection; those rules are absent.

## Missing information and implementation boundary

- Regression window/source, band formula, target-hit/backtest logic, sample size, defaults and uncertainty method are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price regression and historical evaluation use OHLCV as a data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
linear regression time series analysis.
```

### E2: parameters

```text
next 10 candles
```

### E3: parameters

```text
at 20 candles
```

### E4: parameters

```text
next 50 candles
```

### E5: parameters, risks

```text
90% to 100%
```

### E6: readiness

```text
back-test the range and variables
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fletgfxw_ss_linear_modeler](../tv_fletgfxw_ss_linear_modeler.md)
- [tv_method_linear_regression_channel](../tv_method_linear_regression_channel.md)

## Source

https://www.tradingview.com/script/fLeTgfxW-SS-Linear-Modeler/

Publication ID: fLeTgfxW. Source SHA-256: c490ba027bb7309cc3a4f5f10c80baa2f806cdc8e1eb30a7cd453da15b30d48c. Raw-description SHA-256: dad2ed9ffd291accb3a5af34a7a4029b106a112e6bab487f78ece72ba75995d3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
