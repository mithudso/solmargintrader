---

id: tv_profile_kfuhomlx

name: "RedK_Supply/Demand Volume Viewer v1"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Supply/Demand Volume Viewer estimates directional volume from candle shape without bid/ask data or intrabar drilling. It smooths inferred demand/supply components and their net difference to make participation balance easier to inspect. The author explicitly treats the result as a simple proxy and says it does not track trend, so its labels do not establish actual buyer/seller identities or accumulation."

registry_key: null

runner: null

evaluation: null

---

# RedK_Supply/Demand Volume Viewer v1

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Supply/Demand Volume Viewer estimates directional volume from candle shape without bid/ask data or intrabar drilling. It smooths inferred demand/supply components and their net difference to make participation balance easier to inspect. The author explicitly treats the result as a simple proxy and says it does not track trend, so its labels do not establish actual buyer/seller identities or accumulation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Exact double-wick scoring equation, zero-range handling, smoothing defaults and key-level extraction rules are missing.

- Exact double-wick scoring equation, zero-range handling, smoothing defaults and key-level extraction rules are missing.

## How it works

- Assign demand/supply proportions from body/wick geometry, with double weight on wick portions, then divide bar volume accordingly.
- WMA-smooth both components, subtract supply from demand and apply final smoothing to the net.

## Outputs and intended use

- Inspect simplified net display or detailed volume/component overlays; relate net extrema/zero crossings to price-level research alongside trend/momentum tools.

## Parameters and stated settings

- Full green/red bodies are described as 100% demand/supply and dojis 50/50. WMA lengths and final smoothing are configurable but no numeric defaults are supplied.

## Failure modes and caveats

- Analytical: candle-shape allocation is an inference, not observed order flow; price can decline while the proxy shows demand, and historical examples do not validate support levels.

## Missing information and implementation boundary

- Exact double-wick scoring equation, zero-range handling, smoothing defaults and key-level extraction rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
100% demand
```

### E2: parameters, readiness

```text
100% supply
```

### E3: parameters, readiness

```text
50/50 split
```

### E4: mechanism, readiness

```text
double weight for the "wick" parts
```

### E5: mechanism, readiness

```text
weighted moving average (WMA)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_kfuhomlx_redk_supply_demand_volume_viewer_v1](../tv_kfuhomlx_redk_supply_demand_volume_viewer_v1.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/kfUHOMlX-RedK-Supply-Demand-Volume-Viewer-v1/

Publication ID: kfUHOMlX. Source SHA-256: 1febe7e5bfca5e6656d9b63ff2e67c2f5713551e532e66afbf7a1991911e9ef1. Raw-description SHA-256: 64c17b244266a42279bf32953637f143528d267b982f3c8906171ca5c756748b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
