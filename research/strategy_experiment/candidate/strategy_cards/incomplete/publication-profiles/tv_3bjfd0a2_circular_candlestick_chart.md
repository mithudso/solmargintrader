---

id: tv_profile_3bjfd0a2

name: "Circular Candlestick Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Circular Candlestick Chart redraws historical OHLC bars as circular arcs to encourage alternative inspection of price structure. The author openly calls the arrangement impractical, but proposes that it might expose candle clusters or unfamiliar patterns. It remains trading-related because it transforms actual candles and provides a market-sentiment interpretation; it is not merely decorative artwork."

registry_key: null

runner: null

evaluation: null

---

# Circular Candlestick Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Circular Candlestick Chart redraws historical OHLC bars as circular arcs to encourage alternative inspection of price structure. The author openly calls the arrangement impractical, but proposes that it might expose candle clusters or unfamiliar patterns. It remains trading-related because it transforms actual candles and provides a market-sentiment interpretation; it is not merely decorative artwork.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The circular coordinate transformation and percentile population are undisclosed.

- The circular coordinate transformation and percentile population are undisclosed.

## How it works

- Arrange newer candles farther from the circle origin and map OHLC clockwise; longer arcs correspond to greater body or wick ranges.
- Add percentile pointers so recent arcs can be compared with a high or low reference for a directional impression.

## Outputs and intended use

- Inspect clusters and price patterns in the circular layout; proximity of recent arcs to the upper percentile pointer is suggested as an uptrend cue.

## Parameters and stated settings

- Length selects the number of past candles, Width sets chart width, Spacing controls arc separation, and lower Precision values improve detail at the cost of more lines.
- Pointers mark the 75th percentile in blue and the 25th in orange; no default input settings are given.

## Failure modes and caveats

- Analytical: geometric distortion and difficult settings can obscure ordinary price relationships; suggested patterns are exploratory.

## Missing information and implementation boundary

- The source does not specify the coordinate transformation, percentile population or a reproducible trading rule.

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
The most recent candles are further away from the circle origin. Note that OHLC values follow a clockwise direction.
```

### E2: parameters, readiness

```text
two pointers indicating the location of the 75 (in blue) and 25 (in orange) percentiles.
```

### E3: parameters, risks, readiness

```text
with lower values returning more precise results, however, more precision requires a higher amount of lines.
```

## Source

https://www.tradingview.com/script/3BjFD0A2-Circular-Candlestick-Chart/

Publication ID: 3BjFD0A2. Source SHA-256: 5295e4520aa77cdc78002e0424af9922c863474cb29ccbea0b5c8dea8b42d77a. Raw-description SHA-256: 5b586ce194d1d432767b0cb4484435b995226dcda68a751bca1bc702366f5e1b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
