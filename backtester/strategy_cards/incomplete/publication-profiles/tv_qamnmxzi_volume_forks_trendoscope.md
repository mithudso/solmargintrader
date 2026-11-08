---

id: tv_profile_qamnmxzi

name: "Volume Forks [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Draw automatically detected pitchfork structures with volume-profile levels aligned to the fork direction instead of fixed Fibonacci offsets."

registry_key: null

runner: null

evaluation: null

---

# Volume Forks [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Draw automatically detected pitchfork structures with volume-profile levels aligned to the fork direction instead of fixed Fibonacci offsets.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Recursive swing settings, angled-volume allocation, bin width, geometry selection defaults and trading/invalidation rules are missing.

- Recursive swing settings, angled-volume allocation, bin width, geometry selection defaults and trading/invalidation rules are missing.

## How it works

- Detect ABC structures on a recursive zigzag, choose regular or inside Andrews/Schiff/modified-Schiff handle geometry and distribute volume across angled levels over the ABC interval. Fork lines remain parallel to the chosen handle.

## Outputs and intended use

- Use angled concentrations as trend-relative participation/support-resistance references. Regular types terminate the handle at the BC midpoint; inside types at C.

## Parameters and stated settings

- Scanning controls and profile-line settings exist, but numerical defaults are in an external image. The author advises reducing forks per formation if the stated five-hundred-line limit causes incomplete profiles.

## Failure modes and caveats

- Developing zigzags can alter anchors and hence every angled bin. A pitchfork plus volume concentration does not establish future price containment or actual resting orders.

## Missing information and implementation boundary

- Recursive swing settings, angled-volume allocation, bin width, geometry selection defaults and trading/invalidation rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary OHLCV supports the disclosed calculation class; this does not establish source-code parity or verified historical coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Instead of drawing forks based on fib levels, volume distribution over ABC of pitchfork is calculated and drawn in the direction of the handle.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Here, end of the handle is always fixed and it will be the mid point of B and C.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Here, C will act as end of the handle
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
due to pine limitations of 500 lines
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_pitchfork](../../tv_method_pitchfork.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_qamnmxzi_volume_forks_trendoscope](../tv_qamnmxzi_volume_forks_trendoscope.md)

## Source

https://www.tradingview.com/script/qAMnMxZI-Volume-Forks-Trendoscope/

Publication ID: qAMnMxZI. Source SHA-256: 5f80e1e0e640a4a555af79a1b88fa516d5b491dffd48ddacf80e4b09434eff79. Raw-description SHA-256: f8c3a002bf7cb5282c0e3c6dd681d875efd6ff7cf89afd352f137585dd05c18e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
