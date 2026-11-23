---

id: tv_profile_jlrxim5v

name: "RSI Bar Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare several RSI readings at once with configurable compact lines or arrows and threshold-aware coloring."

registry_key: null

runner: null

evaluation: null

---

# RSI Bar Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare several RSI readings at once with configurable compact lines or arrows and threshold-aware coloring.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Standard RSI with caller-selected source/length/timeframe and explicit four-zone color comparisons defines a reproducible indicator.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate five RSI series with individually selectable source, length and timeframe. Color each according to whether it is beyond the sell limit, above the midpoint, below the midpoint or beyond the buy limit.

## Outputs and intended use

- Use the display to compare momentum states across configurations. Labels track the selected limits, while line/arrow style and sizing adapt the layout.

## Parameters and stated settings

- The disclosed limits include 30 and 70, with midpoint 50. Source, length, timeframe, width, colors, limits, line type and right-label offset are adjustable.

## Failure modes and caveats

- Multiple RSI readings can be highly correlated. Developing higher-timeframe readings may change before those bars close.

## Missing information and implementation boundary

- Actual default lengths/timeframes, smoothing details, higher-timeframe confirmation and alert or entry rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
5 RSI with different options:
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- limit change (30, 70), labels will be changed accordingly
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- when RSI > sell limit
- when RSI > 50 but below sell limit
- when RSI < 50 but above buy limit
- when RSI < buy limit
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jlrxim5v_rsi_bar_chart](../tv_jlrxim5v_rsi_bar_chart.md)

## Source

https://www.tradingview.com/script/JLrxIM5v-RSI-Bar-Chart/

Publication ID: JLrxIM5v. Source SHA-256: 1a08393053745ce77cb76dc1d4301e262b5ef26126310543e4520429adfe2dc9. Raw-description SHA-256: 4cde5ec12f4bef3627bf93fa0323c398eed174f18e59f64db22c39e14454a312.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
