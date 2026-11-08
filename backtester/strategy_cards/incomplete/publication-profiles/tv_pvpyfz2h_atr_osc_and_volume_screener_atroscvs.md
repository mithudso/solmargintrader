---

id: tv_profile_pvpyfz2h

name: "ATR OSC and Volume Screener (ATROSCVS)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare volatility-normalized momentum and unusual volume across a cryptocurrency watchlist using a color-coded grid."

registry_key: null

runner: null

evaluation: null

---

# ATR OSC and Volume Screener (ATROSCVS)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare volatility-normalized momentum and unusual volume across a cryptocurrency watchlist using a color-coded grid.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact z-score centering/scaling, range calculation, volume normalization, selected venue symbols, timeframe alignment and signal thresholds are absent.

- Exact z-score centering/scaling, range calculation, volume normalization, selected venue symbols, timeframe alignment and signal thresholds are absent.

## How it works

- Use a modified z-score scaled with true range/ATR rather than standard deviation, alongside normalized volume intended to reduce outlier distortion. Display oscillator strength through cool-to-warm gradients.

## Outputs and intended use

- Review lower oscillator values as the author's oversold context and higher values as overbought context. The grid helps prioritize assets for further analysis rather than defining an executable multi-asset strategy.

## Parameters and stated settings

- The source says support exceeds thirty cryptocurrencies and names several examples, but does not establish a historical universe, default lengths, normalization bounds or input list.

## Failure modes and caveats

- The claim of superior long-lookback behavior is not measured here. ATR normalization does not itself guarantee fixed oscillator bounds, and volume filters can discard meaningful extreme activity.

## Missing information and implementation boundary

- Exact z-score centering/scaling, range calculation, volume normalization, selected venue symbols, timeframe alignment and signal thresholds are absent.

## Data requirements

Required inputs: OHLCV for selected cryptocurrency symbols.

Repository input-class support: unavailable or unresolved. The multi-asset symbol/venue universe and aligned historical data are unspecified; named examples do not establish a point-in-time screening dataset.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
uses this true range instead of the standard deviation in a modified z-score calculation.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
support for over 30 different cryptocurrencies
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
It employs a normalized volume calculation method, effectively filtering out outliers
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_pvpyfz2h_atr_osc_and_volume_screener_atroscvs](../tv_pvpyfz2h_atr_osc_and_volume_screener_atroscvs.md)

## Source

https://www.tradingview.com/script/pvpyfZ2h-ATR-OSC-and-Volume-Screener-ATROSCVS/

Publication ID: pvpyfZ2h. Source SHA-256: 36a57fe882a38134715c4b6ea61b280a1ed6c952f2a5ca1f4fd6fad33948621a. Raw-description SHA-256: e9c44d73bdd6250f9d06d55ceb8f1f48beb1dae522bfd3587e162b9acb0df5e5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
