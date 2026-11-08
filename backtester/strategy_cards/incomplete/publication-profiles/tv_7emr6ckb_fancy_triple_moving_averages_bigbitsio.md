---

id: tv_profile_7emr6ckb

name: "Fancy Triple Moving Averages [BigBitsIO]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Provide a configurable trio of moving averages with visual inclusion windows and hypothetical forward projections."

registry_key: null

runner: null

evaluation: null

---

# Fancy Triple Moving Averages [BigBitsIO]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Provide a configurable trio of moving averages with visual inclusion windows and hypothetical forward projections.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Supported average algorithms, forecast equations, magnitude units, higher-timeframe confirmation and numerical defaults are not supplied.

- Supported average algorithms, forecast equations, magnitude units, higher-timeframe confirmation and numerical defaults are not supplied.

## How it works

- Each average has its own type, period, source, timeframe and candle type. A highlight mode isolates candles participating in the calculation, while a ghost trail can preserve faded older history.

## Outputs and intended use

- Compare smoothing horizons and inspect which recent candles contribute. Forecast curves illustrate assumptions; neutral bias specifically holds the current price unchanged rather than predicting a future market price.

## Parameters and stated settings

- Visibility, inclusion highlight, ghost trail, forecast toggle, bias, period and magnitude are adjustable. No actual default lengths or forecast horizon is disclosed.

## Failure modes and caveats

- Projected averages depend on user assumptions and are not validated forecasts. Different candle types or timeframes can create inconsistent comparisons if their meaning is overlooked.

## Missing information and implementation boundary

- Supported average algorithms, forecast equations, magnitude units, higher-timeframe confirmation and numerical defaults are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the disclosed calculation class; this is not a verified implementation or historical-feed coverage claim.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
- Three moving averages (MA1, MA2, MA3).
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- Forecast bias. (Neutral forecasts MA if the current price remains the same.)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- Toggle to show a ghost trail when Highlight inclusion is toggled on.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_7emr6ckb_fancy_triple_moving_averages_bigbitsio](../tv_7emr6ckb_fancy_triple_moving_averages_bigbitsio.md)

## Source

https://www.tradingview.com/script/7emR6ckb-Fancy-Triple-Moving-Averages-BigBitsIO/

Publication ID: 7emR6ckb. Source SHA-256: 9e7dc1a76dce1f79082723d29daa44dd6d77d961c87e0b89be2426867c57c442. Raw-description SHA-256: 4cf7e8acb6537f4d3392af04c1bea624e2ade2c7a3eb3a9d24462d4da1edb32c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
