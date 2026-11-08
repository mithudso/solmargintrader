---

id: tv_profile_23wjedff

name: "Ehlers Loops [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Ehlers Loops puts filtered price and volume into a two-axis phase display so traders can inspect how movement and participation evolve together. Each symbol traces a tail through quadrants that the author associates with continuation or exhaustion. Histograms summarize the latest components beside the loop, making the display useful for comparing assets. Predictions suggested by loop curvature remain an interpretation of past data rather than an established forecasting result."

registry_key: null

runner: null

evaluation: null

---

# Ehlers Loops [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Ehlers Loops puts filtered price and volume into a two-axis phase display so traders can inspect how movement and participation evolve together. Each symbol traces a tail through quadrants that the author associates with continuation or exhaustion. Histograms summarize the latest components beside the loop, making the display useful for comparing assets. Predictions suggested by loop curvature remain an interpretation of past data rather than an established forecasting result.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Filter recursions and standard-deviation scaling window are absent.

- Filter recursions and standard-deviation scaling window are absent.

## How it works

- Filter price and volume separately through HighPass and SuperSmoother stages to form band-limited zero-mean signals and scale them in standard deviations.
- Plot the paired components through time with tails and quadrant references; show current price/volume histograms.

## Outputs and intended use

- Positive price/positive volume is interpreted as bullish continuation, negative price/positive volume as bearish continuation, and negative-volume quadrants as possible demand/supply exhaustion.

## Parameters and stated settings

- Up to five symbols can be selected. Low-pass period defaults to 10 and high-pass to 125; symbol size, colors, histograms and periods are adjustable.

## Failure modes and caveats

- Analytical: filtered-volume sign is relative to a transformed baseline, not literal negative traded volume; quadrant transitions need not predict reversals.

## Missing information and implementation boundary

- Exact filter coefficients, standard-deviation window, tail length and entry/exit confirmation are not supplied.

## Data requirements

Required inputs: OHLCV for up to five caller-selected symbols.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
HighPass and SuperSmoother filters
```

### E2: parameters, readiness

```text
up to five different symbols
```

### E3: parameters, readiness

```text
Low pass Period: default is 10
```

### E4: parameters, readiness

```text
High pass Period: default is 125
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_23wjedff_ehlers_loops_bigbeluga](../tv_23wjedff_ehlers_loops_bigbeluga.md)

## Source

https://www.tradingview.com/script/23wJeDFf-Ehlers-Loops-BigBeluga/

Publication ID: 23wJeDFf. Source SHA-256: b9ca88d166e6c26254930f668e3914222d40359e30c60c046fe645f779545415. Raw-description SHA-256: fa71f744f56f23ec77a866c3e2f450c746b83ba2758155a0842d863ca304cc08.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
