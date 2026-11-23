---

id: tv_profile_cojscaaa

name: "Multi Asset Similarity Matrix"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare multi-asset return-shape similarity through a configurable matrix of pairwise numerical measures."

registry_key: null

runner: null

evaluation: null

---

# Multi Asset Similarity Matrix

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare multi-asset return-shape similarity through a configurable matrix of pairwise numerical measures.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Volume-modified-return formula, metric parameters, normalization by measure direction, missing-data alignment and ticker defaults are not supplied.

- Volume-modified-return formula, metric parameters, normalization by measure direction, missing-data alignment and ticker defaults are not supplied.

## How it works

- Transform each selected asset into returns or volume-modified returns, retain a window of observations and calculate a selected distance/similarity measure for each pair. Normalize table color using the matrix's current minimum and maximum.

## Outputs and intended use

- Read red as relatively low and blue as relatively high similarity according to the chosen measure. Distances, cosine similarity and correlation are distinct quantities and do not all encode signed co-movement.

## Parameters and stated settings

- Provide comma-separated tickers, choose the source transformation and similarity method, and set window size, default ten. Methods include Euclidean, Manhattan, Minkowski, correlation, cosine, error measures and others.

## Failure modes and caveats

- Min/max color normalization changes with the selected universe. Price/volume scale, outliers and short samples can dominate distances; a similarity table does not prove a tradable relationship.

## Missing information and implementation boundary

- Volume-modified-return formula, metric parameters, normalization by measure direction, missing-data alignment and ticker defaults are not supplied.

## Data requirements

Required inputs: aligned return and volume histories for selected assets.

Repository input-class support: unavailable or unresolved. The selected universe and its aligned series are external requirements, not established by a single chart or the saved prose.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
source method (Returns or Volume Modified Returns)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
specified window size (default is 10)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
maximum and minimum values of the similarity matrix to normalize the color gradient.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cojscaaa_multi_asset_similarity_matrix](../tv_cojscaaa_multi_asset_similarity_matrix.md)

## Source

https://www.tradingview.com/script/cOjScAAA-Multi-Asset-Similarity-Matrix/

Publication ID: cOjScAAA. Source SHA-256: 1fcc637b3b5e3daca48e3294ccf8d135607fdac3ebc46c798cff8b41d0d39cbc. Raw-description SHA-256: 84e14ca6a61665b0a8e2bc7d13d7e48b214a8d17ae9a7a2a36b2ce11c00375aa.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
