---

id: tv_profile_wiwhv552

name: "Custom Pattern Detection"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Custom Pattern Detection lets the user define a multi-leg retracement structure, inspect a synthetic example and search historical swing points for matches. It is a pattern-building workbench rather than a fixed harmonic-pattern catalog. Its flexibility supports testing personal hypotheses, but also means a match reflects user-selected ratios and pivot rules rather than a universally established chart pattern."

registry_key: null

runner: null

evaluation: null

---

# Custom Pattern Detection

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Custom Pattern Detection lets the user define a multi-leg retracement structure, inspect a synthetic example and search historical swing points for matches. It is a pattern-building workbench rather than a fixed harmonic-pattern catalog. Its flexibility supports testing personal hypotheses, but also means a match reflects user-selected ratios and pivot rules rather than a universally established chart pattern.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pivot confirmation and multi-leg candidate selection/overlap rules are unspecified.

- Pivot confirmation and multi-leg candidate selection/overlap rules are unspecified.

## How it works

- Construct a preview from an initial XA displacement and subsequent leg retracement ranges, using the midpoint of permitted Fibonacci percentages for the sample.
- Find swing highs/lows with pivot lookback, then accept leg retracements within each configured From/To Fib range.

## Outputs and intended use

- Switch between Create Pattern to inspect the shape and Detect Pattern to mark matching historical structures.

## Parameters and stated settings

- Supports up to six legs XA through EF, with legs optionally disabled. Offset controls preview spacing, XA Points its initial displacement, and From/To Fib percentages later legs. Example Offset 5 and XA Points -20 are illustrative.

## Failure modes and caveats

- Analytical: flexible ratios and pivot lookback invite overfitting; confirmed pivots can be known later than the displayed turning point.

## Missing information and implementation boundary

- Exact pivot confirmation, pattern overlap selection, tolerance endpoints, defaults and execution/risk rules are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to 6 legs/lines
```

### E2: parameters, readiness

```text
Offset = 5 and XA Points = -20
```

### E3: mechanism, readiness

```text
Price points between from Fib% and To Fib% are treated as valid retracement points.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wiwhv552_custom_pattern_detection](../tv_wiwhv552_custom_pattern_detection.md)

## Source

https://www.tradingview.com/script/WIwhv552-Custom-Pattern-Detection/

Publication ID: WIwhv552. Source SHA-256: 8b1c73a479bda965518d770b894767e877c81973a8c0f1aef7619f500d0c835b. Raw-description SHA-256: b5d5119d4400a7b9abbd68c56f12bffb19d0ae5a7d463fcf40ed7bf7009cd26b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
