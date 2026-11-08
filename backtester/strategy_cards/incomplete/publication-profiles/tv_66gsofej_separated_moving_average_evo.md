---

id: tv_profile_66gsofej

name: "Separated Moving Average - evo"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Separated Moving Average splits the price history into positive-candle and negative-candle streams instead of letting every candle update the same average. The aim is to display two directional references that represent different candle populations. Its brief description emphasizes how a side retains information when the current candle belongs to the other side, making this a stateful smoothing comparison rather than a normal fast/slow crossover pair."

registry_key: null

runner: null

evaluation: null

---

# Separated Moving Average - evo

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Separated Moving Average splits the price history into positive-candle and negative-candle streams instead of letting every candle update the same average. The aim is to display two directional references that represent different candle populations. Its brief description emphasizes how a side retains information when the current candle belongs to the other side, making this a stateful smoothing comparison rather than a normal fast/slow crossover pair.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The average formula, value stream and opposite-side state updates are unspecified.

- The average formula, value stream and opposite-side state updates are unspecified.

## How it works

- Build one moving average from positive candles and another from negative candles.
- When the current bar is positive, the negative average uses its last known negative bar for the calculation; the source does not explicitly spell out the symmetric negative-bar case.

## Outputs and intended use

- Compare the separate positive and negative candle averages visually; the author provides no explicit buy/sell interpretation.

## Parameters and stated settings

- Heikin Ashi smoothing is enabled by default and can be disabled in inputs; lengths and average types are not given.

## Failure modes and caveats

- Analytical: holding the last opposite-color observation can make its reference stale during persistent trends; Heikin Ashi also changes the analyzed candle series.

## Missing information and implementation boundary

- The exact moving-average formula, candle-value input, opposite-side update symmetry and trading rules are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart price/volume data supports the described calculation class; matching Pine implementation remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
one based on positive candles and the other based on negative candles.
```

### E2: mechanism, readiness

```text
If the current bar is positive, the negative MA will use its last known negative bar for the calculation.
```

### E3: parameters, readiness

```text
The default setting uses Heikin Ashi to smooth the candles with the trend, you can turn this off if you want in inputs.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_66gsofej_separated_moving_average_evo](../tv_66gsofej_separated_moving_average_evo.md)
- [tv_method_heikin_ashi](../../tv_method_heikin_ashi.md)

## Source

https://www.tradingview.com/script/66gsofEJ-Separated-Moving-Average-evo/

Publication ID: 66gsofEJ. Source SHA-256: ff113795cf020201327be742862ba27d9404ffebd8ded10eccf85ffddcf1bee6. Raw-description SHA-256: f40de7f9d1f4269c335c4332b6e9cce4dbbf94cd45fd2d0c26f28f1067c6a273.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
