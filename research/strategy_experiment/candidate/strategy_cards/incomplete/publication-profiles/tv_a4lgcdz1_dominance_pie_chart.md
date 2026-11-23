---

id: tv_profile_a4lgcdz1

name: "Dominance Pie Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Dominance Pie Chart puts available ticker-dominance measures into one pie-style display with percentage share and rise/fall information. It is a market-composition view rather than a trade signal. The short source does not identify its asset universe or denominator, so the displayed dominance cannot be assumed to represent a complete cryptocurrency market or any particular investable basket."

registry_key: null

runner: null

evaluation: null

---

# Dominance Pie Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dominance Pie Chart puts available ticker-dominance measures into one pie-style display with percentage share and rise/fall information. It is a market-composition view rather than a trade signal. The short source does not identify its asset universe or denominator, so the displayed dominance cannot be assumed to represent a complete cryptocurrency market or any particular investable basket.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Dominance feed, asset list, denominator, aggregation and rise/fall reference interval are missing.

- Dominance feed, asset list, denominator, aggregation and rise/fall reference interval are missing.

## How it works

- Read unspecified available dominance series and present each ticker’s total percentage alongside its percentage change.

## Outputs and intended use

- Compare relative dominance shares and changes visually on any timeframe.

## Parameters and stated settings

- Source says every timeframe is supported and loading can take time; no universe, change horizon or defaults are provided.

## Failure modes and caveats

- Analytical: shares from inconsistent denominators or incomplete assets can mislead, and relative dominance can rise while absolute market value falls.

## Missing information and implementation boundary

- Dominance feed, asset list, denominator, aggregation and rise/fall reference interval are missing.

## Data requirements

Required inputs: selected dominance percentage histories.

Repository input-class support: unavailable or unresolved. External dominance series and a defined universe/denominator are required; price OHLCV alone is insufficient.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, outputs_and_use, readiness

```text
total % dominance per ticker and between brackets
the % rise/fall.
```

### E2: parameters, readiness

```text
Can be used in every timeframe
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_a4lgcdz1_dominance_pie_chart](../tv_a4lgcdz1_dominance_pie_chart.md)

## Source

https://www.tradingview.com/script/a4lgCDZ1-Dominance-Pie-Chart/

Publication ID: a4lgCDZ1. Source SHA-256: bb2094a5bb1e2564f854145ffd0d78cb47a75681d2d2f07ee4c1bca1eb92d07e. Raw-description SHA-256: e3d6f28c72a9521132134406278937acd1beb670f1ab1dc54f1e069b1104fa87.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
