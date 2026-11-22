---

id: tv_profile_juwuaxdx

name: "DeltaFlow Volume Profile [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "DeltaFlow Volume Profile adds a candle-direction decomposition to a recent-range volume profile. It aims to show both where volume clustered and whether candles assigned to each area leaned bullish or bearish. Its delta labels are derived from this candle-direction split, which is useful context but does not identify the aggressor of each trade or prove which participant dominated."

registry_key: null

runner: null

evaluation: null

---

# DeltaFlow Volume Profile [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

DeltaFlow Volume Profile adds a candle-direction decomposition to a recent-range volume profile. It aims to show both where volume clustered and whether candles assigned to each area leaned bullish or bearish. Its delta labels are derived from this candle-direction split, which is useful context but does not identify the aggressor of each trade or prove which participant dominated.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Allocation of bar volume across price bins is undisclosed.

- Allocation of bar volume across price bins is undisclosed.

## How it works

- Divide a lookback range into bins and aggregate volume, separating it by bullish/bearish candle direction.
- Normalize the component volumes into percentages and subtract bear percentage from bull percentage for bin delta.
- Shade bins by combined volume strength and delta bias; highlight the most significant bin with a PoC band and absolute-volume label.

## Outputs and intended use

- Inspect delta clusters near price, compare support/resistance context and use PoC as a risk-planning reference. The author proposes continuation and reversion ideas without complete execution rules.

## Parameters and stated settings

- Bins range from 10 to 100. LookBack, delta labels, heatmap, stacked volume bars, PoC and colors are configurable; no lookback default is stated.

## Failure modes and caveats

- Analytical: candle direction is an approximation of buying/selling pressure, and binning choices alter apparent imbalances.

## Missing information and implementation boundary

- Exact volume allocation across bins, treatment of dojis, PoC ties and trade-trigger definitions are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
volume is separated by candle direction
```

### E2: parameters, readiness

```text
Bins (10–100)
```

### E3: mechanism, readiness

```text
The difference between Bull % and Bear % for the bin.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_juwuaxdx_deltaflow_volume_profile_bigbeluga](../tv_juwuaxdx_deltaflow_volume_profile_bigbeluga.md)

## Source

https://www.tradingview.com/script/JUWuAXdx-DeltaFlow-Volume-Profile-BigBeluga/

Publication ID: JUWuAXdx. Source SHA-256: 44a5205e8193deedface1cc09fa595fcc217c9b0ac5b1dddf51e96ea02e42689. Raw-description SHA-256: 31da78fc437b038b780ac688d905ac0ff212093852c37568ad41283a12e90150.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
