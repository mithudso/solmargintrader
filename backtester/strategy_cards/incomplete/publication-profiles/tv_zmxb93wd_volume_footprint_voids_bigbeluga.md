---

id: tv_profile_zmxb93wd

name: "Volume Footprint Voids [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Footprint Voids builds a separate lower-timeframe profile within each chart candle, emphasizing concentrations and sparse areas. The author calls the largest block a time point of control and interprets black voids as potential imbalance-fill zones. The description alternates volume and close counts, so the output is best understood as a configurable intrabar-occupancy/profile view whose exact weighting remains unresolved."

registry_key: null

runner: null

evaluation: null

---

# Volume Footprint Voids [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Footprint Voids builds a separate lower-timeframe profile within each chart candle, emphasizing concentrations and sparse areas. The author calls the largest block a time point of control and interprets black voids as potential imbalance-fill zones. The description alternates volume and close counts, so the output is best understood as a configurable intrabar-occupancy/profile view whose exact weighting remains unresolved.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Price-level spacing, volume versus close-count weighting, average threshold, delta attribution and void definition are not fully specified.

- Price-level spacing, volume versus close-count weighting, average threshold, delta attribution and void definition are not fully specified.

## How it works

- Divide candle range into levels starting at the low, then inspect lower-timeframe closes within each level.
- Size blocks by the selected lot/count/volume interpretation and render modes emphasizing delta, total activity, PoC plus gaps or gaps alone.

## Outputs and intended use

- Inspect local support from concentrated lower activity and possible sparse-zone reactions; author claims about inevitable future fills are not adopted.

## Parameters and stated settings

- Lot size, lower timeframe, window/calculation mode, coloring and display settings are configurable without numeric defaults. Closer LTF choices are said to find more voids.

## Failure modes and caveats

- The source warns incorrect size inputs yield bad calculations and chart history cannot all be drawn; analytical: sparse observed closes do not prove an absence of traded volume.

## Missing information and implementation boundary

- Price-level spacing, volume versus close-count weighting, average threshold, delta attribution and void definition are not fully specified.

## Data requirements

Required inputs: lower-timeframe OHLCV within each chart candle.

Repository input-class support: available. OHLCV at the required intrabar resolution supports the data class; actual coverage and the ambiguous allocation algorithm remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
measure the amount of closes within the ranges.
```

### E2: outputs_and_use, readiness

```text
POC will be the largest block displayed, indicating the time point of control
```

### E3: mechanism, readiness

```text
Gray areas are closes above the average
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fair_value_gap](../../tv_method_fair_value_gap.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)
- [tv_zmxb93wd_volume_footprint_voids_bigbeluga](../tv_zmxb93wd_volume_footprint_voids_bigbeluga.md)

## Source

https://www.tradingview.com/script/ZMxB93wD-Volume-Footprint-Voids-BigBeluga/

Publication ID: ZMxB93wD. Source SHA-256: f356473d58d9af430c0704d0e3839d0e677251fb92881461dd2543322a7733b2. Raw-description SHA-256: b8332ec62442df6f53e6f3074573c1af2a28a850efe8984508671dedf369d6d0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
