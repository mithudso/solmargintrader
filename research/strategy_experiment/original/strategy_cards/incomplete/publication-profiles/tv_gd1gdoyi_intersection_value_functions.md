---

id: tv_profile_gd1gdoyi

name: "Intersection Value Functions"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Intersection Value Functions estimates where two connected series cross between samples. It offers crossover/crossunder variants and explicit moving-average/support-resistance applications. The method is linear interpolation of plotted segments, not actual intrabar transaction reconstruction. A pairwise matrix and magnified drawing extend it across average families. The common-factor derivation is clear, but a claimed equivalent expression uses the wrong slope and is said to power the functions, creating a material implementation ambiguity."

registry_key: null

runner: null

evaluation: null

---

# Intersection Value Functions

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

Intersection Value Functions estimates where two connected series cross between samples. It offers crossover/crossunder variants and explicit moving-average/support-resistance applications. The method is linear interpolation of plotted segments, not actual intrabar transaction reconstruction. A pairwise matrix and magnified drawing extend it across average families. The common-factor derivation is clear, but a claimed equivalent expression uses the wrong slope and is said to power the functions, creating a material implementation ambiguity.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Source says functions use a non-equivalent interpolation expression; actual behavior requires resolution.

## How it works

- Compute segment slopes and common factor(B1−A1)/(m1−m2).
- Evaluate a segment at that factor on a qualifying cross.
- Extend intersection levels or build matrix/zoom views.

## Outputs and intended use

- Intersection prices/levels, location histogram and matrix support crossover research.

## Parameters and stated settings

- Two sources, SMA period range and zoom resolution; close versus close25 is an example.

## Failure modes and caveats

- Interpolated crossing is not an executable observed price.
- Third printed formula is not equivalent to the first/second.

## Missing information and implementation boundary

- Actual function expression, parallel/equality handling and defaults absent.

## Data requirements

Required inputs: ohlcv, selected source series.

Repository input-class support: available. Included close/MA examples derive from OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
scaling_factor = (B1 - A1)/(m1 - m2)
```

### E2: mechanism

```text
(1) A1 + m1 × (B1 - A1)/(m1 - m2)
```

### E3: risks, readiness

```text
(3) A2 - m2 × (A2 - B2)/(m1 - m2)
```

### E4: risks

```text
proposed functions use the third calculation.
```

### E5: parameters

```text
close[25]
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/gD1gDOyI-Intersection-Value-Functions/

Publication ID: gD1gDOyI. Source SHA-256: 3ef180cc79227395ee73169ab445ad88260957f91bfa67b03276317e2c307ddb. Raw-description SHA-256: 8a8c127a03490502c150da125917c518495979f94fc740a60fe0dff39dc31843.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
