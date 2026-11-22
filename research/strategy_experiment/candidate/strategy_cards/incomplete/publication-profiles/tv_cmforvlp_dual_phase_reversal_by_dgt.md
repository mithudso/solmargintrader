---

id: tv_profile_cmforvlp

name: "Dual-Phase Reversal by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Dual-Phase Reversal separates initial momentum exhaustion from a later terminal exhaustion sequence, then adds structural levels and volume context. It aims to describe evolving overextension without treating every completed count as an immediate reversal. A change in the four-bar close relationship initiates the first phase; qualification of that setup is distinct from eligibility for the terminal phase. Range pivots and pressure readings provide supporting context. The source explicitly frames the output as contextual, and it never supplies the full sequential predicates required to reproduce the phases."

registry_key: null

runner: null

evaluation: null

---

# Dual-Phase Reversal by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dual-Phase Reversal separates initial momentum exhaustion from a later terminal exhaustion sequence, then adds structural levels and volume context. It aims to describe evolving overextension without treating every completed count as an immediate reversal. A change in the four-bar close relationship initiates the first phase; qualification of that setup is distinct from eligibility for the terminal phase. Range pivots and pressure readings provide supporting context. The source explicitly frames the output as contextual, and it never supplies the full sequential predicates required to reproduce the phases.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core phase progression/qualification and level/pressure equations are undisclosed.

## How it works

- Start momentum phase only on a shift in four-bar close direction and progress toward completion.
- Begin independent terminal counting after momentum completion; derive phase support/resistance, invalidation and target references.
- Add manual/automatic higher-range pivots, normalized volume pressure and relative-volume candle highlights.

## Outputs and intended use

- Sequence marks, phase levels, range pivots, pressure oscillator/signal/histogram and dashboard plus event alerts support exhaustion analysis.

## Parameters and stated settings

- Momentum completes at nine; terminal dashboard counts toward thirteen.
- Pressure scale 0–100. Range choices include 1H,4H,daily,weekly,monthly,quarterly,yearly.
- Thresholds, visibility and volume averages are configurable but numeric defaults absent.

## Failure modes and caveats

- Developing pivots/pressure update before close.
- Counts do not guarantee a turn, and omitted qualification/invalidation rules matter materially.

## Missing information and implementation boundary

- Sequential conditions, Q criterion, terminal validation, level/target equations, pivot and pressure formulas are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. All disclosed sequence, range and volume inputs use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters

```text
four-bar close relationship
```

### E2: parameters

```text
completes count 9
```

### E3: parameters

```text
step count out of 13
```

### E4: parameters

```text
0–100
```

### E5: parameters

```text
1H, 4H, Daily, Weekly, Monthly, Quarterly, and Yearly
```

### E6: readiness

```text
separate set of price conditions
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cmforvlp_dual_phase_reversal_by_dgt](../tv_cmforvlp_dual_phase_reversal_by_dgt.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/cmFOrVlp-Dual-Phase-Reversal-by-DGT/

Publication ID: cmFOrVlp. Source SHA-256: a4cad16abeb6b48035867cab504cdf4c7e82b7fa7fb552c50bb6cd7e4fa90bbc. Raw-description SHA-256: b7bd9f5b8868be01ac3bbbd5bef221ec4fa3b53496f5c9c20413ac75e76f1439.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
