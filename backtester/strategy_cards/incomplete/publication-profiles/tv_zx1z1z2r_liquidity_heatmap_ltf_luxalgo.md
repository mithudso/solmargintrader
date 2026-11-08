---

id: tv_profile_zx1z1z2r

name: "Liquidity Heatmap LTF [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Liquidity Heatmap LTF highlights high-volume lower-timeframe candle bodies inside chart candles. Its aim is to locate compact intrabar activity regions that may be hidden by the parent candle. The highest-activity body receives a special color and interval lines, while optional range/direction lines preserve broader candle context. The term liquidity describes attributed candle activity rather than order-book depth. The source warns that overlapping lower-volume bodies can cover stronger ones, meaning the visible heatmap is not a guaranteed complete ranking of all activity zones."

registry_key: null

runner: null

evaluation: null

---

# Liquidity Heatmap LTF [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Liquidity Heatmap LTF highlights high-volume lower-timeframe candle bodies inside chart candles. Its aim is to locate compact intrabar activity regions that may be hidden by the parent candle. The highest-activity body receives a special color and interval lines, while optional range/direction lines preserve broader candle context. The term liquidity describes attributed candle activity rather than order-book depth. The source warns that overlapping lower-volume bodies can cover stronger ones, meaning the visible heatmap is not a guaranteed complete ranking of all activity zones.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Heatmap normalization/ranking scope and overlap behavior are not fully specified.

## How it works

- Retrieve lower-timeframe open/close/volume and map candle bodies into column heatmaps.
- Highlight the highest-associated-volume body and its bounds; optionally show full range and direction lines.

## Outputs and intended use

- Heatmap colors and interval/range references support discretionary intrabar activity inspection.

## Parameters and stated settings

- LTF must be below chart timeframe; colors and graphical styles are configurable. Numeric defaults are absent.

## Failure modes and caveats

- Overlapping bodies can visually replace a higher-volume highlight.
- Body attribution does not allocate actual transactions across price or reveal resting liquidity.

## Missing information and implementation boundary

- Color normalization, overlap priority, exact volume ranking scope, default LTF and update timing are absent.

## Data requirements

Required inputs: lower-timeframe ohlcv.

Repository input-class support: unavailable or unresolved. Requires intrabar prices/volume beyond chart candles; compatible history is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: required_data, mechanism

```text
closing/opening price and volume data
```

### E2: risks, readiness

```text
candle body with the highest volume is overlapped by a candle body with lower volume this one will be highlighted instead
```

### E3: parameters

```text
Must be lower than the current chart timeframe.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zx1z1z2r_liquidity_heatmap_ltf_luxalgo](../tv_zx1z1z2r_liquidity_heatmap_ltf_luxalgo.md)

## Source

https://www.tradingview.com/script/ZX1z1Z2r-Liquidity-Heatmap-LTF-LuxAlgo/

Publication ID: ZX1z1Z2r. Source SHA-256: 8c7c4a00462b0dfd8b3d3faf4ff289473cb53b850bece7f92a21b3f21da4d4f0. Raw-description SHA-256: aeb53e26e4adb8430465ace61d351608b44d852a2eeb620907c6b5586fd6ff1c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
