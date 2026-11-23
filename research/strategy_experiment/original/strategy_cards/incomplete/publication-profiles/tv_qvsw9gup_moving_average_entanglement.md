---

id: tv_profile_qvsw9gup

name: "Moving Average Entanglement"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Moving Average Entanglement uses the separation between moving averages relative to ATR to distinguish meaningful expansion from a small dead-zone movement. It is intended to assist entry/exit decisions by filtering weak gaps, with optional smoothing and standard-deviation context. The description explains breakout confirmation but does not provide complete long-versus-short or exit mechanics."

registry_key: null

runner: null

evaluation: null

---

# Moving Average Entanglement

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Moving Average Entanglement uses the separation between moving averages relative to ATR to distinguish meaningful expansion from a small dead-zone movement. It is intended to assist entry/exit decisions by filtering weak gaps, with optional smoothing and standard-deviation context. The description explains breakout confirmation but does not provide complete long-versus-short or exit mechanics.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Signed versus absolute gap and dead-zone/deviation construction are not defined.

- Signed versus absolute gap and dead-zone/deviation construction are not defined.

## How it works

- Measure the gap between moving averages and standardize it to ATR.
- Compare the histogram with a red dead-zone line, optionally use its moving average as another filter and show a standardized-distance line in deviation mode.

## Outputs and intended use

- A histogram above the red line is the author’s breakout confirmation; the dashed histogram average and optional deviation line provide secondary context.

## Parameters and stated settings

- Dead-zone ATR percentage and mode/filter settings are described without numeric defaults, moving-average types or lengths.

## Failure modes and caveats

- Analytical: a magnitude filter may confirm a move after much of it occurs and ATR regime changes alter the normalization.

## Missing information and implementation boundary

- Signed versus absolute gap, dead-zone adaptation, deviation window and entry/exit direction rules are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
gap in moving averages standardized to the average true range
```

### E2: outputs_and_use, readiness

```text
When the histogram is above the red line, it confirms a breakout move.
```

### E3: mechanism, readiness

```text
a moving average of the histogram.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qvsw9gup_moving_average_entanglement](../tv_qvsw9gup_moving_average_entanglement.md)

## Source

https://www.tradingview.com/script/QVsW9gUP-Moving-Average-Entanglement/

Publication ID: QVsW9gUP. Source SHA-256: 9c225b80f61ae97026aef249726745e74a815fe71fbc7b03e249eef5e844a765. Raw-description SHA-256: a79b4044135a3366aee975f91aa808ab8a5d27728e8846ea26797c598438a848.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
