---

id: tv_profile_ev2tidhj

name: "Faith Indicator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Faith Indicator contrasts volume associated with expanding highs and lows, then converts the difference into qualitative confidence-style grades. A separate Hull Agreement background summarizes price movement, allowing the user to compare price and participation classifications. The emotional labels are metaphors for inferred demand/supply, not measurements of actual investor feelings or identities."

registry_key: null

runner: null

evaluation: null

---

# Faith Indicator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Faith Indicator contrasts volume associated with expanding highs and lows, then converts the difference into qualitative confidence-style grades. A separate Hull Agreement background summarizes price movement, allowing the user to compare price and participation classifications. The emotional labels are metaphors for inferred demand/supply, not measurements of actual investor feelings or identities.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Averaging periods, grading boundaries, demand/supply accumulation and Hull Agreement equations are absent.

- Averaging periods, grading boundaries, demand/supply accumulation and Hull Agreement equations are absent.

## How it works

- Associate greater volume plus higher high with demand and greater volume plus lower low with supply; subtract average supply from demand and grade the result.
- Color a histogram by faith/distrust and overlay a Hull Agreement price-movement background.

## Outputs and intended use

- Compare volume grade with price direction for confirmation or disagreement, which the author treats as possible unsustainable movement.

## Parameters and stated settings

- Faith grades are ±1, ±2, ±4, ±6, ±8 and zero; background grades range -2 to 2 with color meanings. No lookbacks/defaults are supplied.

## Failure modes and caveats

- Requires published volume; analytical: candle/volume geometry does not identify minority traders or directly measure conviction.

## Missing information and implementation boundary

- Averaging periods, grading boundaries, demand/supply accumulation and Hull Agreement equations are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Very high faith graduated as 8
```

### E2: parameters, readiness

```text
High faith as 6
Good faith as 4
Some Faith as 2
Little Faith as 1
```

### E3: parameters, readiness

```text
Self Protection Distrust graduated as -8
Fear Distrust as -6
Anxiety Distrust as -4
Suspicion Distrust as -2
Doubt Distrust as -1
```

### E4: parameters, readiness

```text
grade 2: blue
```

### E5: parameters, readiness

```text
grad -2: red
```

### E6: risks, readiness

```text
only works if volume is published.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ev2tidhj_faith_indicator](../tv_ev2tidhj_faith_indicator.md)

## Source

https://www.tradingview.com/script/ev2TidhJ-Faith-Indicator/

Publication ID: ev2TidhJ. Source SHA-256: b64b7dff7cb2025ff78921e9d24361058e75b45849aea4830a81d39639d39a44. Raw-description SHA-256: 46c7ad931ceee724be5323ce755e1fbd04302ca9d181351edfb823e9aa23796e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
