---

id: tv_profile_4lbygqj0

name: "Weighted percentile nearest rank"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Calculate a weighted nearest-rank percentile so a numerical sample can contribute unequally to the resulting quantile."

registry_key: null

runner: null

evaluation: null

---

# Weighted percentile nearest rank

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

Calculate a weighted nearest-rank percentile so a numerical sample can contribute unequally to the resulting quantile.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source defines sorting paired values/weights and selecting the first cumulative weight reaching the percentile threshold. Edge validation remains a nonblocking interface caveat.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Sort observations while preserving their corresponding weights. Accumulate sorted weights and find the first cumulative weight at or above the requested percentage of total weight. Return the observation at that index.

## Outputs and intended use

- The result is an observed data value rather than an interpolated estimate. In chart work it could be a building block for distribution levels, but the publication does not prescribe a market signal.

## Parameters and stated settings

- Inputs comprise a data array, matching weights and requested percentile. The example uses data 22,33,11,44,55 and weights 5,3,2,1,4; its median threshold selects 33.

## Failure modes and caveats

- Nonpositive weights, unsorted ties and boundary percentiles need explicit handling before production reuse. The author's testing claim is not independently validated here.

## Missing information and implementation boundary

- Function signature, array mutation, empty input behavior and validation of weights/percentile bounds are absent from the prose.

## Data requirements

Required inputs: caller-supplied data and weight arrays.

Repository input-class support: available. This deterministic numerical function needs supplied arrays, not an external feed. The example establishes its input class; a caller must still choose meaningful market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
data      = 22, 33, 11, 44, 55
weights = 5  , 3  , 2  , 1  , 4
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
thres = weights_sum / 100 * n
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
5) take the iteration index that resulted "aye", and find the data value with the same index, that's gonna be the resulting percentile.
i = 2
data[i] = 33
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_4lbygqj0_weighted_percentile_nearest_rank](../tv_4lbygqj0_weighted_percentile_nearest_rank.md)

## Source

https://www.tradingview.com/script/4LByGQj0-Weighted-percentile-nearest-rank/

Publication ID: 4LByGQj0. Source SHA-256: d4cb2c06ac7e01e8c2b5c416d42d1b22fc737e0a9af6abb6fb994657cde68ff5. Raw-description SHA-256: b1b8e44a6de85a5b6e22cb79c80b86f58f22ea330b3dead0c5f692b0d8aa481d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
