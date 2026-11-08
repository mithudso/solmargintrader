---

id: tv_profile_17xrxgad

name: "Auto PitchFan, Fib Extension/Retracement and ZigZag by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Automate a shared swing-based framework for pitchfan rays, Fibonacci retracement/extension levels and connecting zigzag structure."

registry_key: null

runner: null

evaluation: null

---

# Auto PitchFan, Fib Extension/Retracement and ZigZag by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Automate a shared swing-based framework for pitchfan rays, Fibonacci retracement/extension levels and connecting zigzag structure.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core swing and pitchfan/extension anchoring remain insufficiently defined despite the feature-level workflow.

- Pivot/deviation/depth algorithm
- Pitchfan ray geometry
- Extension anchor/level defaults

## How it works

- Detect reversals exceeding a deviation threshold subject to a depth requirement, connect the pivots and use them as geometric anchors. Draw Fibonacci-inclined rays and horizontal retracement/extension references, optionally retaining historical structures.

## Outputs and intended use

- Use ray/level labels and per-level alerts to review possible reaction areas. The author recommends applying the fan after an initial impulse and visible correction, and distinguishes extension targets after pullbacks from retracement regions.

## Parameters and stated settings

- Deviation, depth and historical visibility are common controls. Listed conventional retracement coefficients are23.6%,38.2%,50%,61.8%,100%; actual pitchfan/extension defaults are not enumerated.

## Failure modes and caveats

- Developing zigzag anchors can revise levels. Fibonacci confluence is a geometric hypothesis, not a measured probability that price bounces or continues.

## Missing information and implementation boundary

- Deviation units, pivot confirmation, ray coordinate/coefficients, extension anchor selection and alert breach conditions are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the stated input class; missing equations are specification gaps and do not mean missing raw OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
percentage greater than a Deviation variable.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Depth[/b], affects the minimum number of bars
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
23.6%, 38.2%, 50%, 61.8%, and 100%
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Ability to set [b]ALERTs[/b] for each PitchFan Ray Level
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_17xrxgad_auto_pitchfan_fib_extension_retracement_and_zigzag_by_dgt](../tv_17xrxgad_auto_pitchfan_fib_extension_retracement_and_zigzag_by_dgt.md)
- [tv_method_fib_extensions](../../../strategy_research/tv_method_fib_extensions.md)
- [tv_method_linear_regression_channel](../tv_method_linear_regression_channel.md)
- [tv_method_pitchfork](../../../strategy_research/tv_method_pitchfork.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/17xrXGad-Auto-PitchFan-Fib-Extension-Retracement-and-ZigZag-by-DGT/

Publication ID: 17xrXGad. Source SHA-256: 2ebe65e87dbb0dff041a03f6d47471da59fadc3a865d27da6126229fdd522ca5. Raw-description SHA-256: 89e94a6b08b4a3f31401ccb4915c822fbe07a44fbd59abeeaeb1998a2402f5ea.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
