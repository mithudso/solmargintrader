---

id: tv_profile_jncgedj7

name: "Order Chain [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Order Chain turns live chart-feed volume changes into price-level boxes and cumulative signed-volume readings. It aims to expose the sequence and relative size of recent activity rather than summarize only finished candles. The author calls the observations orders/ticks but acknowledges aggregation, so they should be understood as feed updates rather than individually verified exchange transactions. Its financial use is live order-flow-style observation; the source does not describe actual order placement or a deterministic trade strategy."

registry_key: null

runner: null

evaluation: null

---

# Order Chain [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Order Chain turns live chart-feed volume changes into price-level boxes and cumulative signed-volume readings. It aims to expose the sequence and relative size of recent activity rather than summarize only finished candles. The author calls the observations orders/ticks but acknowledges aggregation, so they should be understood as feed updates rather than individually verified exchange transactions. Its financial use is live order-flow-style observation; the source does not describe actual order placement or a deterministic trade strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for live update volume differences and changing-price per-tick-level signed CVD. Equal-price treatment, initialization/reset policy and unavailable historical live updates remain explicit limitations.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Subtract previous cumulative volume from current volume on each live update.
- For changing-price updates only, compare current price P_t with preceding update price P_(t−1). Treat ΔV=V_t−V_(t−1) as buy volume if P_t>P_(t−1), sell volume if P_t<P_(t−1); unchanged-price allocation is not disclosed.
- Append each classified update to its exact relevant tick-price level, adding ΔV for buys or subtracting ΔV for sells from the CVD held at that level. Initialization, reset and equal-price behavior remain outside this narrow changing-price-update specification.

## Outputs and intended use

- Scaled boxes show activity size; live delta/CVD and an order chain visualize recent price-level participation.

## Parameters and stated settings

- Chain spans up to 450 ticks/aggregates; other defaults are absent.
- Requires a live market with volume data.

## Failure modes and caveats

- Aggregated feed updates do not represent exact orders or aggressor classification.
- Historical OHLCV cannot reconstruct the sequence; refresh/persistence behavior is not described.

## Missing information and implementation boundary

- Unchanged-price sign rule, reset policy, box aggregation, CVD initialization and trade rules are missing.

## Data requirements

Required inputs: realtime price and cumulative-volume updates.

Repository input-class support: unavailable or unresolved. Requires update-level live data and intrabar persistence, unavailable from historical chart OHLCV alone.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
difference in volume from "now" and the previous tick.
```

### E2: parameters, risks

```text
up to 450 ticks (might include aggregates)
```

### E3: required_data

```text
must be used on a live market with volume data
```

### E4: mechanism

```text
added (buy order) or subtracted (sell order) from the CVD
```

### E5: mechanism, readiness

```text
Predicated on whether the "now" price is greater than or less than price one tick prior, the difference in volume is recorded as "buy" or "sell" volume.
```

### E6: mechanism, readiness

```text
appended to its relevant tick level and added (buy order) or subtracted (sell order) from the CVD value at the identified tick level.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jncgedj7_order_chain_kioseff_trading](../tv_jncgedj7_order_chain_kioseff_trading.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/JNCGeDj7-Order-Chain-Kioseff-Trading/

Publication ID: JNCGeDj7. Source SHA-256: d97d9c59803a53f2b8045d1e1a2f05d07b8c75569d7311b429ffbf540c59388f. Raw-description SHA-256: 57405f524715efc2d3a43400dad3cb9d9cd6c0abebe394eae0ecb74019be36ec.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
