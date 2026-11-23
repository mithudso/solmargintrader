---

id: tv_profile_10xmhfge

name: "Volume per Point"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume per Point helps a reader compare traded activity with the distance a candle travels. Its intended use is to distinguish ordinary volume changes from unusually concentrated activity, divergence, and possible exhaustion. The author treats abnormal spikes as prompts for interpretation rather than prescribing an order. A separate volume display lets the reader compare this concentration measure with directional volume. This is therefore a discretionary volume-reading aid, not a complete trading method."

registry_key: null

runner: null

evaluation: null

---

# Volume per Point

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume per Point helps a reader compare traded activity with the distance a candle travels. Its intended use is to distinguish ordinary volume changes from unusually concentrated activity, divergence, and possible exhaustion. The author treats abnormal spikes as prompts for interpretation rather than prescribing an order. A separate volume display lets the reader compare this concentration measure with directional volume. This is therefore a discretionary volume-reading aid, not a complete trading method.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Volume-per-point denominator and exhaustion/divergence predicates are not disclosed.

- Volume-per-point denominator and exhaustion/divergence predicates are not disclosed.

## How it works

- The script relates volume to candle points, then distinguishes increases and decreases in that measure.
- It separately flags divergence between volume and candle range and exhaustion relative to the preceding candle. RSI and percentage conditions can gate those flags.

## Outputs and intended use

- Columns use green/red for VP increases/decreases and yellow/purple for divergence/exhaustion.
- A lime/red histogram represents buying/selling volume; chart candles can repeat the divergence/exhaustion colors.

## Parameters and stated settings

- Volume multiplier accepts decimals to adjust its visual scale.
- RSI thresholds and candle-range/volume percentage filters are configurable; defaults are not given.

## Failure modes and caveats

- An elevated volume-per-distance reading does not establish market-maker identity or predict direction.
- Directional volume and exhaustion labels may be sensitive to the undisclosed classification rules.

## Missing information and implementation boundary

- Exact VP denominator, zero-range handling, directional-volume formula, exhaustion tests, and filter defaults are absent.
- No entry, stop, target, position-sizing, or execution rules are supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed inputs are candle prices/ranges and volume, a data class available from OHLCV; formula and market-history parity are unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
this script gives you the volume for every point.
```

### E2: mechanism, outputs_and_use

```text
Yellow - There was divergence between volume and candle range
Purple - There are signs of exhaustion compared to the previous candlestick
```

### E3: outputs_and_use

```text
Lime - Buying volume
Red - Selling volume
```

### E4: parameters

```text
Decimals are allowed!
```

### E5: parameters, mechanism

```text
RSI Filters - RSI must be below or above the specified value for the divergence or exhaustion to trigger
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_10xmhfge_volume_per_point](../tv_10xmhfge_volume_per_point.md)

## Source

https://www.tradingview.com/script/10XmHfge-Volume-per-Point/

Publication ID: 10XmHfge. Source SHA-256: 04443ea7a8ff778aa779107ccc4a7501c5dbc2ee1bf9fdb3417f3202da28d7ae. Raw-description SHA-256: b8bd3c4d25e810158591794100a960a4a53d4aaadf2e7e4de3f34e557b1f0ad9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
