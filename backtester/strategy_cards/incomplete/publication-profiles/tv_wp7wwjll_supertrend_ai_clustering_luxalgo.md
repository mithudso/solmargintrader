---

id: tv_profile_wp7wwjll

name: "SuperTrend AI (Clustering) [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "SuperTrend AI evaluates several SuperTrend factor settings with a smoothed directional-performance proxy, clusters their scores and uses the average factor from a selected performance group. It adapts a trailing reference according to recent fit rather than training a supervised forecast. The displayed score is not a win probability, and the author says it cannot predict every signal reliably."

registry_key: null

runner: null

evaluation: null

---

# SuperTrend AI (Clustering) [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

SuperTrend AI evaluates several SuperTrend factor settings with a smoothed directional-performance proxy, clusters their scores and uses the average factor from a selected performance group. It adapts a trailing reference according to recent fit rather than training a supervised forecast. The displayed score is not a win probability, and the author says it cannot predict every signal reliably.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** SuperTrend recursion, memory-to-alpha mapping, empty-cluster handling, stop-average adaptation and signal-label scaling are missing.

- SuperTrend recursion, memory-to-alpha mapping, empty-cluster handling, stop-average adaptation and signal-label scaling are missing.

## How it works

- For each factor, exponentially update signed close-change performance using the preceding SuperTrend state.
- Initialize three performance centroids from quartiles, run k-means and average factors in the chosen best/average/worst cluster.
- Calculate the final SuperTrend and an adaptive moving average of its trailing reference.

## Outputs and intended use

- Interpret the adaptive stop similarly to SuperTrend and use performance labels as relative context, not guaranteed follow-through.

## Parameters and stated settings

- ATR length, factor min/max/step, performance memory, cluster choice, maximum iterations and historical calculation window are configurable. Three clusters are used; numeric defaults are absent.

## Failure modes and caveats

- Analytical: repeated parameter selection can chase recent noise, cluster membership changes abruptly and low iteration limits can yield poor grouping.

## Missing information and implementation boundary

- SuperTrend recursion, memory-to-alpha mapping, empty-cluster handling, stop-average adaptation and signal-label scaling are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
assuming three groups of interest (K = 3)
```

### E2: mechanism, readiness

```text
P(t, factor) = P(t-1, factor) + α * (∆C(t) × S(t-1, factor) - P(t-1, factor))
```

### E3: mechanism, readiness

```text
average of the factors associated with the best-performing cluster
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_trailing_stop](../../tv_method_trailing_stop.md)
- [tv_wp7wwjll_supertrend_ai_clustering_luxalgo](../tv_wp7wwjll_supertrend_ai_clustering_luxalgo.md)

## Source

https://www.tradingview.com/script/wP7WWjLL-SuperTrend-AI-Clustering-LuxAlgo/

Publication ID: wP7WWjLL. Source SHA-256: 1f6e773e0ffadc8284edf5cfeb39a0fd736ecf08576f7109a876941b9a432f78. Raw-description SHA-256: 30536dc72739f2e06d8db4ff96d2793dab890047b97073c1e6e03f682ad7e0d8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
