---

id: tv_profile_zhfjqywg

name: "CVD Profiles [TradingIQ]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Map estimated cumulative directional participation into session price profiles and contrast it with activity, notional and imbalance views."

registry_key: null

runner: null

evaluation: null

---

# CVD Profiles [TradingIQ]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Map estimated cumulative directional participation into session price profiles and contrast it with activity, notional and imbalance views.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The model list describes intended outputs but does not specify core directional allocation or session/value-area contracts.

- Directional-volume/price-row allocation
- CVD/session resets and initial balance
- Ratio/value-area/notional formulas

## How it works

- Use lower-timeframe observations to distribute buy/sell estimates across price rows. Offer cumulative delta, buy/sell ratio, total activity or price-weighted volume, plus POC/value area, initial balance and a delta/change-of-delta histogram.

## Outputs and intended use

- Stack profiles to compare shifts in acceptance and directional concentration. The author explicitly calls the flow an approximation and notes strong delta can fail to move price or be absorbed.

## Parameters and stated settings

- Choose lower timeframe, tick-size resolution, value-area percent, fixed start/rolling sessions, profile mode, colors and delta/acceleration histogram. Numerical defaults and initial-balance duration are absent.

## Failure modes and caveats

- Price-times-volume is not necessarily USD notional unless instrument units/quote currency are handled correctly. Estimated directional activity is not actual trade aggression, and POC/value area depend on the chosen activity model.

## Missing information and implementation boundary

- Buy/sell classification, row allocation, CVD accumulation/reset, ratio denominator, value-area construction and notional conversion are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price/volume history supports the input class; missing equations are specification gaps rather than missing raw data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
it is an approximation of order flow
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
profile resolution (tick size)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
fixed start vs rolling sessions
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
CVD Delta = [i]current pressure
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
CVD Acceleration = [i]change in pressure
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_profile](../tv_method_market_profile.md)
- [tv_method_opening_range](../tv_method_opening_range.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_zhfjqywg_cvd_profiles_tradingiq](../tv_zhfjqywg_cvd_profiles_tradingiq.md)

## Source

https://www.tradingview.com/script/zHFJQYwG-CVD-Profiles-TradingIQ/

Publication ID: zHFJQYwG. Source SHA-256: fdb3ea8ba2f1342492bd0e4402632898add523c7523e4461f9036b1db57b804a. Raw-description SHA-256: 1e8a1ec482af96d4f1199c6986a4633ca76062a380aecf83a294995c5ae66eb5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
