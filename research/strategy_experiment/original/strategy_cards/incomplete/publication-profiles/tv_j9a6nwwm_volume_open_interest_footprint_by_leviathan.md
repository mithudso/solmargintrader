---

id: tv_profile_j9a6nwwm

name: "Volume / Open Interest \"Footprint\" - By Leviathan"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This footprint-style display summarizes volume or open-interest behavior across the chart’s visible range into a single profile at the screen edge. Panning or zooming changes the sample, so it is a viewport-conditioned research view rather than a fixed historical signal. The author proposes positive-delta zones as possible support/resistance or target references, while retaining choices between total activity, opposing components and their difference."

registry_key: null

runner: null

evaluation: null

---

# Volume / Open Interest "Footprint" - By Leviathan

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This footprint-style display summarizes volume or open-interest behavior across the chart’s visible range into a single profile at the screen edge. Panning or zooming changes the sample, so it is a viewport-conditioned research view rather than a fixed historical signal. The author proposes positive-delta zones as possible support/resistance or target references, while retaining choices between total activity, opposing components and their difference.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Footprint row allocation and directional activity estimation are undisclosed.

- Footprint row allocation and directional activity estimation are undisclosed.

## How it works

- Aggregate selected volume or open-interest observations within the visible range into price rows.
- Render total, up/down or delta heatmap variants and optionally mark positive-delta rows as boxes.

## Outputs and intended use

- Inspect the right-side footprint and its positive-delta levels; moving the visible range automatically recalculates the display.

## Parameters and stated settings

- Resolution controls row count; Type selects Total, UP/DOWN or Delta. Volume can aggregate eight sources, with RQC selected when feeds report quote currency.

## Failure modes and caveats

- Analytical: changing the viewport changes the result, and buy/sell or OI opening-pressure interpretations depend on undisclosed attribution rules.
- The author warns to check base-versus-quote reporting before aggregation.

## Missing information and implementation boundary

- Row allocation, volume-side attribution, available OI feeds, normalization and source list are not disclosed.

## Data requirements

Required inputs: ohlcv, selected external volume feeds, open-interest history for OI mode, visible-range boundaries.

Repository input-class support: unavailable or unresolved. External volume aggregation and OI modes need selected feeds and their units; chart OHLCV alone does not supply all modes.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
within your chart's visible range.
```

### E2: parameters, readiness

```text
You can aggregate volume data from 8 different sources.
```

### E3: risks, readiness

```text
check if volume data is reported in base or quote currency
```

### E4: outputs_and_use, readiness

```text
These levels can serve as significant points of interest, S/R, targets
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_j9a6nwwm_volume_open_interest_footprint_by_leviathan](../tv_j9a6nwwm_volume_open_interest_footprint_by_leviathan.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/J9a6nWwM-Volume-Open-Interest-Footprint-By-Leviathan/

Publication ID: J9a6nWwM. Source SHA-256: d675010448612a111f731f8770430c4a66b8e2b52964963a02794d85c89b03c0. Raw-description SHA-256: 4501580fa152fc44355561225a06651065479819c5f323484b8a62c34354f6e6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
