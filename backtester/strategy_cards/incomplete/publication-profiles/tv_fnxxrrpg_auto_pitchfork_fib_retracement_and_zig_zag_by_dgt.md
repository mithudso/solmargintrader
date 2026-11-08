---

id: tv_profile_fnxxrrpg

name: "Auto Pitchfork, Fib Retracement and Zig Zag by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Auto Pitchfork, Fib Retracement and Zig Zag automates three related chart-annotation tools around detected turning points. The main goal is identifying possible support/resistance with a pitchfork placed at prior trend endpoints. Fibonacci retracement and zigzag overlays share the pivot framework. The source gives conventional discretionary use—buying near support and selling near resistance—while also warning against relying on the indicator alone. The chosen pitchfork variant changes geometry, so its suggested regime suitability should be treated as an author guideline rather than a validated selection rule."

registry_key: null

runner: null

evaluation: null

---

# Auto Pitchfork, Fib Retracement and Zig Zag by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Auto Pitchfork, Fib Retracement and Zig Zag automates three related chart-annotation tools around detected turning points. The main goal is identifying possible support/resistance with a pitchfork placed at prior trend endpoints. Fibonacci retracement and zigzag overlays share the pivot framework. The source gives conventional discretionary use—buying near support and selling near resistance—while also warning against relying on the indicator alone. The chosen pitchfork variant changes geometry, so its suggested regime suitability should be treated as an author guideline rather than a validated selection rule.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pivot selection and pitchfork variant geometry are unspecified.

- Pivot selection and pitchfork variant geometry are unspecified.

## How it works

- Detect pivots using Deviation and Depth thresholds and construct a three-point pitchfork.
- Offer Andrews, Schiff and Modified variants, with customizable extra levels.
- Adapt built-in Fibonacci retracement and zigzag logic to the same study.

## Outputs and intended use

- Automatic pitchfork, retracement levels and zigzag support visual support/resistance analysis; pitchfork-level alerts can notify interactions.

## Parameters and stated settings

- Deviation, Depth, pitchfork type, custom levels and line styling are configurable.
- The author favors Andrews in strong trends and Schiff/Modified in corrective or sideways conditions; defaults are not given.

## Failure modes and caveats

- Unconfirmed zigzag pivots can change and redraw derived geometry.
- Near-line entries lack precise tolerance, confirmation or risk controls.

## Missing information and implementation boundary

- Pivot confirmation, variant equations, Fibonacci/custom ratios, alert predicates, defaults and stops/targets are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Detected price pivots and derived geometry are OHLCV-based.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
three points at the end of previous trends
```

### E2: parameters

```text
“Deviation” and “Depth”
```

### E3: parameters

```text
Andrews' Pitchfork (Original), Schiff and Modified Pitchfork
```

### E4: outputs_and_use

```text
ALERTs[/b] for the Pitchfork Levels
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fnxxrrpg_auto_pitchfork_fib_retracement_and_zig_zag_by_dgt](../tv_fnxxrrpg_auto_pitchfork_fib_retracement_and_zig_zag_by_dgt.md)
- [tv_method_pitchfork](../../../strategy_research/tv_method_pitchfork.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/FnxXRrPG-Auto-Pitchfork-Fib-Retracement-and-Zig-Zag-by-DGT/

Publication ID: FnxXRrPG. Source SHA-256: b587df2ff2ca5e8f68fdeb085716e3b07711d1241a4cbab906b80f1588fb5e00. Raw-description SHA-256: 9c5bd91e99c22e58042bd670bf9134f90b7f11a905bb73d0c2e00e86c40bd787.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
