---

id: tv_profile_lper4qca

name: "Volume Analysis - Heatmap and Volume Profile"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Analysis combines a lower-timeframe volume heatmap with a volume profile and column statistics. The user chooses the grid dimensions and history depth, and the script examines lower-timeframe price movement and volume inside chart candles. The resulting display is intended to expose where activity concentrates and how buying and selling estimates differ across time columns. It can draw in a separate pane or on the main chart and can compress non-trading gaps so adjacent activity columns remain visually continuous."

registry_key: null

runner: null

evaluation: null

---

# Volume Analysis - Heatmap and Volume Profile

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Analysis combines a lower-timeframe volume heatmap with a volume profile and column statistics. The user chooses the grid dimensions and history depth, and the script examines lower-timeframe price movement and volume inside chart candles. The resulting display is intended to expose where activity concentrates and how buying and selling estimates differ across time columns. It can draw in a separate pane or on the main chart and can compress non-trading gaps so adjacent activity columns remain visually continuous.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Volume allocation, directional classification and value-area equations are missing.
- The lower-timeframe resolution and historical coverage contract is incomplete.

## How it works

- Lower-timeframe open, close, volume and timestamps supply a grid of price movement and associated volume.
- Heatmap boxes encode volume intensity and direction, with absolute positioning or a zero-line layout.
- A volume profile adds value-area boundaries and point of control; columns can display volume, cumulative volume and estimated buy/sell differences.

## Outputs and intended use

- Inspect the heatmap, profile and column totals as activity context.
- Use compressed gaps to compare sequential trading activity while remembering that visual spacing no longer represents uniform elapsed time.

## Parameters and stated settings

- The source claims up to 100K lower-timeframe observations per candle and a volume profile with up to 25 rows.
- Grid rows, columns, history, account-plan mode and minimum resolution are configurable.

## Failure modes and caveats

- Lower-timeframe history may be unavailable on large chart timeframes.
- Directional volume estimates do not constitute an actual bid/ask trade classification.

## Missing information and implementation boundary

- Price-bin allocation, buy/sell inference, value-area calculation and automatic resolution selection are not defined.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV.

Repository input-class support: unavailable or unresolved. The detailed grid needs lower-timeframe history and platform resolution access beyond ordinary chart bars.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
it can be up to 100K for each candle
```

### E2: parameters

```text
Volume Profile with up to 25 rows
```

### E3: mechanism

```text
calculates how closing price moves, how much volume on each move
```

### E4: outputs_and_use

```text
shows Volume, Cumulative volume, Difference between Buy/Sell volume for each column
```

### E5: mechanism

```text
omitting weekends and holidays.
```

### E6: required_data, risks

```text
number of contained candles should be more than 1
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lper4qca_volume_analysis_heatmap_and_volume_profile](../tv_lper4qca_volume_analysis_heatmap_and_volume_profile.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/lPEr4QCA-Volume-Analysis-Heatmap-and-Volume-Profile/

Publication ID: lPEr4QCA. Source SHA-256: 03e07e7be76caa4c70b1ba35534b5f8725a99c12bc9b838d3b951a2a69e67b91. Raw-description SHA-256: 656d5414ce8c8d62addd7f074de59727dffd4895ec06dde972ecfec9ae513ed3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
