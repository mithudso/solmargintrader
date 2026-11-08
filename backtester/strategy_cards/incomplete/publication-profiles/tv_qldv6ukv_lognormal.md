---

id: tv_profile_qldv6ukv

name: "LogNormal"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Model positive skewed price distributions in log space and expose descriptive,probability,tail-risk and quantile-mapping utilities to financial scripts."

registry_key: null

runner: null

evaluation: null

---

# LogNormal

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Model positive skewed price distributions in log space and expose descriptive,probability,tail-risk and quantile-mapping utilities to financial scripts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The financial API is extensive but transformation,fit and risk-function equations are absent.

- Parameter conversion and quantile-fitting equations
- VaR/shortfall variable and sign convention
- Fisher/interval/precision algorithms

## How it works

- Initialize a LogNorm object from linear mean/dispersion,derive log-space parameters and modeled quantiles,then call Gaussian-backed density/CDF/inverse functions. Compare empirical quantile summaries with modeled quantiles to map values between distributions. Additional methods expose moments,information measures,Fisher information,intervals,VaR and expected-shortfall-like quantities.

## Outputs and intended use

- Return numerical model properties or transformed coordinates rather than trades. The financial motivation is lognormal price/risk modeling under a normal continuously compounded-return assumption; empirical fitting can adjust either model outputs or input coordinates.

## Parameters and stated settings

- Inputs include mean,standard deviation/variance,positive coordinates,confidence/probability,sample size,log base and precision flags. LogNorm/Quantile fields are interdependent and should be managed through init/set/quantiles. No financial lookback or probability default is disclosed.

## Failure modes and caveats

- A lognormal price assumption does not guarantee normal returns or correct financial tails. Density is not a probability,and model quantiles/shortfall depend on whether the modeled variable is price or loss. Differential entropy need not satisfy the nonnegative return range claimed in the prose.

## Missing information and implementation boundary

- Linear-to-log formulas,quantile interpolation/whiskers,fit mapping,tail/loss sign conventions,precision approximations and interval/Fisher equations are not supplied in this API overview.

## Data requirements

Required inputs: caller positive numerical/price sample or moments.

Repository input-class support: available. Caller price samples or moments are sufficient; no external feed is intrinsically required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, risks, readiness

```text
Prices are commonly modeled using log-normal distributions (ie. Black-Scholes)
```

### E2: purpose, mechanism, parameters, risks, readiness

```text
assuming [i]continuously compounding returns[/i] are normally distributed.
```

### E3: purpose, mechanism, parameters, risks, readiness

```text
avoid setting the LogNorm and Quantile fields directly
```

### E4: purpose, mechanism, parameters, risks, readiness

```text
density is not a probability
```

### E5: purpose, mechanism, parameters, risks, readiness

```text
Estimates the average loss [i]beyond[/i] a confidence level
```

### E6: purpose, mechanism, parameters, risks, readiness

```text
fit(x, a, b)
```

## Source

https://www.tradingview.com/script/qldv6Ukv-LogNormal/

Publication ID: qldv6Ukv. Source SHA-256: 1c2b45dd88812f63fa18e2ae272f3fde939021e2e3a5e8fab44231aa0165e6ed. Raw-description SHA-256: 4ad8419c423ca34f60f3a3b87c2da3682022294f6d0acc76dc4f228b205e9673.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
