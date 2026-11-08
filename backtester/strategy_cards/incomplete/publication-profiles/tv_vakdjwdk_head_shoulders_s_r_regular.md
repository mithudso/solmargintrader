---

id: tv_profile_vakdjwdk

name: "Head & Shoulders S/R Regular"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Head & Shoulders S/R Regular searches a particular pivot/line geometry and monitors price inside a projected right-shoulder trigger region. It aims to make potential regular head-and-shoulders structures visible while distinguishing upside, downside and unresolved trigger behavior. The method first waits for aligned baseline points, then finds the intervening head and left shoulder. It is more specific than merely matching a familiar silhouette, but the coordinate equations for its trigger area are not present. Colored patterns are contextual states, not a fully described trading strategy."

registry_key: null

runner: null

evaluation: null

---

# Head & Shoulders S/R Regular

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Head & Shoulders S/R Regular searches a particular pivot/line geometry and monitors price inside a projected right-shoulder trigger region. It aims to make potential regular head-and-shoulders structures visible while distinguishing upside, downside and unresolved trigger behavior. The method first waits for aligned baseline points, then finds the intervening head and left shoulder. It is more specific than merely matching a familiar silhouette, but the coordinate equations for its trigger area are not present. Colored patterns are contextual states, not a fully described trading strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Trigger-area geometry and pivot alignment/search rules are not reproducible from prose.

## How it works

- Find aligned A/C/E points, highest between C–E as head D and highest between A–C as left shoulder B.
- Draw a right-shoulder trigger area and color green/red/blue according to closes above/below/inside its boundaries.

## Outputs and intended use

- Pattern/trigger-region drawings show conditional support/resistance behavior.

## Parameters and stated settings

- Date filter, left/right pivot bars, E retracement bounds, shoulder-height tolerance, head/shoulder ratio, shoulder-width adjustment and maximum visible patterns are configurable.
- Examples include E retracement 1.4–1.5, shoulder/head 35–45%, tolerances 0/85% and width adjustments 0/100/-70%.

## Failure modes and caveats

- Pattern origins can precede confirmed pivots; projected right-shoulder geometry may change.
- The source does not establish pattern success rates or stop placement.

## Missing information and implementation boundary

- Alignment tolerance, exact A/C/E search, trigger-boundary equations, default values and signal timing are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price pivots, extrema and close comparisons are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
A, C and E are alined
```

### E2: mechanism

```text
highest point between C - E
```

### E3: parameters

```text
between 1.4 & 1.5
```

### E4: parameters

```text
35-45%
```

### E5: parameters

```text
85%
```

### E6: parameters

```text
100% (Right shoulder area is double
```

### E7: parameters

```text
-70%
```

### E8: parameters

```text
0% (= the same relative height)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_head_shoulders](../../tv_method_head_shoulders.md)
- [tv_vakdjwdk_head_shoulders_s_r_regular](../tv_vakdjwdk_head_shoulders_s_r_regular.md)

## Source

https://www.tradingview.com/script/VAkdJwDk-Head-Shoulders-S-R-Regular/

Publication ID: VAkdJwDk. Source SHA-256: 432ce96aa9133bc2530c26724a960a0cbbb2e88fc14975db468ad27b66a1df6c. Raw-description SHA-256: 235dbdd9d2b62c05dbe342ec9167b7dfba9ddb2878dc3cac156282f971efb66f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
