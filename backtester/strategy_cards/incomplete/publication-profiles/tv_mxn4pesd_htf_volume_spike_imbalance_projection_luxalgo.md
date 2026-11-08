---

id: tv_profile_mxn4pesd

name: "HTF Volume Spike & Imbalance Projection [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This projection tool examines lower-timeframe volume inside higher-timeframe candles and places the findings beside the working chart. A faded previous candle preserves completed context while the current block evolves live. Volume spikes, their price clusters and a per-candle profile aim to expose where unusual participation occurred, although bar-level volume cannot independently identify institutions or actual aggressive order flow."

registry_key: null

runner: null

evaluation: null

---

# HTF Volume Spike & Imbalance Projection [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This projection tool examines lower-timeframe volume inside higher-timeframe candles and places the findings beside the working chart. A faded previous candle preserves completed context while the current block evolves live. Volume spikes, their price clusters and a per-candle profile aim to expose where unusual participation occurred, although bar-level volume cannot independently identify institutions or actual aggressive order flow.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Previous/current HTF candle projection is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Request granular lower-timeframe data, flag volume exceeding its moving average by a configurable multiplier, and place bubbles at associated prices.
- Build higher-timeframe candle/profile blocks and identify repeated same-direction spikes at a price level as stacked imbalance.
- For supplied HTF OHLC, draw body between open/close and wick between low/high. Keep previous completed candle faded; update the current candle from developing OHLC. This direct projection excludes spike attribution and volume profile.

## Outputs and intended use

- Inspect ghost/current HTF candle, spike scatter and profile; source suggests watching returns to prior imbalance zones for possible reversals.
- Usable scope: Previous/current HTF candle projection. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Stacked imbalance requires three or more same-direction spikes at the same price level in one HTF candle.
- Inputs include HTF anchor/Auto, spike granularity, spike multiplier, volume-MA length and visibility toggles; no numeric defaults are supplied.

## Failure modes and caveats

- Analytical: current HTF values and spike clusters evolve before close; volume direction and price-level matching are proxies, not proof of institutional activity.

## Missing information and implementation boundary

- Spike direction attribution, same-price tolerance, profile allocation, auto-timeframe mapping and historical granular-data coverage are missing.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV within HTF candles.

Repository input-class support: available. Selected-resolution OHLCV supports this deterministic class; available intrabar depth and exact reconstruction remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
3 or more volume spikes of the same direction occur at the same price level within one HTF candle.
```

### E2: mechanism, readiness

```text
request.security_lower_tf()
```

### E3: mechanism, readiness

```text
volume exceeded a moving average by a user-defined multiplier.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
[list][*][b]Ghost Bar (Left Block):[/b] This represents the previous completed HTF candle. It is faded out to provide historical context and show where the previous "value" was established.[*][b]Current Bar (Right Block):[/b] This represents the HTF candle currently forming and updates in real-time as new data arrives.[/list]
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
The HTF Volume Spike & Imbalance Projection [LuxAlgo] indicator provides a comprehensive multi-timeframe analysis tool that projects higher timeframe (HTF) candle structures, volume spikes, and volume profiles directly onto the current chart. This script aims to bridge the gap between different time horizons, allowing traders to identify institutional interest, supply/demand zones, and significant order flow imbalances within an HTF context without ever switching timeframes.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mxn4pesd_htf_volume_spike_imbalance_projection_luxalgo](../tv_mxn4pesd_htf_volume_spike_imbalance_projection_luxalgo.md)

## Source

https://www.tradingview.com/script/MXn4pESD-HTF-Volume-Spike-Imbalance-Projection-LuxAlgo/

Publication ID: MXn4pESD. Source SHA-256: 6209cac44dbae53a55f1eb941107b0cf1a583116a70b59b33474eedc75af2011. Raw-description SHA-256: f3a217077cea19f91052ae86243fd10fee6d1ef8f791c805c592cfc95150f778.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
