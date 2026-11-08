---

id: tv_profile_8zsalctc

name: "TrendFlex Oscillator - Dr. John Ehlers"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "TrendFlex Oscillator adapts Ehlers’s trend-retaining oscillator and exposes additional smoothing controls for experimentation. Its purpose is to respond to reversals while retaining the trend component, rather than serving solely as a detrended cycle display. The author emphasizes a compact output scale across sampling intervals and packages the calculation as a reusable function. Those behavioral statements are source claims without the underlying implementation here. Adjustable levels are provided as a foundation for users who want alerts, but the source does not define an actionable threshold crossing or a complete trading method."

registry_key: null

runner: null

evaluation: null

---

# TrendFlex Oscillator - Dr. John Ehlers

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

TrendFlex Oscillator adapts Ehlers’s trend-retaining oscillator and exposes additional smoothing controls for experimentation. Its purpose is to respond to reversals while retaining the trend component, rather than serving solely as a detrended cycle display. The author emphasizes a compact output scale across sampling intervals and packages the calculation as a reusable function. Those behavioral statements are source claims without the underlying implementation here. Adjustable levels are provided as a foundation for users who want alerts, but the source does not define an actionable threshold crossing or a complete trading method.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The TrendFlex normalization and filter/smoothing equations are not disclosed.

- The TrendFlex normalization and filter/smoothing equations are not disclosed.

## How it works

- Apply the TrendFlex calculation with a Super Smoother stage and an internal EMA.
- Allow an override for independent Super Smoother period and a Post Smooth adjustment to the internal EMA.

## Outputs and intended use

- A trend-sensitive oscillator and adjustable levels support discretionary trend/reversal observation.
- Reusable trendflex() function is intended for incorporation into other scripts.

## Parameters and stated settings

- The author describes a ±2.0 range across one-second to one-month candles.
- Super Smoother override/period, Post Smooth and adjustable levels are supplied; numerical defaults are absent.

## Failure modes and caveats

- Near-zero-lag and bounded-range descriptions are not verified guarantees.
- Extra smoothing controls can change responsiveness and encourage hindsight tuning.

## Missing information and implementation boundary

- Full TrendFlex/filter equations, normalization, defaults, alert predicates and entry/exit rules are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described chart oscillator/filter family is compatible with OHLCV prices; precise formula and scale behavior remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose

```text
reversal sensitive near zero-lag averaging indicator retaining the TREND component.
```

### E2: parameters, risks

```text
bound range between +/-2.0 on "1 second" candles all the way up to "1 month"
```

### E3: mechanism, parameters, readiness

```text
independent control for the Super Smoother.
```

### E4: parameters

```text
"Post Smooth" input()
```

### E5: outputs_and_use

```text
reusable function named trendflex().
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8zsalctc_trendflex_oscillator_dr_john_ehlers](../tv_8zsalctc_trendflex_oscillator_dr_john_ehlers.md)

## Source

https://www.tradingview.com/script/8ZSALctc-TrendFlex-Oscillator-Dr-John-Ehlers/

Publication ID: 8ZSALctc. Source SHA-256: 7930b45729c0edcb2922cade5a46879d69823d4f70f55defb762d7792fbc0cd6. Raw-description SHA-256: 3a1b70cf4eadfd16fee8b93fb9e119d2648ddb199a478be1dc05803f3b5af297.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
