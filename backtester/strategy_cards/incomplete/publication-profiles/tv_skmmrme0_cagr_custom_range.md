---

id: tv_profile_skmmrme0

name: "CAGR Custom Range"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "CAGR Custom Range calculates an annualized compound growth rate between two interactively selected chart times. It aims to make endpoint performance comparison convenient while demonstrating interactive inputs. The selected bars contribute closing prices, not manually chosen price coordinates. An optional second symbol provides a same-period comparison, with label color indicating relative outcome. The source clearly distinguishes this notional reinvested growth rate from risk: it ignores drawdowns and is not a trading backtest. Different market calendars can map the chosen times to different bars."

registry_key: null

runner: null

evaluation: null

---

# CAGR Custom Range

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

CAGR Custom Range calculates an annualized compound growth rate between two interactively selected chart times. It aims to make endpoint performance comparison convenient while demonstrating interactive inputs. The selected bars contribute closing prices, not manually chosen price coordinates. An optional second symbol provides a same-period comparison, with label color indicating relative outcome. The source clearly distinguishes this notional reinvested growth rate from risk: it ignores drawdowns and is not a trading backtest. Different market calendars can map the chosen times to different bars.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Exact annualization day-count and endpoint timestamp matching are not specified.

## How it works

- Order the selected times, find endpoint closes and compute their annualized compound growth rate.
- Optionally compute the comparison symbol’s rate over the same selected times and color the result accordingly.

## Outputs and intended use

- A connecting line and growth-rate label show endpoint performance; sign colors and comparison background distinguish outcomes.

## Parameters and stated settings

- Requires at least one day between points. Reset dates are beginning of September and October 2021.
- Compare to symbol, up/down colors and line width are configurable.

## Failure modes and caveats

- Short-window annualization exaggerates small changes and says nothing about drawdown or path risk.
- The source uses repainting security requests because it does not generate orders/alerts.

## Missing information and implementation boundary

- Exact day-count/year convention and timestamp-to-bar matching are not reproduced; invalid/nonpositive prices and unavailable comparison handling are unspecified.

## Data requirements

Required inputs: ohlcv, selected endpoint timestamps, comparison symbol history when enabled.

Repository input-class support: unavailable or unresolved. Requires user-selected times and optionally an external comparison history; those run inputs are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
close[/url] value for each of the two selected bars
```

### E2: mechanism, readiness

```text
assumes all profits are reinvested.
```

### E3: parameters

```text
minimum of one day
```

### E4: parameters

```text
beginning of September and October 2021
```

### E5: risks

```text
repainting
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/SkmMrMe0-CAGR-Custom-Range/

Publication ID: SkmMrMe0. Source SHA-256: 9cc0ef8d1f3f9afa9d66047bde245855bcb4935b64a14e56586b7142ae27e0de. Raw-description SHA-256: d215d5653a54037500c9d489c8151c5b4e3c153e784a7559ff1ab3f320d98b93.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
