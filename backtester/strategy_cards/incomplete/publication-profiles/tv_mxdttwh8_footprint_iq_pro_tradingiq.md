---

id: tv_profile_mxdttwh8

name: "Footprint IQ Pro [TradingIQ]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Build candle-level footprint displays with volume/delta metrics, imbalance flags and selected historical price-level references."

registry_key: null

runner: null

evaluation: null

---

# Footprint IQ Pro [TradingIQ]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Build candle-level footprint displays with volume/delta metrics, imbalance flags and selected historical price-level references.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The output ratios are defined, but the core buy/sell/price-level allocation is not reproducible.

- Buy/sell volume classification and price bins
- Value-area algorithm
- CVD state/reset contract

## How it works

- Compute buy/sell volume and their difference at price areas, divide delta by total volume for delta ratio and flag sufficiently large signed ratios. Detect stacked adjacent imbalances, POC/value area and cumulative delta by level.

## Outputs and intended use

- Metric boxes show delta, ratio, total/buy/sell volume; optional labels explain symbols. Lines mark strong positive/negative delta regions and value area; alerts cover stacked imbalances.

## Parameters and stated settings

- Imbalance magnitude defaults seventy percent and stack count three. Value-area percentage and one-second-versus-coarser data are configurable; precise bin sizes are not disclosed.

## Failure modes and caveats

- The negative-imbalance paragraph also calls it buying, an apparent labeling contradiction. Finer sub-bars do not guarantee true trade-aggressor classification, and extreme delta levels need not remain support/resistance.

## Missing information and implementation boundary

- Tick/sub-bar buy-sell assignment, price allocation, ratio zero cases, stack direction, value-area expansion and CVD resets are missing.

## Data requirements

Required inputs: fine-grained price/volume observations, buy/sell classification rules.

Repository input-class support: unavailable or unresolved. The source does not establish the underlying classified event/volume data; ordinary OHLCV is insufficient for exact footprint parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Delta (Difference between buy and sell volume)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Delta Ratio (Delta as a percentage of total volume)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
set to 70% by default.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The default value is three.
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
negative net delta constitutes >=70% of the total volume, a buying imbalance
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../tv_method_volume_delta.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)
- [tv_mxdttwh8_footprint_iq_pro_tradingiq](../tv_mxdttwh8_footprint_iq_pro_tradingiq.md)

## Source

https://www.tradingview.com/script/mxDTtwh8-Footprint-IQ-Pro-TradingIQ/

Publication ID: mxDTtwh8. Source SHA-256: 291c7e29d566dc0f3c19f89e14faf13714a9137e50b17fd83154f877d6fc9f75. Raw-description SHA-256: 93dcce8b86fa0a2ef7a742c0d7c6d6829e9c4cdbe5a5f4aabfe5c1e4e480b38a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
