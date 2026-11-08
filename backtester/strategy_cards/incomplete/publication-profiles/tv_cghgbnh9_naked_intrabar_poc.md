---

id: tv_profile_cghgbnh9

name: "Naked Intrabar POC"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Naked Intrabar POC approximates the price of greatest within-bar participation using either time-at-price or volume-at-price. It exposes that reference as a series so another indicator can use it instead of conventional OHLC. The source explicitly emphasizes approximation and the tradeoff between finer lower-timeframe sampling and the amount of usable history."

registry_key: null

runner: null

evaluation: null

---

# Naked Intrabar POC

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Naked Intrabar POC approximates the price of greatest within-bar participation using either time-at-price or volume-at-price. It exposes that reference as a series so another indicator can use it instead of conventional OHLC. The source explicitly emphasizes approximation and the tradeoff between finer lower-timeframe sampling and the amount of usable history.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Exact bin construction, time weighting, volume allocation, tie-breaking and meaning of naked/unretested lifetime are not specified.

- Exact bin construction, time weighting, volume allocation, tie-breaking and meaning of naked/unretested lifetime are not specified.

## How it works

- Bin lower-timeframe observations by price, summarize time or volume participation and choose an intrabar point of control.

## Outputs and intended use

- Inspect POC circles or use the exposed intrabar_poc variable as an alternative input; chart visual order may need adjustment for visibility.

## Parameters and stated settings

- Bin size and sample lower timeframe are configurable without stated defaults; time versus volume basis is selectable.

## Failure modes and caveats

- Accuracy depends on bin size and intrabar resolution; historical availability is limited, though replay can expose earlier states.

## Missing information and implementation boundary

- Exact bin construction, time weighting, volume allocation, tie-breaking and meaning of naked/unretested lifetime are not specified.

## Data requirements

Required inputs: lower-timeframe OHLCV or time-at-price observations.

Repository input-class support: available. Selected lower-resolution observations support the data class; actual history depth and exact weighting remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
approximates (!) the intrabar point of control (POC) either from time or volume at price.
```

### E2: risks, readiness

```text
trade off is between accuracy and historical availability
```

### E3: outputs_and_use, readiness

```text
intrabar_poc
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cghgbnh9_naked_intrabar_poc](../tv_cghgbnh9_naked_intrabar_poc.md)

## Source

https://www.tradingview.com/script/cgHGBnH9-Naked-Intrabar-POC/

Publication ID: cgHGBnH9. Source SHA-256: 0be06bebba8763fdd42d0700910b1dd0d73aa75b64c3eb594644685dd60830ee. Raw-description SHA-256: 25fb74021e35db55edb77b5bf289fd2f017cbcfeab3816cb925852782e7576d3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
