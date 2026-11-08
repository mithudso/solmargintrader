---

id: tv_profile_j38vuavw

name: "Intrabar Profile [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Intrabar Profile draws a mini volume or delta profile over each visible candle. It aims to expose where lower-timeframe participation concentrated, allowing price-body appearance to be compared with internal activity. PoC and value area summarize that distribution, while the source repeatedly calls delta an estimate from price movement rather than a predictive engine or direct aggressor-side record."

registry_key: null

runner: null

evaluation: null

---

# Intrabar Profile [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Intrabar Profile draws a mini volume or delta profile over each visible candle. It aims to expose where lower-timeframe participation concentrated, allowing price-body appearance to be compared with internal activity. PoC and value area summarize that distribution, while the source repeatedly calls delta an estimate from price movement rather than a predictive engine or direct aggressor-side record.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Volume-to-row allocation, directional attribution, value-area percentage/expansion, PoC ties and defaults are absent.

- Volume-to-row allocation, directional attribution, value-area percentage/expansion, PoC ties and defaults are absent.

## How it works

- Reconstruct per-candle price-row volume from lower-timeframe observations, select the highest-volume row as PoC and mark a total-volume-based value area.
- Switch to estimated directional delta using lower-timeframe price movement and volume; adapt profile drawing scale as the chart changes.

## Outputs and intended use

- Inspect concentration, imbalance, possible absorption and price/profile disagreement with optional labels; no automatic trade instruction is provided.

## Parameters and stated settings

- Granularity choices are five-minute, one-minute, one-second or one-tick. Row count, colors, transparency, PoC/value-area visibility and level labels are configurable without numeric defaults.

## Failure modes and caveats

- Accuracy depends on available granular data and account/feed access; analytical: inferred absorption or buyer dominance cannot identify actual participant intent.

## Missing information and implementation boundary

- Volume-to-row allocation, directional attribution, value-area percentage/expansion, PoC ties and defaults are absent.

## Data requirements

Required inputs: lower-timeframe or tick price/volume observations.

Repository input-class support: unavailable or unresolved. Some modes use ordinary lower-resolution OHLCV, but the full specified granularity includes tick observations; access and coverage are unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
5-minute
[*]1-minute
[*]1-second
[*]1-tick
```

### E2: mechanism, risks, readiness

```text
delta is estimated from lower timeframe price movement and volume
```

### E3: outputs_and_use, readiness

```text
not a predictive engine
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_j38vuavw_intrabar_profile_kioseff_trading](../tv_j38vuavw_intrabar_profile_kioseff_trading.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/j38vuAvW-Intrabar-Profile-Kioseff-Trading/

Publication ID: j38vuAvW. Source SHA-256: e69ad17246669a74ce40e79b3974646acd55b5ba91fc62efcb8507743934ffc8. Raw-description SHA-256: a39599be37c04c70fee128a6da8bbec94f994ec07e5e93887cb4baee8a9f242e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
