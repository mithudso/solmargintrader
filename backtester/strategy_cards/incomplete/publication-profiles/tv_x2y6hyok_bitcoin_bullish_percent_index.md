---

id: tv_profile_x2y6hyok

name: "Bitcoin Bullish Percent Index"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Bitcoin Bullish Percent Index measures breadth across a manually chosen crypto basket by counting point-and-figure buy states, then applies another point-and-figure representation to that breadth series. It asks whether strength is broad among assets the author regards as BTC-correlated, rather than measuring Bitcoin alone. The selected basket and dual P&F transformations are central to interpreting the result."

registry_key: null

runner: null

evaluation: null

---

# Bitcoin Bullish Percent Index

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Bitcoin Bullish Percent Index measures breadth across a manually chosen crypto basket by counting point-and-figure buy states, then applies another point-and-figure representation to that breadth series. It asks whether strength is broad among assets the author regards as BTC-correlated, rather than measuring Bitcoin alone. The selected basket and dual P&F transformations are central to interpreting the result.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Automatic P&F box scaling and constituent/breadth P&F sequencing are undisclosed.

- Automatic P&F box scaling and constituent/breadth P&F sequencing are undisclosed.

## How it works

- Construct P&F states for each constituent, divide buy-signal count by total constituents and build a P&F chart of the resulting BPI.
- Classify BPI columns and buy/sell states into alerts, confirmations and corrections.

## Outputs and intended use

- Above the midpoint favors bulls, below favors bears; extreme zones contextualize new rising/falling columns and the six named breadth states.
- Six disclosed states: Bull Alert=BPI below30% then new rising X column;Bear Alert=BPI above70% then new O column declining below70%;Bull Confirmed=P&F buy signal and rising X;Bear Confirmed=P&F sell signal and falling O;Bull Correction=P&F buy signal but falling O;Bear Correction=P&F sell signal but rising X. These mappings do not supply the missing constituent/BPI P&F construction.

## Parameters and stated settings

- Basket contains 40 cryptos. Constituent reversal defaults to 3; BPI reversal is 3 boxes of 2%, requiring 6% reversal. Midpoint is 50%, overbought above 70%, oversold below 30%, range 0–100.
- Constituents use percentage scaling, automatic by timeframe or manual; source notes complex calculations can load slowly.

## Failure modes and caveats

- Analytical: discretionary fixed constituents introduce survivorship/selection bias and P&F synthetic states may vary with construction/timeframe.

## Missing information and implementation boundary

- Complete basket, automatic box-sizing map, P&F sequencing, missing-feed handling and executable trade rules are absent.

## Data requirements

Required inputs: ordinary price histories for the source-selected fixed40-crypto basket.

Repository input-class support: available. Ordinary constituent price histories are a supported data class. The source describes a discretionary fixed40-asset basket; its exact identities/cache coverage are unknown. No dynamic point-in-time universe is inferred. Missing P&F algorithms remain computational gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
choose 40 cryptos
```

### E2: parameters, readiness

```text
reversal value is 3 by default
```

### E3: parameters, readiness

```text
each box represents 2%
```

### E4: parameters, readiness

```text
at least a 6% move in BPI
```

### E5: parameters, readiness

```text
above 50% and the bears when below 50%
```

### E6: parameters, readiness

```text
overbought when above 70% and oversold when below 30%. BPI can move between 0 and 100.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
Bull Alert: BPI is below 30% and then forms a new column of X's (rises)
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
Bear Alert: BPI is above 70% and then forms a new column of O's that decline below 70%.
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
Bull Confirmed: BPI is on a P&F buy signal and in a column of X's (rising).
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
Bear Confirmed: BPI is on a P&F sell signal and in a column of O's (falling).
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
Bull Correction: BPI is on a P&F buy signal, but currently falling (column of O's).
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
Bear Correction: BPI is on a P&F sell signal, but currently rising (column of X's).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_x2y6hyok_bitcoin_bullish_percent_index](../../tv_x2y6hyok_bitcoin_bullish_percent_index.md)

## Source

https://www.tradingview.com/script/X2Y6Hyok-Bitcoin-Bullish-Percent-Index/

Publication ID: X2Y6Hyok. Source SHA-256: abcd4c4e0c838d771eddf0560bc2a151957db12cfd8dc3f2e071f8c1cc457b57. Raw-description SHA-256: f0f2d6e6e773a2a0f745f369b9f278eb6045b846618060c41715134a03db3129.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
