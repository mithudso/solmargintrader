---

id: tv_profile_nbswkxvu

name: "Electrocardiogram Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Replace conventional candles with an electrocardiogram-style visualization that distinguishes candle direction, close-to-close movement and the order of intrabar extremes."

registry_key: null

runner: null

evaluation: null

---

# Electrocardiogram Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Replace conventional candles with an electrocardiogram-style visualization that distinguishes candle direction, close-to-close movement and the order of intrabar extremes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the ordered-OHLC block transformation and its three explicit color rules when extrema ordering is supplied; acquiring that ordering and exact plotting coordinates remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Given OHLC and the observed order of the bar’s high and low, build five connected segments: open–open, open–first extreme, first–second extreme, second extreme–close and close–close. Each block occupies seven ordinary candle spaces.
- Color its body green when close > open and red otherwise. Color its border green when current close > previous close and red otherwise. Color signal lines green if the high occurs after the low, and red if the low occurs after the high.

## Outputs and intended use

- Use the different color layers to inspect distinct dimensions of price behavior. Background highlighting helps map the expanded blocks back to the original candles.

## Parameters and stated settings

- Each block uses five lines and one box and occupies seven candle spaces. The author states a five-hundred-line limit allows no more than one hundred bars in this implementation.

## Failure modes and caveats

- Ordinary OHLC does not reveal whether high or low happened first. If the script infers order rather than observing it, the displayed sentiment narrative may be wrong.

## Missing information and implementation boundary

- How intrabar extreme order is acquired, tie treatment and live persistence are unspecified. Exact segment x positions/vertical scaling and complete rendering parity are not printed.

## Data requirements

Required inputs: OHLCV, intrabar ordering of high and low.

Repository input-class support: unavailable or unresolved. OHLCV supplies prices but not the order of intrabar extrema; that additional requirement is not resolved in the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
each block will take 1 box and 5 lines, it is not possible to display more than 100 bars.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Each block of new Electrocardiogram chart will take the space of 7 bars of candlestick chart.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
open-firstPeak(high or low of the bar whichever comes first)
```

### E4: mechanism, parameters, readiness

```text
If close is greater than open, body is green. Otherwise, the body is painted red.
```

### E5: mechanism, parameters, readiness

```text
If the close of current bar is greater than that of last bar, then the border color is green. Otherwise, border color is painted red.
```

### E6: mechanism, parameters, readiness

```text
If highest part of the bar reached after reaching the lowest part of the bar, then signal lines are coloured green
```

## Source

https://www.tradingview.com/script/NbsWKxVu-Electrocardiogram-Chart/

Publication ID: NbsWKxVu. Source SHA-256: 2279c85aa096e72b85164c03aacdf068807ddd0181b70113d832328a9cfa7caf. Raw-description SHA-256: 15937530f18e9d2036b74545a7f4411bc65c380243c3c43660f8e8934f44257e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
