---

id: tv_profile_ekbuz93v

name: "Delta Ladder [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Delta Ladder renders per-price volume differences as a ladder or colored blocks around each candle. Its purpose is to make localized directional-volume imbalance and point-of-control structure visible. A configurable assumption can fill the absent side when only buy or sell volume is recorded; the author calls that assumption arbitrary, so this is an inferred visualization rather than a guaranteed exchange footprint."

registry_key: null

runner: null

evaluation: null

---

# Delta Ladder [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Delta Ladder renders per-price volume differences as a ladder or colored blocks around each candle. Its purpose is to make localized directional-volume imbalance and point-of-control structure visible. A configurable assumption can fill the absent side when only buy or sell volume is recorded; the author calls that assumption arbitrary, so this is an inferred visualization rather than a guaranteed exchange footprint.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Underlying price-level volume construction and attribution are unspecified.

- Underlying price-level volume construction and attribution are unspecified.

## How it works

- Divide bars into price blocks and display volume delta in classic, on-bar or pure-ladder arrangements.
- Highlight PoC and shade relative delta differences; optionally merge blocks into a color-only canvas.
- Optional Volume Assumption replaces one-sided recorded levels with an assumed split.

## Outputs and intended use

- Inspect per-level imbalance, total candle delta and timestamps, with sell/buy blocks placed according to the chosen layout.

## Parameters and stated settings

- Bars can split up to 497 times. Volume Assumption uses an optional 60/40 split and can be disabled to record data as-is.

## Failure modes and caveats

- The 60/40 split is expressly arbitrary; analytical: inferred volume sides and block allocation can differ from actual aggressor-side order flow.

## Missing information and implementation boundary

- Underlying data resolution, attribution method, row construction, PoC calculation and zero-data handling are not specified; tick-based blocks are only planned.

## Data requirements

Required inputs: lower-resolution price/volume observations for per-level allocation.

Repository input-class support: unavailable or unresolved. The source does not establish the underlying granularity or buy/sell attribution; ordinary candle OHLCV cannot prove exact footprint reconstruction.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Price bars can be split up to 497 times
```

### E2: parameters, mechanism, readiness

```text
assumes a 60/ 40 split
```

### E3: risks, readiness

```text
this assumption was performed arbitrarily
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ekbuz93v_delta_ladder_kioseff_trading](../tv_ekbuz93v_delta_ladder_kioseff_trading.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/EkBUz93v-Delta-Ladder-Kioseff-Trading/

Publication ID: EkBUz93v. Source SHA-256: a07f6cf774f4841b9469976b37645837aeae4de0ba52f7100494320ae60422e8. Raw-description SHA-256: 4f7fb53d63587cb663d0e8a4c53d98cf2cd13ebb685b91ccc33e02813e63d131.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
