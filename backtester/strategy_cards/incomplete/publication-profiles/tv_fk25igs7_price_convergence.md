---

id: tv_profile_fk25igs7

name: "Price Convergence"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Price Convergence aims to assess potential price discovery by comparing the likelihood of upward price movement with the likelihood of downward movement. The entire source is a single conceptual sentence, so it establishes an analytical objective but provides no calculational recipe. It should remain a sparse, explicitly unresolved profile rather than acquire a probability model from its title."

registry_key: null

runner: null

evaluation: null

---

# Price Convergence

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Price Convergence aims to assess potential price discovery by comparing the likelihood of upward price movement with the likelihood of downward movement. The entire source is a single conceptual sentence, so it establishes an analytical objective but provides no calculational recipe. It should remain a sparse, explicitly unresolved profile rather than acquire a probability model from its title.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Neither upward nor downward probability estimator is disclosed.

- Neither upward nor downward probability estimator is disclosed.

## How it works

- Compare an estimated probability of price increase with an estimated probability of price decrease; neither estimator is described.

## Outputs and intended use

- The intended result is a likelihood assessment for price discovery, with no documented plotted format or decision threshold.

## Parameters and stated settings

- No parameters, estimation horizon, sample size or defaults are disclosed.

## Failure modes and caveats

- Analytical: unspecified probabilities cannot be assumed calibrated, complementary or predictive.

## Missing information and implementation boundary

- Probability estimation, the meaning of price discovery, input series, output scale and trading decisions are unknown.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, readiness

```text
Compares the probability of price increase to the probability of price decrease to predict the likelihood of price discovery.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fk25igs7_price_convergence](../tv_fk25igs7_price_convergence.md)

## Source

https://www.tradingview.com/script/FK25igs7-Price-Convergence/

Publication ID: FK25igs7. Source SHA-256: ab2ae884689914dbbfa83660ec4fb3817279773d862dd0f0d65fd5a641c97ade. Raw-description SHA-256: c13b53424defd1ac9206445e3145a378d18b21c6ed15c3d97418d27f90974417.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
