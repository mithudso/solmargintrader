---

id: tv_profile_rgnbiicd

name: "ABC on Recursive Zigzag [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "ABC on Recursive Zigzag detects corrective patterns across nested swing scales and adds configurable trade levels and historical summaries. Its aim is to let users experiment with entry, target and stop ratios rather than accept a fixed pattern-only display. The source’s wave narrative is internally inconsistent: it calls A and C opposite to the larger trend, then describes C as aligned with that trend. The actual recognition criteria must therefore come from missing code rather than this prose. Reported win ratio/risk reward is an indicator summary, not evidence of realistic execution."

registry_key: null

runner: null

evaluation: null

---

# ABC on Recursive Zigzag [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

ABC on Recursive Zigzag detects corrective patterns across nested swing scales and adds configurable trade levels and historical summaries. Its aim is to let users experiment with entry, target and stop ratios rather than accept a fixed pattern-only display. The source’s wave narrative is internally inconsistent: it calls A and C opposite to the larger trend, then describes C as aligned with that trend. The actual recognition criteria must therefore come from missing code rather than this prose. Reported win ratio/risk reward is an indicator summary, not evidence of realistic execution.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core recursive-zigzag/pattern predicates and trade-level equations are undisclosed.

## How it works

- Build recursive multilevel zigzags to identify larger and smaller ABC structures.
- Generate trade boxes from user-defined entry/target/stop ratios and summarize historical outcomes.

## Outputs and intended use

- Pattern drawings, trade-level boxes, summary table and new/update alerts support pattern research.

## Parameters and stated settings

- Entry, target and stop ratios are configurable; exact names/defaults and zigzag controls are absent.

## Failure modes and caveats

- Nested patterns overlap and can update; outcome counts may not be independent.
- Inconsistent wave-direction explanation and unspecified fills limit interpretation of backtest summaries.

## Missing information and implementation boundary

- Zigzag algorithm, ABC ratio constraints, trade-level formulas, fill ordering, fees and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed swing-pattern method is price-based; algorithmic gaps do not imply unavailable raw data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
recursive multi level zigzag
```

### E2: parameters, readiness

```text
entry, target and stop ratios
```

### E3: risks

```text
two smaller waves in the opposite direction (A and C)
```

### E4: risks

```text
same direction as the prevailing trend.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_elliott_wave](../tv_method_elliott_wave.md)
- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)
- [tv_rgnbiicd_abc_on_recursive_zigzag_trendoscope](../tv_rgnbiicd_abc_on_recursive_zigzag_trendoscope.md)

## Source

https://www.tradingview.com/script/RGNBIIcD-ABC-on-Recursive-Zigzag-Trendoscope/

Publication ID: RGNBIIcD. Source SHA-256: 5fd24cf92f754af9eb66cfe327b98e335b1a830f95b026da1c2d851ad5ab3e16. Raw-description SHA-256: 11554d6e71ce1c92cc8ed4fd12b61f8a53e3fc24c062d97880c92b1afb72e85f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
