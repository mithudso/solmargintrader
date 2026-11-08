---

id: tv_profile_cjx3k6l2

name: "Stop Loss Cascades (Breakouts) [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Estimate where hidden stop pressure might concentrate and contextualize possible breakout cascades. The indicator explicitly models unobservable stops rather than measuring actual stop locations, quantities or live order-book depth."

registry_key: null

runner: null

evaluation: null

---

# Stop Loss Cascades (Breakouts) [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate where hidden stop pressure might concentrate and contextualize possible breakout cascades. The indicator explicitly models unobservable stops rather than measuring actual stop locations, quantities or live order-book depth.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Swing eligibility/lifetime, ATR period/scaling, volume distribution weights, trigger/retirement conditions and historical move horizon are undisclosed.

- Swing eligibility/lifetime, ATR period/scaling, volume distribution weights, trigger/retirement conditions and historical move horizon are undisclosed.

## How it works

- The swing model assigns all classified buy volume to the closest active low and sell volume to the closest active high after formation, producing comparative potential-stop magnitudes. Direction derives from higher/lower close classification.
- The volatility-at-entry model distributes directional volume over multiple timeframe ATR distances. Triggered clusters receive size-classification graphics; nearby modeled buy/sell clusters populate a table.
- For typical-move context, log-transform current and historical cluster magnitudes and choose neighbors within a spacing-based tolerance or the closest match, then retrieve their associated historical moves. A ratio meter sums active and triggered buy/sell clusters.

## Outputs and intended use

- Cluster zones, trigger graphs, nearest-level data and directional ratios support situational awareness around breakout areas.
- Historical similar-size outcomes are explicitly descriptive, sometimes having very few neighbors; they are not forecasts or proof of latent positions.

## Parameters and stated settings

- Model choice and lower-timeframe granularity defaulting to one minute; finer seconds/ticks trade coverage for detail.
- Volatility distribution references1m,5m,15m,30m,1h,4h and ATR multiples1,1.5,2.

## Failure modes and caveats

- Assigning all volume to stops ignores exits, hedges, alternative stops and positions already closed. Exaggerated magnitudes are relative proxies.
- Resting liquidity can absorb triggered flow; modeled cluster size cannot guarantee breakout acceleration.

## Missing information and implementation boundary

- Swing eligibility/lifetime, ATR period/scaling, volume distribution weights, trigger/retirement conditions and historical move horizon are undisclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Lower-timeframe OHLCV supports the disclosed proxy model; it does not supply actual stop orders or aggressor flags.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
stop loss location & size data is not publicly available
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The model assigns [b]ALL[/b] classified volume to the swing level.
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
six common timeframes (1m, 5m, 15m, 30m, 1h, 4h) and 3 common ATR multiples
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
(1ATR, 1.5ATR, 2ATR)
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
This setting is set to 1-minute data by default
```

### E6: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
treat these measurements as a description of history rather than a prediction.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cjx3k6l2_stop_loss_cascades_breakouts_kioseff_trading](../tv_cjx3k6l2_stop_loss_cascades_breakouts_kioseff_trading.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_round_number_levels](../tv_method_round_number_levels.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/CJX3k6l2-Stop-Loss-Cascades-Breakouts-Kioseff-Trading/

Publication ID: CJX3k6l2. Source SHA-256: abab15bfadc98e37d712bd5953f2f85514c022f6f1293708cd443d1c459d40dd. Raw-description SHA-256: eee5ed5e803040a589835e04538e6c2786267e12739d29e04851c5749ae5b9f7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
