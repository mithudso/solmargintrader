---

id: tv_profile_8ea9mvz5

name: "Technical Ratings on Multi-frames / Assets"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Technical Ratings on Multi-frames / Assets presents a compact comparison of consolidated technical opinions across assets and timeframes. It is a monitoring fork of a technical-rating indicator, designed to help a reader choose where to focus attention. The fork removes markers, visualizations and alerts in favor of a customizable table and switches between configured asset sets. Its inherited description includes features that may no longer apply after those removals. Ratings summarize indicator biases rather than independent evidence of future returns; agreement can arise because many components measure related price behavior."

registry_key: null

runner: null

evaluation: null

---

# Technical Ratings on Multi-frames / Assets

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Technical Ratings on Multi-frames / Assets presents a compact comparison of consolidated technical opinions across assets and timeframes. It is a monitoring fork of a technical-rating indicator, designed to help a reader choose where to focus attention. The fork removes markers, visualizations and alerts in favor of a customizable table and switches between configured asset sets. Its inherited description includes features that may no longer apply after those removals. Ratings summarize indicator biases rather than independent evidence of future returns; agreement can arise because many components measure related price behavior.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Component technical-rating vote predicates and oscillator calculation settings are absent.

- Component technical-rating vote predicates and oscillator calculation settings are absent.

## How it works

- Aggregate moving-average and oscillator groups with adjustable group weights, then map the result to strong-buy/buy/neutral/sell/strong-sell labels.
- Request each selected asset across configured timeframes and arrange the ratings in a table.

## Outputs and intended use

- A traffic-light-style table compares asset/timeframe states; a second configured set can be selected quickly.
- The source warns this fork may not match TradingView built-in ratings.

## Parameters and stated settings

- Display covers 12 assets in three timeframes, with another 12 configured for switching; row layouts include 3, 4, 6 or 12.
- Inherited group default is 50/50. Neutral boundaries are ±0.1 and strong boundaries ±0.5.
- Moving-average components use SMA/EMA lengths 10,20,30,50,100,200, HMA 9 and VWMA 20 plus Ichimoku; oscillator group contains 11 components.

## Failure modes and caveats

- Inherited non-repainting claims and old security limits are not independently verified.
- Many correlated components can create false confidence; removed alerts should not be assumed operational.

## Missing information and implementation boundary

- Exact component voting predicates, oscillator lengths, final fork repaint handling and default symbols/timeframes are not supplied.

## Data requirements

Required inputs: selected multi-asset ohlcv histories, configured asset universe.

Repository input-class support: unavailable or unresolved. The table requires aligned external asset histories and a user-defined universe; actual coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, purpose

```text
12 assets in 3 timeframes
```

### E2: parameters

```text
An additional 12 assets
```

### E3: parameters

```text
rows 3, 4, 6 and 12
```

### E4: parameters

```text
The default is 50/50.
```

### E5: parameters

```text
Between 0.1 and -0.1
```

### E6: parameters

```text
above/below the 0.5/-0.5 level.
```

### E7: parameters

```text
periods 10, 20, 30, 50, 100 and 200
```

### E8: parameters

```text
Hull Moving Average of period 9
```

### E9: parameters

```text
Volume-weighed Moving Average of period 20
```

### E10: parameters

```text
11 components
```

### E11: mechanism, risks, readiness

```text
Markers, visualizations and alerts have been deleted
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8ea9mvz5_technical_ratings_on_multi_frames_assets](../tv_8ea9mvz5_technical_ratings_on_multi_frames_assets.md)

## Source

https://www.tradingview.com/script/8EA9MvZ5-Technical-Ratings-on-Multi-frames-Assets/

Publication ID: 8EA9MvZ5. Source SHA-256: 7536f3e49dd70441fd3635d0bb0b7d723102207b6016b67d53b03527f7dcdd6a. Raw-description SHA-256: 16228619df77c14600dbbce32d77fc133862da28690b9c06f7f22802d6c78cc7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
