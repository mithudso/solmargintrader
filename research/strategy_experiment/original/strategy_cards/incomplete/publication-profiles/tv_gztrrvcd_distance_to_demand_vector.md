---

id: tv_profile_gztrrvcd

name: "Distance to Demand Vector"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Measure the separation between current market conditions and a demand reference derived from price range."

registry_key: null

runner: null

evaluation: null

---

# Distance to Demand Vector

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Measure the separation between current market conditions and a demand reference derived from price range.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The demand extraction, long/short classification, distance metric and actionable interpretation are missing.

- The demand extraction, long/short classification, distance metric and actionable interpretation are missing.

## How it works

- The author describes a relevant demand vector based on long/short demand extracted from price range, then displays distance to that vector. No vector or distance formula is given.

## Outputs and intended use

- Use the distance as an exploratory pressure or displacement diagnostic. The text gives no sign convention, scale or decision threshold.

## Parameters and stated settings

- No lookback, range definition or numerical default is disclosed.

## Failure modes and caveats

- Price-range-derived demand is an inferred proxy, not evidence of actual outstanding orders or investor demand.

## Missing information and implementation boundary

- The demand extraction, long/short classification, distance metric and actionable interpretation are missing.

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
demand vector is based on the demand for long/short, extracted from price range..
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gztrrvcd_distance_to_demand_vector](../tv_gztrrvcd_distance_to_demand_vector.md)

## Source

https://www.tradingview.com/script/gztrrvcD-Distance-to-Demand-Vector/

Publication ID: gztrrvcD. Source SHA-256: 6458be7f226b0293be6abeb90da7b66a63221ccaf96f66885cb37c097f76de45. Raw-description SHA-256: 50a4415e4c4e5bd0ee6a815a3b5f489f4c9e37f4c1240b3400ed79f8360a622c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
