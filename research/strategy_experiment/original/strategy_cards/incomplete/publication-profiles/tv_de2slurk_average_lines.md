---

id: tv_profile_de2slurk

name: "Average Lines"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Average Lines constructs a moving reference from projections of relationships among historical pivots. Rather than averaging prices directly, it draws a line from the latest pivot to each preceding pivot, extends those lines, and averages their values on subsequent bars. The aim is a new moving-average-like view that incorporates many pivot slopes. The future extensions are geometric extrapolations, not forecasts with established predictive accuracy. The author also uses the script to demonstrate line fills and last-bar indexing, but its pivot-based price reference gives it a financial purpose."

registry_key: null

runner: null

evaluation: null

---

# Average Lines

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Average Lines constructs a moving reference from projections of relationships among historical pivots. Rather than averaging prices directly, it draws a line from the latest pivot to each preceding pivot, extends those lines, and averages their values on subsequent bars. The aim is a new moving-average-like view that incorporates many pivot slopes. The future extensions are geometric extrapolations, not forecasts with established predictive accuracy. The author also uses the script to demonstrate line fills and last-bar indexing, but its pivot-based price reference gives it a financial purpose.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pivot detection and retained prior-pivot set defining the averaged projection are unspecified.

- Pivot detection and retained prior-pivot set defining the averaged projection are unspecified.

## How it works

- At a pivot, connect the latest pivot to each earlier pivot and extend the resulting lines.
- On following bars, add the projected line values and average them into a composite reference.

## Outputs and intended use

- Extended component lines and their average show the combined pivot-trend projection.

## Parameters and stated settings

- No pivot lookback or numerical defaults are disclosed.
- The source warns visible lines are limited to 500 even when the average includes more components.

## Failure modes and caveats

- The displayed subset may not explain the full average.
- Pivot confirmation can lag, and a large collection of old slopes may dominate current behavior.

## Missing information and implementation boundary

- Pivot definition, high/low separation, retention, weighting, initialization and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price pivots and bar-coordinate projections are OHLCV-derived; algorithm details remain unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
draws a line from the last to every previous one
```

### E2: mechanism

```text
all these lines and added and averaged
```

### E3: parameters, risks

```text
visible lines maximum of 500
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_de2slurk_average_lines](../tv_de2slurk_average_lines.md)

## Source

https://www.tradingview.com/script/De2slurk-Average-Lines/

Publication ID: De2slurk. Source SHA-256: 159a33f5a9db6427fdca7657a103ad3d1c354150fde32292f84a040c30380760. Raw-description SHA-256: 53201f63175caa30ac5ab1621139958767536c7694087b10d6b5d84e7c449698.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
