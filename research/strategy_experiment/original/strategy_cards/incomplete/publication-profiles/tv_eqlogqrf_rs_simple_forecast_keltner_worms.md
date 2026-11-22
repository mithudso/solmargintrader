---

id: tv_profile_eqlogqrf

name: "[RS]Simple Forecast - Keltner Worms"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Create an experimental projected price region by adapting Keltner channels and shifting their displayed segments."

registry_key: null

runner: null

evaluation: null

---

# [RS]Simple Forecast - Keltner Worms

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Create an experimental projected price region by adapting Keltner channels and shifting their displayed segments.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The multiplier objective, base average, range estimator, forecast horizon and real-time update behavior are absent.

- The multiplier objective, base average, range estimator, forecast horizon and real-time update behavior are absent.

## How it works

- The author combines automatically selected multipliers, offsets and show_last cutoffs to form a forecast area from Keltner channels. No optimization criterion or channel formula is supplied.

## Outputs and intended use

- Inspect the resulting projected area as an experimental visualization. Its forward placement is not evidence of predictive reliability.

## Parameters and stated settings

- The text names multiplier finding, offsets and display cutoffs without giving values, bounds or a selection method.

## Failure modes and caveats

- Automatically fitted envelopes can overfit recent history. A shifted historical channel can look prescient if its timing is misunderstood.

## Missing information and implementation boundary

- The multiplier objective, base average, range estimator, forecast horizon and real-time update behavior are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; this does not establish implementation parity or complete historical coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Using keltner channels with automatic multiplier finding, offsets and show_last cutoffs to generate a forecast area.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eqlogqrf_rs_simple_forecast_keltner_worms](../tv_eqlogqrf_rs_simple_forecast_keltner_worms.md)

## Source

https://www.tradingview.com/script/EQlOGqrF-RS-Simple-Forecast-Keltner-Worms/

Publication ID: EQlOGqrF. Source SHA-256: a82e4ffdb6ac296f633cd410a3d71199fbc05e33db97ea0c8a04cb70aa03e73d. Raw-description SHA-256: ce704647178ebb52a44b66e346207efeab878d4ba90c6ec5f3f731f8b53466af.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
