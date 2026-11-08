---

id: tv_profile_ekkb1vlg

name: "Voss Predictor (A Peek Into the Future) - Dr. John Ehlers"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Voss Predictor combines a bandpass-filtered cycle series with a predictive-filter transform and a correlation-based color companion. The intended use is anticipating cyclical turning points through phase response, not forecasting news or all price movements. The author warns that small or false turns can occur and that trending markets require special care, making the correlation layer a contextual filter rather than proof of reliable prediction."

registry_key: null

runner: null

evaluation: null

---

# Voss Predictor (A Peek Into the Future) - Dr. John Ehlers

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Voss Predictor combines a bandpass-filtered cycle series with a predictive-filter transform and a correlation-based color companion. The intended use is anticipating cyclical turning points through phase response, not forecasting news or all price movements. The author warns that small or false turns can occur and that trending markets require special care, making the correlation layer a contextual filter rather than proof of reliable prediction.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Filter recursions, predictor coefficients, correlation-color computation and executable signal rules require code or referenced material not reproduced here.

- Filter recursions, predictor coefficients, correlation-color computation and executable signal rules require code or referenced material not reproduced here.

## How it works

- Feed Ehlers’ two-pole bandpass output into the Voss predictor, then apply a Correlation Color companion to aid interpretation during trends.

## Outputs and intended use

- Inspect cyclic turn anticipation with trend context and other tools; the source explicitly says not to use the predictor alone.

## Parameters and stated settings

- Two-pole bandpass is specified; no bandpass period/bandwidth, prediction horizon, correlation window or defaults are disclosed.

## Failure modes and caveats

- Author warns of minute/false turns and limitations in trends; analytical: negative group delay is a filter property, not access to future information.

## Missing information and implementation boundary

- Filter recursions, predictor coefficients, correlation-color computation and executable signal rules require code or referenced material not reproduced here.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
Ehlers' 2-pole bandpass filter, fed into the Voss predictor, and my Correlation Color.
```

### E2: purpose, readiness

```text
anticipate cyclic turning points via negative group delay.
```

### E3: risks, readiness

```text
it can catch minute turning points or even false ones
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ekkb1vlg_voss_predictor_a_peek_into_the_future_dr_john_ehlers](../tv_ekkb1vlg_voss_predictor_a_peek_into_the_future_dr_john_ehlers.md)

## Source

https://www.tradingview.com/script/ekkb1vlg-Voss-Predictor-A-Peek-Into-the-Future-Dr-John-Ehlers/

Publication ID: ekkb1vlg. Source SHA-256: d700a87526fc116582fc188f0c56bba8547394c2b1d624d5ed9d4484a87c22ab. Raw-description SHA-256: bd58e815874d317b8384e5d86ede9e0c9f5e8cf50b6dbe10640dba34df8a63a3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
