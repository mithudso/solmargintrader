---

id: tv_profile_lpnsjmbh

name: "Clusters Volume Profile [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Clusters Volume Profile groups historical price bars by price proximity and gives each group its own volume distribution. This separates activity occurring at similar prices even when it was not adjacent in time. The author intends cluster points of control and boundaries to help identify price regimes, retests and possible support or resistance. Claims about institutional interest are interpretations of aggregated chart activity; the display does not identify the institutions trading there."

registry_key: null

runner: null

evaluation: null

---

# Clusters Volume Profile [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Clusters Volume Profile groups historical price bars by price proximity and gives each group its own volume distribution. This separates activity occurring at similar prices even when it was not adjacent in time. The author intends cluster points of control and boundaries to help identify price regimes, retests and possible support or resistance. Claims about institutional interest are interpretations of aggregated chart activity; the display does not identify the institutions trading there.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Blocking calculation or data contracts remain.

- Exact clustering initialization and volume-bin allocation are missing.

## How it works

- Initialize centroids across the lookback price range, assign bars to their nearest centroid using the source-labelled HLC2 median price, and update centers with assigned-bar volume-weighted prices.
- Repeat a selected iteration count, then render a profile and point of control for each group.

## Outputs and intended use

- Compare profile overlap and gaps for sideways versus separated price regimes.
- The author suggests POC retests as discretionary entries, cluster boundaries as possible stops and another cluster POC as a target.

## Parameters and stated settings

- Cluster count ranges from 2 to 10. Lookback, iterations, profile rows, maximum width, offset and dot appearance are configurable.

## Failure modes and caveats

- Cluster boundaries move as the lookback changes; volume concentration alone does not prove future support.

## Missing information and implementation boundary

- Centroid seed placement, empty-cluster handling and allocation of bar volume to profile bins are absent; HLC2 nomenclature is ambiguous.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the stated input class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, missing_information

```text
Iteratively assigning each price bar to the nearest centroid based on the HLC2 (median) price.
```

### E2: mechanism

```text
Recalculating centroids based on the volume-weighted average price of the assigned bars.
```

### E3: parameters

```text
Sets how many distinct price groups the algorithm should attempt to find (2 to 10).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lpnsjmbh_clusters_volume_profile_luxalgo](../tv_lpnsjmbh_clusters_volume_profile_luxalgo.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/lpnsjMbH-Clusters-Volume-Profile-LuxAlgo/

Publication ID: lpnsjMbH. Source SHA-256: a443b26f876b92d2de096ec676894316a9952b5a7f7256cb01ff7aad4b1e6d54. Raw-description SHA-256: 55e795f924aa3192c40f7947337945e5d4e0aa8628284999dab0d63dcc2acd8f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
