---

id: tv_profile_u1l7ixmp

name: "Rolling Candle Profile with Buy/Sell Signals (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Show localized directional pressure between price and an adaptive reference line, then mark fresh agreement of profile, price position and anchor slope."

registry_key: null

runner: null

evaluation: null

---

# Rolling Candle Profile with Buy/Sell Signals (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Show localized directional pressure between price and an adaptive reference line, then mark fresh agreement of profile, price position and anchor slope.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The normalized ratio and defaults are supplied, but its buying/selling inputs and signal-state gates are not reproducible.

- Pressure component/recency/localization equations
- Colored-band cutoff
- Fresh alignment and hybrid blending

## How it works

- Divide the anchor-to-nearest-body-edge corridor into twelve bands. Aggregate sixty recent candles with recency emphasis; calculate normalized buy-minus-sell imbalance in each band using price, estimated volume delta or hybrid pressure.

## Outputs and intended use

- Green/red/transparent bands show buying/selling/weak pressure. Long labels require dominant green pressure, enough active bands, price above a rising anchor and fresh alignment; short labels reverse those conditions. The source explicitly denies true bid/ask delta.

## Parameters and stated settings

- Anchor choices are EMA/SMA/VWMA/VWAP/Donchian midpoint, length default twenty-one. Dominance defaults 0.25, active bands seven and same-direction signal spacing six bars. Localization, wick influence and intrabar resolution are configurable.

## Failure modes and caveats

- Pressure weights and selected color thresholds can change the signal materially. Candle-derived volume is a proxy and should not be represented as observed buyer/seller flow.

## Missing information and implementation boundary

- Price-pressure formula, recency weights, hybrid blend, active-band definition and fresh-alignment state machine are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculations use ordinary OHLCV; missing equations are specification gaps, not missing external market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
12 independent pressure bands.
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
most recent 60 candles
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
(Buying Pressure - Selling Pressure)
 / (Buying Pressure + Selling Pressure)
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Default: 21.
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Default: 0.25.
```

### E6: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Default: 7.
```

### E7: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Default: 6.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../tv_method_volume_delta.md)
- [tv_u1l7ixmp_rolling_candle_profile_with_buy_sell_signals_zeiierman](../tv_u1l7ixmp_rolling_candle_profile_with_buy_sell_signals_zeiierman.md)

## Source

https://www.tradingview.com/script/u1L7iXmp-Rolling-Candle-Profile-with-Buy-Sell-Signals-Zeiierman/

Publication ID: u1L7iXmp. Source SHA-256: 5120cbbf89b456c73abbfe8461b43a5a5970cac2b365cf29d7caa52acfeb0c9e. Raw-description SHA-256: b188149b41f1fbfa27b7d2755c62c677cea93bc2619f22be909d789b23559383.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
