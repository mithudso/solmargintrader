---

id: tv_profile_16zufzf4

name: "XeL OnlineRecursion"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Provide stateful streaming statistics and finance-oriented recursive weighting so importing scripts can compose adaptive market models efficiently."

registry_key: null

runner: null

evaluation: null

---

# XeL OnlineRecursion

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Provide stateful streaming statistics and finance-oriented recursive weighting so importing scripts can compose adaptive market models efficiently.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The architecture and statistical contracts are discussed, but exported computation equations/interfaces are absent from the overview.

- Per-estimator recurrences/signatures
- Initialization/reset/missing-data semantics
- Participation and tail-model equations

## How it works

- Retain statistical populations and update them observation by observation. Derive moments, covariance/regression, quantiles, robust location/scale, tail interpretations and participation/dispersion models from that retained state, distinguishing cumulative, rolling, exponential, anchored and event-clock meanings.

## Outputs and intended use

- Call exported state types/methods or functional interfaces. The NQ/open-interest example illustrates composition, not trading recommendations; missing relationships may return unavailable values and fallback remains the caller's responsibility.

## Parameters and stated settings

- Feedback alpha generally lies zero-to-one when used in that role. The publication corresponds to development1.0.0-rc.2 independently of TradingView import revision. Estimator-specific defaults are absent.

## Failure modes and caveats

- A recursive population is not interchangeable with a finite rolling window. Same-observation feedback can distort composed estimators unless callers use prior retained values where appropriate; tail-model suitability is not guaranteed.

## Missing information and implementation boundary

- Actual update equations, signatures, initialization/reset/NA policies per estimator, coefficient constructors and moment-to-Student-t mapping are not documented in this overview.

## Data requirements

Required inputs: caller numerical/financial observations, participation/open-interest data for dependent models.

Repository input-class support: unavailable or unresolved. Generic estimators accept caller series, but finance-oriented participation models may require external open interest or related data that is not supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
continuous numerical and financial data.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Most recursive components use constant retained memory and O(1) work per observation
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
alpha generally follows a [0,1] convention.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
previously retained value to avoid unintended same-observation feedback.
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
1.0.0-rc.2
```

## Source

https://www.tradingview.com/script/16ZuFZF4-XeL-OnlineRecursion/

Publication ID: 16ZuFZF4. Source SHA-256: 68fcc1d948ca54a44a7ff0cdfdf0e601d002390474ce5a7440d7158fca645def. Raw-description SHA-256: a837f96075678f3e38a03d85a357c84b737ccbb33424c104c7b43c23cb0da357.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
