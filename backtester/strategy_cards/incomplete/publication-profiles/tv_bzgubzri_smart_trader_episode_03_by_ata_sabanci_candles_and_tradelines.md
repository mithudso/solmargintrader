---

id: tv_profile_bzgubzri

name: "Smart Trader, Episode 03, by Ata Sabanci, Candles and Tradelines"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Describe market structure through aggregated candle blocks,volume-pressure estimates and a rule-generated narrative while keeping chart levels sparse."

registry_key: null

runner: null

evaluation: null

---

# Smart Trader, Episode 03, by Ata Sabanci, Candles and Tradelines

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Describe market structure through aggregated candle blocks,volume-pressure estimates and a rule-generated narrative while keeping chart levels sparse.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for supplied-block composite candles, nonzero-range geometric volume and maximum-buy-high/maximum-sell-low levels; intrabar, POC, quality and narrative remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- On caller-partitioned blocks, composite OHLC is first open, maximum high, minimum low and final close. For each nonzero-range bar R=H-L, geometric buy volume B=V*(C-L)/R and sell volume S=V*(H-C)/R; delta=B-S. Within each block, the maximum-B bar’s high is MAX BUY and maximum-S bar’s low is MAX SELL. Ties/zero ranges require caller conventions.
- Aggregate first open,maximum high,minimum low,last close by block. Estimate buy/sell via close-location fractions or intrabar data; compare block highs/lows for trend and average wicks/body changes for pressure. Identify POC and max-buy-bar high/max-sell-bar low,retire consumed levels and show nearest above/below.

## Outputs and intended use

- A dashboard holds detailed block/trend/quality metrics and an AI-style narrative assembled from deterministic conditions. It describes current conditions rather than predicting future prices or establishing an actual language-model engine.

## Parameters and stated settings

- Window/group count,live/closed basis,geometric/intrabar mode,range-angle threshold,projection,core levels and narrative language are configurable. Quality spans0-100 with80plus high,60-79medium. Intrabar choices include tick,second,15second andminute.

## Failure modes and caveats

- Geometric close-location splitting is a proxy and cannot support claims of observed aggression. Replay/live can differ; even intrabar data needs a classification rule. Claimed locked state/non-repainting requires code verification.

## Missing information and implementation boundary

- Trend segment anchoring,POC allocation,intrabar sign,zero-range split,quality weighting,candle-pattern thresholds and narrative conditions are missing.

## Data requirements

Required inputs: ohlcv, fine intrabar/tick observations for precise mode.

Repository input-class support: unavailable or unresolved. The geometric mode can use OHLCV,but the full precise-mode output needs unverified classified intrabar/tick data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Buy Volume = Total Volume × ((Close - Low) / Range)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Sell Volume = Total Volume × ((High - Close) / Range)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
HIGH quality (80+)
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
MEDIUM quality (60-79)
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The HIGH of this bar marks the level.
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The LOW of this bar marks the level.
```

### E7: mechanism, parameters, readiness

```text
Buy Volume = Total Volume × ((Close - Low) / Range)
```

### E8: mechanism, parameters, readiness

```text
Sell Volume = Total Volume × ((High - Close) / Range)
```

### E9: mechanism, parameters, readiness

```text
The bar with the highest buying volume. The HIGH of this bar marks the level.
```

### E10: mechanism, parameters, readiness

```text
The bar with the highest selling volume. The LOW of this bar marks the level.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bzgubzri_smart_trader_episode_03_by_ata_sabanci_candles_and_tradelines](../tv_bzgubzri_smart_trader_episode_03_by_ata_sabanci_candles_and_tradelines.md)
- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_doji](../../tv_method_doji.md)
- [tv_method_engulfing](../../tv_method_engulfing.md)
- [tv_method_hammer](../tv_method_hammer.md)
- [tv_method_inside_bar](../../tv_method_inside_bar.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/BZgubzrI-Smart-Trader-Episode-03-by-Ata-Sabanci-Candles-and-Tradelines/

Publication ID: BZgubzrI. Source SHA-256: 5dbff2331db01ddad8be6e5952debbad278a2e7a1ed34390280797a40dea845c. Raw-description SHA-256: 5f3c357f491ec94923d1bad4bb7156b83a2b07fb75adb389fbd8514b408bcc96.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
