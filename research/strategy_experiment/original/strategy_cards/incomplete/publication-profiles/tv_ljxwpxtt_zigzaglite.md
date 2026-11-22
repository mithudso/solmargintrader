---

id: tv_profile_ljxwpxtt

name: "ZigzagLite"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "ZigzagLite supplies a lighter pivot and zigzag object interface for financial chart scripts. It separates calculating pivot state from extracting coordinates and drawing lines, so a caller can reuse the detected structure in its own analysis instead of treating the picture as an entry signal. The library accepts ordinary OHLC or a custom series array and optional lower-timeframe extreme timestamps. Its documentation describes object storage and drawing methods much more precisely than the actual pivot-selection calculation."

registry_key: null

runner: null

evaluation: null

---

# ZigzagLite

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

ZigzagLite supplies a lighter pivot and zigzag object interface for financial chart scripts. It separates calculating pivot state from extracting coordinates and drawing lines, so a caller can reuse the detected structure in its own analysis instead of treating the picture as an entry signal. The library accepts ordinary OHLC or a custom series array and optional lower-timeframe extreme timestamps. Its documentation describes object storage and drawing methods much more precisely than the actual pivot-selection calculation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The pivot detection and confirmation equations and recursive level construction are absent.

## How it works

- Pivot objects carry chart points, direction, recursion level and ratios based on preceding pivots; flags distinguish new pivots, double pivots and replacement of the last pivot.
- Extraction methods return prices, bar indices or chart points. Calculation can use an explicit OHLC array or properties embedded in the zigzag object.
- Fresh and continuous drawing paths manage line/label collections, with an additional polyline representation.

## Outputs and intended use

- Call calculate before consuming pivot state; drawplain only renders the state already present.
- Use returned coordinates to build another financial structure detector; no portfolio or execution behavior is specified.

## Parameters and stated settings

- Default zigzag length is 5, retained pivot count 20 and offset 0.
- Directions use 1, -1, 2 and -2; default drawing object maximum is 300.

## Failure modes and caveats

- A current pivot can replace an earlier last pivot, so its evolving endpoint should not be treated as immutable.
- Custom input arrays can change the financial meaning of the resulting structure.

## Missing information and implementation boundary

- Pivot confirmation, recursive next-level selection and ratio equations are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The default calculation uses standard chart prices; custom series and lower-timeframe timestamps are optional caller inputs.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose

```text
Lighter version of the Zigzag Library. Without indicators and sub-component divisions
```

### E2: parameters

```text
Zigzag length. Default value is 5
```

### E3: parameters

```text
max number of pivots to hold in the calculation. Default value is 20
```

### E4: parameters

```text
Default is 0 - which means calculation is done based on the latest bar.
```

### E5: parameters

```text
Valid values are 1, -1, 2, -2
```

### E6: parameters

```text
Default is 300
```

### E7: risks

```text
true if new pivot calculated replaces the old one.
```

### E8: mechanism, required_data

```text
Array containing OHLC values. Can also have custom values for which zigzag to be calculated
```

## Source

https://www.tradingview.com/script/lJXwpXtt-ZigzagLite/

Publication ID: lJXwpXtt. Source SHA-256: 0617d2812e099039e4ca2f433cc29f5a78bca8c0d74d646ecbedd03a42eb0b6a. Raw-description SHA-256: cafa594d657dfeb76ec9a0b848d82b00aafe42cb34a646e5b1065558cb8b64a8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
