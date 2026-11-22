---

id: tv_profile_gdgxyl8b

name: "Recursive Reversal Chart Patterns [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Recursive Reversal Chart Patterns scans nested zigzag structures for common reversal formations. It aims to find both smaller and larger structures and optionally require supporting indicator divergence. The categories include double/triple tops and bottoms, cup variants and head-and-shoulders variants. The description is architectural rather than algorithmic: recognition resides in referenced libraries and the settings are largely screenshot-only. It warns that the workload can time out, so a missing pattern may reflect computational limits rather than absence of a setup."

registry_key: null

runner: null

evaluation: null

---

# Recursive Reversal Chart Patterns [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Recursive Reversal Chart Patterns scans nested zigzag structures for common reversal formations. It aims to find both smaller and larger structures and optionally require supporting indicator divergence. The categories include double/triple tops and bottoms, cup variants and head-and-shoulders variants. The description is architectural rather than algorithmic: recognition resides in referenced libraries and the settings are largely screenshot-only. It warns that the workload can time out, so a missing pattern may reflect computational limits rather than absence of a setup.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core recursive-zigzag and pattern/divergence recognition rules are not supplied.

## How it works

- Build recursive zigzags and pass them to reversal-pattern recognition libraries.
- Optionally filter patterns with internal/external indicator divergence.

## Outputs and intended use

- Bullish/bearish pattern drawings support discretionary reversal research.

## Parameters and stated settings

- Depth, pattern selection, scanner and secondary indicators are controls without reproduced numeric defaults.
- Reducing depth or limiting selected patterns mitigates timeouts.

## Failure modes and caveats

- Nested patterns are correlated and can update with pivots.
- Divergence filtering is explicitly experimental and difficult to verify manually.

## Missing information and implementation boundary

- Zigzag, pattern ratios/tolerances, divergence tests, confirmation and defaults are absent.

## Data requirements

Required inputs: ohlcv, external indicator series when selected.

Repository input-class support: available. Core pattern work is candle-price based; optional external series need their own data contract.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
built on recursive zigzags.
```

### E2: parameters

```text
decrease the value of depth parameter
```

### E3: risks

```text
purely experimental.
```

### E4: mechanism

```text
patterns are shown only if the divergence data is inline.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gdgxyl8b_recursive_reversal_chart_patterns_trendoscope](../tv_gdgxyl8b_recursive_reversal_chart_patterns_trendoscope.md)
- [tv_method_cup_handle](../tv_method_cup_handle.md)
- [tv_method_double_top_bottom](../tv_method_double_top_bottom.md)
- [tv_method_head_shoulders](../../../strategy_research/tv_method_head_shoulders.md)
- [tv_method_pitchfork](../../../strategy_research/tv_method_pitchfork.md)
- [tv_method_triple_top_bottom](../../../strategy_research/tv_method_triple_top_bottom.md)

## Source

https://www.tradingview.com/script/gdgXyl8b-Recursive-Reversal-Chart-Patterns-Trendoscope/

Publication ID: gdgXyl8b. Source SHA-256: 2db727446a6ab65e13b6bad0f1938de8811b1d26d403d9589d4dc56fe5b01e99. Raw-description SHA-256: 9b3821c347b9446c0124183f0e1b4f92f9eb764f7d05ea6dbc7f689a913aba84.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
