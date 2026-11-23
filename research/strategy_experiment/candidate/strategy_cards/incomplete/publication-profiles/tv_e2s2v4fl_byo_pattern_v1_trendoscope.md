---

id: tv_profile_e2s2v4fl

name: "BYO Pattern V1 [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Let a user define ratio-based geometric patterns and automatically search them across recent zigzag structures."

registry_key: null

runner: null

evaluation: null

---

# BYO Pattern V1 [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Let a user define ratio-based geometric patterns and automatically search them across recent zigzag structures.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The custom ratio validator is well described, but its automatic swing input and PRZ computation are not defined enough to reproduce the full indicator.

- Base/recursive zigzag algorithm
- Default pattern ratios
- PRZ construction and CBE/CDE clarification

## How it works

- Extract five/six pivots, compute enabled leg retracement/extension ratios, validate each exact-value tolerance or range and accept only if all enabled tests pass and the pivot set is new. Build a PRZ from enabled terminal ratios and optionally use log differences.

## Outputs and intended use

- Draw named patterns, labels, ratio annotations and a live configuration/count table. The source explicitly says it does not generate buy/sell signals or manage trades.

## Parameters and stated settings

- Default pattern is Three Drives. Select pivot count, zigzag length/depth, forming bars, error percent, log mode and XAB/ABC/BCD/CDE/XAD/XCD/ABE/ADE conditions. Five-pivot scans require a terminal BCD/XAD/XCD rule; six require CDE/ABE/ADE.

## Failure modes and caveats

- Forming-bar inclusion and developing zigzags can change matches. More recursive levels can slow execution or cause errors; arbitrary ratio fitting can overfit historical shapes.

## Missing information and implementation boundary

- Base/recursive zigzag calculation, default Three Drives numbers, PRZ intersection/union rule and tolerance boundary behavior are absent. One settings line says CBE rather than CDE, an unresolved typo.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the input class; code behavior and cache coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Default configuration is set to the classic Three Drives pattern
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
If all enabled ratios pass validation
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
5 pivot pattern should at least have one of the ratio enabled among BCD, XAD or XCD.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
6 pivot pattern should at least have one of the ratio enabled among CDE, ABE and ADE
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
CBE, ABE, and ADE ratios
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_e2s2v4fl_byo_pattern_v1_trendoscope](../tv_e2s2v4fl_byo_pattern_v1_trendoscope.md)
- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)

## Source

https://www.tradingview.com/script/e2S2v4fl-BYO-Pattern-V1-Trendoscope/

Publication ID: e2S2v4fl. Source SHA-256: 8f332718f13335a376c8e9f4ecac26b9312e7cad2d92d5fabb8f861e0f548136. Raw-description SHA-256: 4b12d1a734d71a14de554ccb57db0f5a3f0fb1d4e5dcb38c4a2c8a905c0912e6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
