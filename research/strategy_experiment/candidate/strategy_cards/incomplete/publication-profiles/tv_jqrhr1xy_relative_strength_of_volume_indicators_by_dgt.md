---

id: tv_profile_jqrhr1xy

name: "Relative Strength of Volume Indicators by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Relative Strength of Volume Indicators applies RSI-style momentum analysis to several volume-derived series and displays the result beside ordinary price RSI. It aims to reveal whether price momentum is supported or contradicted by volume-related behavior. The author combines multiple familiar tools rather than proposing a wholly new predictor. MFI is used directly instead of applying RSI to it again, while other selected volume indicators receive the relative-strength transformation. Additional volume displays and bar colors provide participation context for discretionary interpretation."

registry_key: null

runner: null

evaluation: null

---

# Relative Strength of Volume Indicators by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Relative Strength of Volume Indicators applies RSI-style momentum analysis to several volume-derived series and displays the result beside ordinary price RSI. It aims to reveal whether price momentum is supported or contradicted by volume-related behavior. The author combines multiple familiar tools rather than proposing a wholly new predictor. MFI is used directly instead of applying RSI to it again, while other selected volume indicators receive the relative-strength transformation. Additional volume displays and bar colors provide participation context for discretionary interpretation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The selected volume-source transformations and smoothing parameter contract are incomplete.

- The selected volume-source transformations and smoothing parameter contract are incomplete.

## How it works

- Calculate regular RSI and RSI on selected Accumulation/Distribution, EFI, OBV or PVT; use MFI as-is.
- Optionally smooth the transformed series and label its value/name.
- Add selectable volume histogram with average or volume oscillator and volume-based candle coloring.

## Outputs and intended use

- Paired momentum plots, highlighted threshold regions, optional labels and volume visualization support divergence/trend analysis.

## Parameters and stated settings

- Volume-indicator selection, smoothing, labels, volume display mode and bar coloring are adjustable.
- The prose discusses conventional RSI 70/30 extremes and trend ranges 40–90 or 10–60, with 40–50/50–60 support/resistance zones; it does not establish these as enforced defaults.

## Failure modes and caveats

- RSI applied to cumulative volume proxies may have different distributions from price RSI.
- Extreme readings can persist in trends and do not define independent reversal trades.

## Missing information and implementation boundary

- Source lengths, smoothing defaults, exact EFI/PVT implementations, bar-color thresholds and order rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. All named price/volume indicators can be derived from OHLCV; formula/default parity is unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
above 70
```

### E2: parameters

```text
below 30
```

### E3: parameters

```text
40 to 90 range
```

### E4: parameters

```text
40-50 zone
```

### E5: parameters

```text
10 to 60 range
```

### E6: parameters

```text
50-60 zone
```

### E7: mechanism, readiness

```text
Money Flow Index (MFI)
```

### E8: mechanism

```text
(used as it is)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jqrhr1xy_relative_strength_of_volume_indicators_by_dgt](../tv_jqrhr1xy_relative_strength_of_volume_indicators_by_dgt.md)
- [xs_momentum](../../../strategy_research/xs_momentum.md)

## Source

https://www.tradingview.com/script/JQrHr1XY-Relative-Strength-of-Volume-Indicators-by-DGT/

Publication ID: JQrHr1XY. Source SHA-256: 35136719cb3218befb284b0556097ec2aae3b417b40ed7281182729f7fe2dfe1. Raw-description SHA-256: 57542665479764dd837bbd72b63d3e82cca372cba32817d3d950653928e337ca.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
