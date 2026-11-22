---

id: tv_profile_hfizhwba

name: "[RS]Donchian HL Width - Cycle Information"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Donchian HL Width Cycle Information is an experimental attempt to characterize cyclical new peaks using percentage widths of Donchian channels. The financial idea supported by the source is studying cycles through changing channel breadth rather than using a plain price oscillator. The complete description is extremely short and does not establish which peaks are measured, whether they refer to width or price, or how the cycle information is displayed. A faithful explanation therefore preserves the research objective while leaving the actual detection algorithm unknown."

registry_key: null

runner: null

evaluation: null

---

# [RS]Donchian HL Width - Cycle Information

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Donchian HL Width Cycle Information is an experimental attempt to characterize cyclical new peaks using percentage widths of Donchian channels. The financial idea supported by the source is studying cycles through changing channel breadth rather than using a plain price oscillator. The complete description is extremely short and does not establish which peaks are measured, whether they refer to width or price, or how the cycle information is displayed. A faithful explanation therefore preserves the research objective while leaving the actual detection algorithm unknown.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The cyclical-peak calculation from Donchian width is not specified.

- The cyclical-peak calculation from Donchian width is not specified.

## How it works

- Use Donchian channel percentage widths as input to an unspecified cyclical-new-peak analysis.

## Outputs and intended use

- Experimental cycle information is produced, but the source does not describe plot states or intended decisions.

## Parameters and stated settings

- No channel lengths, percentage denominator or default settings are supplied.

## Failure modes and caveats

- Channel expansion can reflect a single outlier and need not imply a stable periodic cycle.
- Experimental status and missing detection rules prevent reproducible signal interpretation.

## Missing information and implementation boundary

- Channel definitions, peak detection, cycle estimation, output scale, confirmation and trading rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Donchian range widths can be computed from OHLCV prices; the undisclosed cycle method is an algorithm gap.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, risks, readiness

```text
Experimental:
some information on cyclical new peaks using Donchian Channel % Widths.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hfizhwba_rs_donchian_hl_width_cycle_information](../tv_hfizhwba_rs_donchian_hl_width_cycle_information.md)

## Source

https://www.tradingview.com/script/HfIZHwba-RS-Donchian-HL-Width-Cycle-Information/

Publication ID: HfIZHwba. Source SHA-256: dc845a11260f1efa55bb8b90a4575472972e77f86943e3155cb38e26c6d07a70. Raw-description SHA-256: 0e82bdbc341ac47f40b464096ac7aa73e423542f9db320182751e31385031bc8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
