---

id: tv_profile_wba7j6tu

name: "Mean Deviation Index"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Mean Deviation Index combines an adaptive mean with an ATR-distance gate to highlight sufficiently large price departures. It aims to distinguish meaningful directional displacement from movement close to the mean. Positive/negative background states can be used aggressively as trend entries or as context for pullback continuation. The second example, however, calls a green/upward setup a short, contradicting the earlier green-long convention. That ambiguity must remain explicit rather than silently turning it into a corrected strategy."

registry_key: null

runner: null

evaluation: null

---

# Mean Deviation Index

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Mean Deviation Index combines an adaptive mean with an ATR-distance gate to highlight sufficiently large price departures. It aims to distinguish meaningful directional displacement from movement close to the mean. Positive/negative background states can be used aggressively as trend entries or as context for pullback continuation. The second example, however, calls a green/upward setup a short, contradicting the earlier green-long convention. That ambiguity must remain explicit rather than silently turning it into a corrected strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core EMA filtering equation and index magnitude are unspecified; directional usage prose conflicts.

## How it works

- Filter an EMA using standard deviation of ATR to obtain the reference mean.
- Only display signed nonzero index when price exceeds an ATR-multiple distance from that mean.

## Outputs and intended use

- Green positive and red negative background states show above/below-mean displacement.

## Parameters and stated settings

- ATR Multiplier defaults to one. Other smoothing/volatility lengths are absent.

## Failure modes and caveats

- The pullback-short example conflicts with the stated green-long direction.
- An ATR gate can trigger late or repeatedly during choppy expansions.

## Missing information and implementation boundary

- ATR-standard-deviation EMA filtering equation, lengths, index scale, pullback trigger and trade management are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. ATR, EMA and price distance use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
standard deviation of the ATR to filter an EMA
```

### E2: parameters

```text
default is 1 x ATR.
```

### E3: risks

```text
for a short, you wait for the background color to turn green
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wba7j6tu_mean_deviation_index](../tv_wba7j6tu_mean_deviation_index.md)

## Source

https://www.tradingview.com/script/WBA7j6tU-Mean-Deviation-Index/

Publication ID: WBA7j6tU. Source SHA-256: 9ec673c6bbdbdf22305bdc1797ed00a000b8410f5c550e4dfb6d3ae4d9f7e253. Raw-description SHA-256: 448ecac02fc6cc305f7eeb59a18194baefec0f1a64ee34b2bc362d70f46f171f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
