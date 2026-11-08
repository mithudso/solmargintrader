---

id: tv_profile_nlygzrmb

name: "Short Volume Stamper"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Annotate unusual short-sale-volume episodes and summarize short-volume participation around historical highs."

registry_key: null

runner: null

evaluation: null

---

# Short Volume Stamper

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Annotate unusual short-sale-volume episodes and summarize short-volume participation around historical highs.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the disclosed anchored short/total-volume ratio, threshold colors and retrospective event-window aggregation when the separate volume feed is supplied; VWAP dollar estimates are outside this narrow scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- From the two-year price-high anchor, sum daily short-sale volume S and total volume V and calculate S/V. Color the connecting line red when S/V >= 20% and green otherwise. The numerator measures transaction flow, not outstanding short positions.
- For a new one-year short-volume high, aggregate the five preceding sessions, event session and four following sessions. For a price pivot defined as the highest high over 51 sessions, aggregate three preceding sessions, the event and two following sessions. Calculate short/total-volume ratios over those retrospective windows and apply the same color threshold.
- Secondary dollar estimates use VWAP with short and non-short turnover, but the exact VWAP anchoring is not defined.

## Outputs and intended use

- Labels, boxes and lines compare short-volume ratios around events. The text calls one measure short interest ratio, but its described numerator is short-sale volume, not outstanding short positions.

## Parameters and stated settings

- The threshold is twenty percent. The price pivot spans 51 sessions. Short-volume-high windows contain five preceding, the event and four subsequent sessions; price-pivot windows contain three preceding, the event and two subsequent sessions.

## Failure modes and caveats

- Both event windows include future sessions, so finalized stamps are retrospective. VWAP times turnover estimates gross transaction value and cannot establish remaining short positions.

## Missing information and implementation boundary

- Short-volume feed, handling of future-window completion, overlapping events, universe coverage and exact VWAP anchoring are omitted.

## Data requirements

Required inputs: daily short-sale-volume series, price/total-volume history.

Repository input-class support: unavailable or unresolved. Short-sale-volume data is a separate feed. It is not derivable from OHLCV and no verified history is supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
short volume / total volume ratio since the 2-year high price.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
a NEW 1-year high in SHORT volume is achieved, and when a PIVOT POINT high is achieved (highest high over 51 sessions).
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
5 sessions prior to the new high, the session of the new high, and the 4 sessions after the new high (10 sessions).
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
3 sessions prior to the pivot high, the session of the pivot high, and the 2 sessions after the new high (6 sessions).
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Red labels, red boxes, and red lines indicate a short volume ratio greater than or equal to 20%
```

### E6: mechanism, parameters, readiness

```text
This script calculates the total short volume, total volume, and the short volume / total volume ratio since the 2-year high price.
```

### E7: mechanism, parameters, readiness

```text
a green line (short interest ratio < 20%) connects the 2-year high to the current session’s high.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_nlygzrmb_short_volume_stamper](../../tv_nlygzrmb_short_volume_stamper.md)

## Source

https://www.tradingview.com/script/nLYgzrMB-Short-Volume-Stamper/

Publication ID: nLYgzrMB. Source SHA-256: 9d4dce0939721b2fb49e2cb315beef140170bcce999aec557153bdbefc98e514. Raw-description SHA-256: e0a3b847956d200b9f7c3054e4378405e2ae0f0ea6a28990838016e69d672e5a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
