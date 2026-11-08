---

id: tv_profile_hv8ghojp

name: "Recursive Auto-Pitchfork [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Automatically draw pitchforks across a hierarchy of zigzag scales while demonstrating reusable financial drawing objects."

registry_key: null

runner: null

evaluation: null

---

# Recursive Auto-Pitchfork [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Automatically draw pitchforks across a hierarchy of zigzag scales while demonstrating reusable financial drawing objects.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The hierarchy outline is clear, but its pivot reduction and fork selection rules are not disclosed.

- Base/recursive zigzag calculation
- Retracement acceptance and fork geometry/defaults

## How it works

- Build a base zigzag from length/depth, recursively derive coarser zigzags and stop when four or fewer pivots remain or no reduction occurs. At each level inspect the latest three pivots and draw pitchforks conditioned on retracement ratio.

## Outputs and intended use

- Use forks as multiscale geometry for trend/support-resistance analysis. The description also explains separation of type definitions from methods so library updates can preserve dependency types.

## Parameters and stated settings

- Base zigzag length/depth and fork settings are mentioned, but their defaults and retracement criteria appear only in an external screenshot.

## Failure modes and caveats

- Developing swing anchors can change projected forks. Multiple scales can create dense correlated drawings; a library architecture does not establish the validity of the financial geometry.

## Missing information and implementation boundary

- Base and recursive pivot-reduction rules, permitted retracements, fork variants and object-retirement logic are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described input class; source-code parity and complete history remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
until we are left with 4 or less pivots or when no further reduction is possible
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
check the last 3 pivots and draw pitchfork based on the retracement ratio.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hv8ghojp_recursive_auto_pitchfork_trendoscope](../tv_hv8ghojp_recursive_auto_pitchfork_trendoscope.md)
- [tv_method_pitchfork](../../../strategy_research/tv_method_pitchfork.md)

## Source

https://www.tradingview.com/script/hv8ghOJp-Recursive-Auto-Pitchfork-Trendoscope/

Publication ID: hv8ghOJp. Source SHA-256: 9093173a0e43c1d793cf7baae9dce80e0280e9bc35ceffe6a357b7574bc5c3e4. Raw-description SHA-256: 6d3f4c201640855d049d76474ef45f3356d2d74202790df454aaeae96312610f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
