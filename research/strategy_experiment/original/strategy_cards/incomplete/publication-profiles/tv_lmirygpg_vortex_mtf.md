---

id: tv_profile_lmirygpg

name: "Vortex MTF"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Vortex MTF presents the positive and negative Vortex components from a selected timeframe without requiring the user to change the chart timeframe. The components compare directional movement across adjacent bars with accumulated true range. Their relative strength is intended to help identify directional changes and confirm an existing trend. The author discusses comparing larger and smaller timeframes and lengthening the calculation window to reduce frequent crossings, but these are discretionary analysis suggestions rather than a complete trading system."

registry_key: null

runner: null

evaluation: null

---

# Vortex MTF

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Vortex MTF presents the positive and negative Vortex components from a selected timeframe without requiring the user to change the chart timeframe. The components compare directional movement across adjacent bars with accumulated true range. Their relative strength is intended to help identify directional changes and confirm an existing trend. The author discusses comparing larger and smaller timeframes and lengthening the calculation window to reduce frequent crossings, but these are discretionary analysis suggestions rather than a complete trading system.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The true-range differences lack explicit absolute-value treatment, and MTF sampling and confirmation are unspecified.

## How it works

- Positive movement is the absolute difference between the current high and previous low; negative movement is the absolute difference between current low and previous high.
- Each movement sum is divided by the true-range sum over the chosen window.
- The true-range prose lists three differences but does not explicitly apply absolute values to its previous-close differences, leaving an implementation ambiguity.

## Outputs and intended use

- Compare VI+ and VI- relationships and crossings as trend or reversal context.
- Request a separate calculation timeframe while retaining the current chart view.

## Parameters and stated settings

- The prose describes 14 to 30 days as common and compares 25 periods with 14 as a smoothing example.

## Failure modes and caveats

- Longer windows can suppress crossings while delaying response.
- Unconfirmed higher-timeframe values may change before that timeframe closes unless a confirmation policy is implemented.

## Missing information and implementation boundary

- The signed true-range wording and higher-timeframe sampling/confirmation policy need clarification; the selected defaults are not stated.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Vortex components derive from historical high, low and close series; timeframe aggregation is within that data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
VM+ = Absolute value of current high minus prior low
VM- = Absolute value of current low minus prior high
```

### E2: mechanism

```text
SUM VMn+/SUM TRn = VIn+
SUM VMn-/SUM TRn = VIn−
```

### E3: mechanism, missing_information

```text
Current high minus current low
Current high minus previous close
Current low minus previous close
```

### E4: parameters

```text
between 14 and 30 days is common
```

### E5: parameters

```text
using 25 periods instead of 14
```

### E6: purpose, outputs_and_use

```text
see the Vortex indicator values for a specific time period without changing the graph time period.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lmirygpg_vortex_mtf](../tv_lmirygpg_vortex_mtf.md)

## Source

https://www.tradingview.com/script/lMirygPG-Vortex-MTF/

Publication ID: lMirygPG. Source SHA-256: 87fc51042c3185b3f99c77ea0c8ed8dc1388f68a8a40a83b429d3e9ac3d83720. Raw-description SHA-256: 67df9f6c1f46edfff2d73e4096cd5fa1885410e8f3dadd1bff89a3322956cf44.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
