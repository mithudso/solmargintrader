---

id: tv_profile_mll8cpjq

name: "Range Oscillator (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Range Oscillator expresses the distance of the closing price from an adaptive equilibrium as a percentage of a volatility-adjusted range. Its heatmap is intended to distinguish directional pressure, transition areas and excursions beyond an ordinary range. The author offers both breakout and mean-reversion interpretations, so an extreme does not carry a single unambiguous trading instruction. The normalizing equation is disclosed, but the adaptive inputs and color engine remain substantially descriptive."

registry_key: null

runner: null

evaluation: null

---

# Range Oscillator (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Range Oscillator expresses the distance of the closing price from an adaptive equilibrium as a percentage of a volatility-adjusted range. Its heatmap is intended to distinguish directional pressure, transition areas and excursions beyond an ordinary range. The author offers both breakout and mean-reversion interpretations, so an extreme does not carry a single unambiguous trading instruction. The normalizing equation is disclosed, but the adaptive inputs and color engine remain substantially descriptive.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation remains underspecified.

- RangeATR construction, weighted mean and heatmap computations are missing.

## How it works

- Detect a range using a minimum confirmation length and ATR width multiplier.
- Weight the equilibrium mean by consecutive candle-movement size, then compute 100 times close minus mean divided by RangeATR.
- Assign adaptive heat colors according to interaction intensity, heat levels and minimum touches.

## Outputs and intended use

- Above-zero green readings suggest bullish pressure and below-zero red readings bearish pressure.
- Excursions beyond +100 or -100 prompt breakout/exhaustion assessment; movement back toward zero suggests a possible range reset.

## Parameters and stated settings

- Minimum range length, ATR width multiplier, number of heat levels and minimum touches are configurable; numeric defaults are absent.

## Failure modes and caveats

- The same excursion can precede continuation or reversal; colors do not determine which will occur.

## Missing information and implementation boundary

- Weighted-mean formula, ATR period, range confirmation/reset and touch-counting color thresholds are undefined.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The calculation uses chart OHLCV rather than an external data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
Osc = 100 * (Close - Mean) / RangeATR
```

### E2: outputs_and_use

```text
breaks above +100 or below –100
```

### E3: mechanism

```text
Larger price changes are given greater weight
```

### E4: parameters

```text
Minimum Touches per Level
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mll8cpjq_range_oscillator_zeiierman](../tv_mll8cpjq_range_oscillator_zeiierman.md)

## Source

https://www.tradingview.com/script/mlL8CpJq-Range-Oscillator-Zeiierman/

Publication ID: mlL8CpJq. Source SHA-256: 646b85b6ef2c3692f9e1664d9f171d7999a26948519a1e4baa17de37383c7b45. Raw-description SHA-256: 91c361e9df6e6f94411168f7830e0bd05ffc3bd45ce1594a2d0a2cb2862b0a67.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
