---

id: tv_profile_xkbwnq2h

name: "Intrabar Run Count Indicator [tbiktag]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Intrabar Run Count tests the sequence of positive and negative returns within each chart bar for departure from a random-sign model. It aims to identify unusual clustering or alternation, not forecast direction. A standardized observed-versus-expected run count is compared with confidence thresholds and highlighted on the chart. The description contains a core contradiction: it defines an absolute difference but later interprets negative statistics. It also loosely associates too few runs with mean reversion, although runs of equal signs usually indicate clustering. Those ambiguities prevent an exact specification."

registry_key: null

runner: null

evaluation: null

---

# Intrabar Run Count Indicator [tbiktag]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Intrabar Run Count tests the sequence of positive and negative returns within each chart bar for departure from a random-sign model. It aims to identify unusual clustering or alternation, not forecast direction. A standardized observed-versus-expected run count is compared with confidence thresholds and highlighted on the chart. The description contains a core contradiction: it defines an absolute difference but later interprets negative statistics. It also loosely associates too few runs with mean reversion, although runs of equal signs usually indicate clustering. Those ambiguities prevent an exact specification.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Signed-versus-absolute statistic and zero-return/sample conventions are ambiguous.

## How it works

- Construct intrabar return signs and count consecutive same-sign runs.
- Compare observed run count with its null expectation/standard deviation and threshold the resulting statistic.

## Outputs and intended use

- Indicator line, on-chart marks and bar colors flag potential non-randomness without a long/short recommendation.

## Parameters and stated settings

- Confidence level and intrabar analysis count are configurable; defaults absent.

## Failure modes and caveats

- Statistical rejection is not proof of tradable inefficiency.
- Small samples, zero returns and repeated testing affect calibration.
- Absolute-versus-signed statistic prose conflicts.

## Missing information and implementation boundary

- Runs mean/variance equations are only linked, zero handling, continuity correction, intrabar selection and defaults are absent.

## Data requirements

Required inputs: lower-timeframe price histories.

Repository input-class support: unavailable or unresolved. Requires compatible intrabar sequences; chart candles alone cannot supply run order.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
absolute difference between the observed number of runs and the expected number
```

### E2: risks, readiness

```text
If the test statistic is negative
```

### E3: outputs_and_use, risks

```text
do not convey directional information
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_gap_fill](../tv_method_gap_fill.md)
- [tv_xkbwnq2h_intrabar_run_count_indicator_tbiktag](../tv_xkbwnq2h_intrabar_run_count_indicator_tbiktag.md)

## Source

https://www.tradingview.com/script/XkBwnQ2h-Intrabar-Run-Count-Indicator-tbiktag/

Publication ID: XkBwnQ2h. Source SHA-256: 57c89498458ac4f885d5bfacaf709cc92c0c37fc7f8950b7ac91773c6c87bc71. Raw-description SHA-256: e70f855eeb362cad9792eada6be79ee2a63a9d4ffb99b5d0021ce777241f55a5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
