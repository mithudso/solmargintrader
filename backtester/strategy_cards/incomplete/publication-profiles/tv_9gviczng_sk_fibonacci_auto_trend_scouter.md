---

id: tv_profile_9gviczng

name: "[SK] Fibonacci Auto Trend Scouter"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Fibonacci Auto Trend Scouter automatically draws trend references from two timeframes and Fibonacci levels from the shorter horizon. It aims to reduce manual chart annotation while keeping both near-term and broader directional context visible. Optional sights connect a trend’s midpoint to the current price, offering a visual sense of displacement. The levels and lines evolve as high/low values change, so they are dynamic references rather than fixed historically available support/resistance. The source suggests reading direction and potential levels but supplies no systematic entry or confirmation test."

registry_key: null

runner: null

evaluation: null

---

# [SK] Fibonacci Auto Trend Scouter

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fibonacci Auto Trend Scouter automatically draws trend references from two timeframes and Fibonacci levels from the shorter horizon. It aims to reduce manual chart annotation while keeping both near-term and broader directional context visible. Optional sights connect a trend’s midpoint to the current price, offering a visual sense of displacement. The levels and lines evolve as high/low values change, so they are dynamic references rather than fixed historically available support/resistance. The source suggests reading direction and potential levels but supplies no systematic entry or confirmation test.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** High/low selection windows and the Fibonacci-level construction are undisclosed.

- High/low selection windows and the Fibonacci-level construction are undisclosed.

## How it works

- Detect highs/lows on two selected timeframes and update their trend lines as price changes.
- Color each line by its own direction and optionally draw midpoint-to-current-price sights.
- Use the shorter timeframe’s highest/lowest values to compute Fibonacci support/resistance levels.

## Outputs and intended use

- Trend lines/extensions, optional source labels and short Fibonacci lines with level/price tooltips support discretionary chart analysis.

## Parameters and stated settings

- Two timeframes, line colors/styles/widths/extensions and labels are configurable.
- Sights default off; Fibonacci lines default short and can extend left/right.
- The description mentions seven data-point labels per timeframe but gives no timeframe or ratio defaults.

## Failure modes and caveats

- Updating extrema can shift historical-looking references; no non-repainting guarantee is established.
- Automatically drawn Fibonacci levels do not demonstrate that price will react there.

## Missing information and implementation boundary

- High/low detection windows, pivot confirmation, Fibonacci ratios, timeframe defaults and actionable trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Timeframe highs/lows and current price are OHLCV-derived; precise aggregation and drawing rules remain unspecified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, parameters

```text
2 different timeframes
```

### E2: mechanism, readiness

```text
lines are updated.
```

### E3: parameters

```text
7 data points of each timeframe
```

### E4: parameters

```text
They are toggled off by default
```

### E5: mechanism

```text
highest and lowest value from the short timeframe
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_9gviczng_sk_fibonacci_auto_trend_scouter](../tv_9gviczng_sk_fibonacci_auto_trend_scouter.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/9GviCznG-SK-Fibonacci-Auto-Trend-Scouter/

Publication ID: 9GviCznG. Source SHA-256: 7fd3485890c34ce91b7b4d22f9d5642748bde5236d89dddd7e1c1896592d477d. Raw-description SHA-256: 84a4b8f999b4d9e6abe45a137f993c40e138cad78eef1327895a47b49a76b5a4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
