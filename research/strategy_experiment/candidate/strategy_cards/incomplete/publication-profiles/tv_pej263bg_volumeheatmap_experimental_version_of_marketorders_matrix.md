---

id: tv_profile_pej263bg

name: "VolumeHeatmap | Experimental Version of Marketorders Matrix"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This experimental VolumeHeatmap publication aims to visualize where traded volume develops and to expose the price level carrying the greatest volume. The author frames that point of control as a reference for value trading and shows example chart links. The prose is a brief release note rather than an algorithm specification. Its mention of market orders does not establish access to actual aggressor-tagged exchange trades, and the heatmap should not be represented as an observed order book."

registry_key: null

runner: null

evaluation: null

---

# VolumeHeatmap | Experimental Version of Marketorders Matrix

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This experimental VolumeHeatmap publication aims to visualize where traded volume develops and to expose the price level carrying the greatest volume. The author frames that point of control as a reference for value trading and shows example chart links. The prose is a brief release note rather than an algorithm specification. Its mention of market orders does not establish access to actual aggressor-tagged exchange trades, and the heatmap should not be represented as an observed order book.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The volume input/granularity and price-allocation algorithm are undisclosed; no lower-timeframe requirement can be inferred from the title.

- Volume-source/granularity contract and volume-at-price allocation are unspecified.

## How it works

- Accumulate or otherwise estimate volume at price and display a heatmap; the allocation method is not described.
- Display a point of control and the evolution of the volume distribution.

## Outputs and intended use

- Inspect high-volume price areas as discretionary value references.
- The publication does not give entry, exit, alert or risk rules.

## Parameters and stated settings

- No numerical settings, defaults, bin counts or lookback lengths are disclosed.

## Failure modes and caveats

- The author explicitly acknowledges unresolved bugs.
- Without a disclosed feed and allocation definition, apparent volume concentration cannot be interpreted as exact market-order flow.

## Missing information and implementation boundary

- Volume source, price-bin allocation, reset window, color scale and POC selection/tie rules are missing.

## Data requirements

Required inputs: volume and associated price observations; source and granularity unspecified.

Repository input-class support: unavailable or unresolved. The source does not identify the volume feed or observation granularity. It could use chart-candle allocation or more detailed inputs; neither OHLCV sufficiency nor a required lower-timeframe/order-flow feed is established. Availability remains false because the input contract is unknown.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: risks

```text
some bugs I cannot solve today.
```

### E2: outputs_and_use

```text
It also possible to see the POC
```

### E3: purpose, required_data, readiness

```text
find the pricelevel with the most volume
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_pej263bg_volumeheatmap_experimental_version_of_marketorders_matrix](../tv_pej263bg_volumeheatmap_experimental_version_of_marketorders_matrix.md)

## Source

https://www.tradingview.com/script/peJ263bG-VolumeHeatmap-Experimental-Version-of-Marketorders-Matrix/

Publication ID: peJ263bG. Source SHA-256: 62990ec50659bbe323e6a95bbecfb3d004864d726b645e6a450d44ec553c3c2c. Raw-description SHA-256: d3932369191aa465d44dbce744a92872a35c75e3522e206be933ea7bb250eb76.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
