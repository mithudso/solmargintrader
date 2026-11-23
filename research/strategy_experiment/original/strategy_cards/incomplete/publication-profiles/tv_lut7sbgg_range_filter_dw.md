---

id: tv_profile_lut7sbgg

name: "Range Filter [DW]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Range Filter is an experimental price-noise filter intended to make the prevailing trend easier to see. It borrows the idea of a volatility gate from QQE but applies the gate to price instead of smoothed RSI. The description establishes a useful conceptual separation between the measured range, the filtered price and the boundaries that would cause the filter to move. It does not provide enough detail to reproduce the published line exactly."

registry_key: null

runner: null

evaluation: null

---

# Range Filter [DW]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Range Filter is an experimental price-noise filter intended to make the prevailing trend easier to see. It borrows the idea of a volatility gate from QQE but applies the gate to price instead of smoothed RSI. The description establishes a useful conceptual separation between the measured range, the filtered price and the boundaries that would cause the filter to move. It does not provide enough detail to reproduce the published line exactly.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation remains underspecified.

- The range estimator and state-update recurrence are not disclosed.

## How it works

- Calculate a smoothed average price range and multiply it by a user-specified amount.
- Gate price changes that fail to exceed that range; plot target boundaries around the filtered state.

## Outputs and intended use

- Read the filtered line and trend-based candle colors as directional context.
- The target ranges show prices that would trigger movement rather than promised breakout fills or trade targets.

## Parameters and stated settings

- A range multiplier is mentioned, but neither its default nor a range averaging period is supplied.

## Failure modes and caveats

- A gate can suppress genuine early moves as well as noise; delayed movement is inherent to the concept.

## Missing information and implementation boundary

- The range definition, smoothing method, period, initialization and filter-update recurrence are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The calculation uses chart OHLCV rather than an external data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters

```text
First, a smooth average price range is calculated for the basis of the filter and multiplied by a specified amount.
```

### E2: mechanism

```text
gating price movements that do not exceed the specified range.
```

### E3: outputs_and_use

```text
The color scheme is based on the filtered price trend.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lut7sbgg_range_filter_dw](../tv_lut7sbgg_range_filter_dw.md)

## Source

https://www.tradingview.com/script/lut7sBgG-Range-Filter-DW/

Publication ID: lut7sBgG. Source SHA-256: f164a49ccd4788a20240187127e21c7a75787b922d41a5b7bc255f86ce10e600. Raw-description SHA-256: 61ec440b256273dc4d2c5f18c842d49a5c2bd827f3d2d94524c027411309fe64.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
