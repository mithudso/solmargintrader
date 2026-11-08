---

id: tv_profile_nbptoyxr

name: "Asset Drift Model"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Asset Drift Model tests whether historical returns support a persistent directional bias rather than reacting to the latest price swing. It combines mean-return inference with economic-size, power, sign consistency, subsample stability and mean-reversion checks. The output distinguishes strong, weak or absent evidence, making no-evidence a failure to establish drift rather than proof of randomness. Its role is retrospective regime and portfolio research. Several prose claims overstate what small samples or absent drift establish; a zero mean does not imply random-walk behavior, and non-overlapping returns are not automatically independent."

registry_key: null

runner: null

evaluation: null

---

# Asset Drift Model

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Asset Drift Model tests whether historical returns support a persistent directional bias rather than reacting to the latest price swing. It combines mean-return inference with economic-size, power, sign consistency, subsample stability and mean-reversion checks. The output distinguishes strong, weak or absent evidence, making no-evidence a failure to establish drift rather than proof of randomness. Its role is retrospective regime and portfolio research. Several prose claims overstate what small samples or absent drift establish; a zero mean does not imply random-walk behavior, and non-overlapping returns are not automatically independent.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** HAC, minimum-detectable-effect, sign-test and variance-ratio equations are missing.

- HAC, minimum-detectable-effect, sign-test and variance-ratio equations are missing.

## How it works

- Form non-overlapping log returns and estimate mean drift with a simplified one-lag HAC standard error.
- Check sign-test evidence, mean/median agreement, half-sample consistency and variance-ratio mean reversion.
- Require significance, effect size, stated detectability and robustness for strong evidence; report rejection reasons otherwise.

## Outputs and intended use

- Dashboard shows directional/evidence class, sample status, t statistics, MDE/power, sign/stability/variance-ratio diagnostics and annualized drift.

## Parameters and stated settings

- Uses 60-day returns over 756 trading days, described as 12 full-sample and six half-sample observations.
- Absolute t threshold 2.0, economic threshold 3% annualized and sign-test annotation at 10%.
- Inference blocked below 10 observations, heuristic at 10–19 and allowed at 20+.

## Failure modes and caveats

- The default sample is explicitly in the heuristic range; asymptotic significance labels are uncertain.
- Comparing observed effect with an MDE is not a complete power analysis without a specified power target.
- Historical drift can change and does not establish net long/short edge.

## Missing information and implementation boundary

- Exact HAC/MDE/sign/variance-ratio formulas, annualization, stability thresholds, trading-calendar alignment and execution rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical price returns and their statistics derive from OHLCV; sufficient length and code parity remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
non-overlapping 60-day periods.
```

### E2: parameters

```text
756 trading days
```

### E3: parameters, risks

```text
12 independent observations
```

### E4: parameters

```text
6 observations per half-sample
```

### E5: parameters

```text
absolute t-statistic to exceed 2.0
```

### E6: parameters

```text
at least 3 percent annualized drift
```

### E7: parameters

```text
fewer than 10 observations
```

### E8: parameters

```text
10 to 19 observations
```

### E9: parameters

```text
20 or more observations
```

### E10: parameters

```text
significance at 10 percent.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_nbptoyxr_asset_drift_model](../tv_nbptoyxr_asset_drift_model.md)

## Source

https://www.tradingview.com/script/NBPTOyXr-Asset-Drift-Model/

Publication ID: NBPTOyXr. Source SHA-256: 0e612285a8ac047845a999a0271e1b2dcfe54cef23232db9082cf7faa2358543. Raw-description SHA-256: 999d7b41b14a45b8bab2bdbda706982ed0d53166852e9751392a3ae48be84242.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
