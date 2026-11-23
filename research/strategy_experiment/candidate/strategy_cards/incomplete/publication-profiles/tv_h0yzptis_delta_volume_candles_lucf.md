---

id: tv_profile_h0yzptis

name: "Delta Volume Candles [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Delta Volume Candles augments or replaces price candles with intrabar-derived volume-pressure information. It separates up/down intrabar volume, constructs several balance measures and uses them for candle additions, moving-average channels, divergence regions, colors and configurable alerts. The author presents delta as a proxy for participation convergence with price, explicitly warning against rigid reversal inference from declining delta."

registry_key: null

runner: null

evaluation: null

---

# Delta Volume Candles [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Delta Volume Candles augments or replaces price candles with intrabar-derived volume-pressure information. It separates up/down intrabar volume, constructs several balance measures and uses them for candle additions, moving-average channels, divergence regions, colors and configurable alerts. The author presents delta as a proxy for participation convergence with price, explicitly warning against rigid reversal inference from declining delta.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Historical raw/EMA directional-volume balances is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Assign intrabar volume by open/close direction, then prior-close direction for dojis, then carry last polarity; sum signed volume per chart bar.
- Build instant delta, EMA difference, RSI-centered momentum, ALMA-smoothed excess-volume and percentage balances, plus combined-state/marker summaries.
- Scale top/bottom candle extensions by delta share of volume relative to recent body size; save/expand divergence-channel levels until breached and renewed.
- Sign intrabar volume by close-open; flat body uses close-previous_intrabar_close then last polarity. Sum U,D;Bar Balance=U-D;Average Balance=EMA(U,n)-EMA(D,n),caller n/LTF. Initial polarity,auto-LTF,ALMA,markers/momentum excluded.

## Outputs and intended use

- Inspect balance/price agreement, divergence-channel breaks and top/bottom EMA references; configure markers/alerts for the selected balance conditions.
- Usable scope: Historical raw/EMA directional-volume balances. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Five balances are documented. Default top/bottom sizing uses average candle body over 100 bars; discrepancy background flags more than 1% intrabar/chart volume mismatch.
- Divergence-channel defaults use open/close levels and close breaches; balance/EMA periods and intrabar precision are configurable.

## Failure modes and caveats

- Intrabar resolution trades precision for history; delta remains a price-direction proxy. Realtime values update and historical feed/start changes can recalculate; source says markers/alerts appear at close.

## Missing information and implementation boundary

- Full period defaults, ALMA settings, marker rules, exact LTF mapping and momentum-sign wording require code confirmation.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV for intrabar attribution.

Repository input-class support: available. Historical OHLCV at the selected lower resolution supports the deterministic proxy; actual feed coverage/parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
five balances
```

### E2: parameters, readiness

```text
average candle body size of the last 100 bars.
```

### E3: parameters, readiness

```text
more than 1%.
```

### E4: mechanism, readiness

```text
last known polarity is used.
```

### E5: risks, readiness

```text
our volume delta calculations will remain a mere proxy.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
 • As a last resort, when there is no movement during an intrabar, and it closes at the same price as the previous intrabar, the last known polarity is used.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
 • Color an EMA channel.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_h0yzptis_delta_volume_candles_lucf](../tv_h0yzptis_delta_volume_candles_lucf.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/h0yZPTiS-Delta-Volume-Candles-LucF/

Publication ID: h0yZPTiS. Source SHA-256: 96ed493ae556d091d4350ef0fffd79143cadcfa1ed239a227d1c93979e091c91. Raw-description SHA-256: b6bfb07e1ddc80e6f1f9257f325c647a06e326dfed95f5d5325f3864f8b044cb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
