---

id: tv_profile_tkzp5uj0

name: "Hancock - RSI Volume"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Hancock RSI Volume applies the relative-strength idea to estimated up and down volume instead of price changes. It is intended to compare activity associated with upward and downward price movement, providing a volume-based complement to ordinary RSI. The study obtains finer observations from a user-selected lower timeframe. Its bullish-money-flow language describes a directional estimate and should not be read as direct evidence of cash entering or leaving the market."

registry_key: null

runner: null

evaluation: null

---

# Hancock - RSI Volume

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Hancock RSI Volume applies the relative-strength idea to estimated up and down volume instead of price changes. It is intended to compare activity associated with upward and downward price movement, providing a volume-based complement to ordinary RSI. The study obtains finer observations from a user-selected lower timeframe. Its bullish-money-flow language describes a directional estimate and should not be read as direct evidence of cash entering or leaving the market.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation or data contract remains incomplete.

- Directional-volume estimation and RSI smoothing rules are missing.

## How it works

- Estimate buy and sell volume for each chart candle from configurable lower-timeframe observations.
- Use those volume components in an RSI-style calculation in place of upward and downward price changes.

## Outputs and intended use

- Inspect the relative dominance of estimated up-volume and down-volume.
- No threshold entries, exits or automatic order execution are specified.

## Parameters and stated settings

- Lower timeframe is configurable; RSI period, smoothing and numeric defaults are not disclosed.

## Failure modes and caveats

- Bar-direction estimates cannot uniquely identify actual aggressive buyers and sellers.
- Different lower-timeframe coverage can change the oscillator.

## Missing information and implementation boundary

- Buy/sell classification, flat-bar treatment, volume aggregation, RSI smoothing and initialization are absent.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV.

Repository input-class support: unavailable or unresolved. Required live updates, detailed lower-timeframe observations or multi-asset inputs are not supplied by ordinary historical chart bars.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
up-volume and down-volume are used in the RSI formula instead changes in price.
```

### E2: mechanism, required_data

```text
estimates the buy and sell volume of each candle by using a configurable lower time-frame
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_tkzp5uj0_hancock_rsi_volume](../tv_tkzp5uj0_hancock_rsi_volume.md)

## Source

https://www.tradingview.com/script/tKzP5Uj0-Hancock-RSI-Volume/

Publication ID: tKzP5Uj0. Source SHA-256: 8f34d53e8c0358f7a02e39f0f4bd05507978c9b1154de176bf2d0609ca6cbd18. Raw-description SHA-256: dd2e73afea658286fe4f0c20dfdcafd8196daff77b9bc1409fd51c09f821a9d8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
