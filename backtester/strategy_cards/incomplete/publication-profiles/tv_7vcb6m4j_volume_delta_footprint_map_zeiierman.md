---

id: tv_profile_7vcb6m4j

name: "Volume Delta Footprint Map (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume Delta Footprint Map estimates directional activity within chart candles and spreads that activity across price stripes. Its aim is to reveal where buying- or selling-associated volume concentrated and how those concentrations persist over time. A trader can inspect clusters for possible support, resistance, continuation or absorption, then interpret subsequent price behavior. The description carefully distinguishes this footprint-style approximation from exchange bid/ask transactions. Claims about trapped buyers or sellers are interpretive scenarios, not direct observations of positions or forced liquidation."

registry_key: null

runner: null

evaluation: null

---

# Volume Delta Footprint Map (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Delta Footprint Map estimates directional activity within chart candles and spreads that activity across price stripes. Its aim is to reveal where buying- or selling-associated volume concentrated and how those concentrations persist over time. A trader can inspect clusters for possible support, resistance, continuation or absorption, then interpret subsequent price behavior. The description carefully distinguishes this footprint-style approximation from exchange bid/ask transactions. Claims about trapped buyers or sellers are interpretive scenarios, not direct observations of positions or forced liquidation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Stripe-volume allocation, decay and dominance normalization equations are missing.

- Stripe-volume allocation, decay and dominance normalization equations are missing.

## How it works

- Sign lower-timeframe candle volume by candle direction and distribute delta across the traded price range.
- Carry stripe delta forward with exponential decay and rank strength using relative magnitude and directional dominance.
- Optionally remove stripe sections once price trades through them.

## Outputs and intended use

- Positive/negative stripes with varying intensity show concentration; untouched portions remain visible when touch gaps are enabled.
- Use clusters with observed rejection or continuation to frame discretionary hypotheses.

## Parameters and stated settings

- Strength combines relativeDelta at 0.70 with deltaDominance at 0.30.
- Automatic/manual lower timeframe, lookback, stripe count, persistence, minimum strength, intensity steps and touch gaps are configurable.

## Failure modes and caveats

- Candle-signed volume is not aggressor-side transaction data.
- Resolution, decay and binning change apparent concentrations; absorption cannot be established from this proxy alone.

## Missing information and implementation boundary

- Exact range allocation, doji rule, decay equation, normalization, automatic-timeframe mapping and defaults are absent.

## Data requirements

Required inputs: lower-timeframe ohlcv.

Repository input-class support: unavailable or unresolved. Requires intrabar OHLCV coverage beyond the chart candles; compatible lower-timeframe histories and depth are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
delta = direction × volume
```

### E2: mechanism, parameters

```text
strength = relativeDelta × 0.70 + deltaDominance × 0.30
```

### E3: mechanism

```text
Delta is carried forward using exponential decay
```

### E4: risks

```text
does not represent exchange-level bid and ask transactions.
```

### E5: mechanism, required_data

```text
Each lower-timeframe candle distributes its delta across the price levels it traded through
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_7vcb6m4j_volume_delta_footprint_map_zeiierman](../tv_7vcb6m4j_volume_delta_footprint_map_zeiierman.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/7vcb6M4J-Volume-Delta-Footprint-Map-Zeiierman/

Publication ID: 7vcb6M4J. Source SHA-256: 7191d179601fca30e29eb0525e6f40cb855785c5b0d7230629db0bc28c598724. Raw-description SHA-256: 4b22f04c3780458ac37dbf44142ca3193083493aa49c21e90a826b040f224b33.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
