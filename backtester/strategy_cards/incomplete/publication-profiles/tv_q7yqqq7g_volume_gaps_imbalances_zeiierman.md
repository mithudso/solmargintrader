---

id: tv_profile_q7yqqq7g

name: "Volume Gaps & Imbalances (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Map sampled volume into price rows and show directional candle-volume imbalance by row and larger vertical sector."

registry_key: null

runner: null

evaluation: null

---

# Volume Gaps & Imbalances (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Map sampled volume into price rows and show directional candle-volume imbalance by row and larger vertical sector.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The principal profile allocation, direction split and delta ratio are explicit and parameterized; choose/document source and boundary conventions for a reproduction.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Divide a lookback high-low span into rows, assign each bar's volume using a selected source price and classify it bullish for close above open, bearish otherwise. Mark empty rows and calculate sector delta as bullish minus bearish volume divided by total volume.

## Outputs and intended use

- Inspect split bull/bear profiles, empty rows and a summary delta grid for structural context. Empty sampled buckets do not prove no exchange trade occurred at those prices, despite the author's true-void wording.

## Parameters and stated settings

- Lookback, rows, source, summary sections/width, panel spacing and delta-text display are user inputs; no numerical defaults are listed.

## Failure modes and caveats

- Assigning an entire candle's volume to one source bucket can create artificial holes. Candle direction is not actual aggressor flow, and gaps need not fill.

## Missing information and implementation boundary

- Exact bin-edge handling, selected-source definition/default and sector partition rounding are not given; the principal source-price bucket/directional-sum computation is nevertheless specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculations use ordinary OHLCV; missing equations are specification gaps, not missing external market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Bullish volume when close > open
[*]Bearish volume when close <= open
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Δ = (Bull Volume − Bear Volume) ÷ Total Volume × 100%
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Source –[/b] Price source used to assign volume into rows.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fair_value_gap](../../tv_method_fair_value_gap.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)
- [tv_q7yqqq7g_volume_gaps_imbalances_zeiierman](../tv_q7yqqq7g_volume_gaps_imbalances_zeiierman.md)

## Source

https://www.tradingview.com/script/Q7YQQq7g-Volume-Gaps-Imbalances-Zeiierman/

Publication ID: Q7YQQq7g. Source SHA-256: 4626bd571fe28210c556fe128b56918d999fb52a2b0b51dd66cc0c42f028b34c. Raw-description SHA-256: 5cb9d8a039b1b0745d6faa0ab6328d2f7b932583f3848a142436d9916f71a573.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
