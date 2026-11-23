---

id: tv_profile_pkhv9soh

name: "Auto Fib Speed Resistance Fans by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Auto Fib Speed Resistance Fans draws time/price fan structures between alternating price extremes. The author intends the rays and grids to help assess trend correction, slope and potential support/resistance. Automatic pivot selection removes some manual drawing work, while historical fans show earlier structures. The source discusses Fibonacci levels as possible areas of reaction, but gives no evidence that those levels deliver a repeatable prediction."

registry_key: null

runner: null

evaluation: null

---

# Auto Fib Speed Resistance Fans by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Auto Fib Speed Resistance Fans draws time/price fan structures between alternating price extremes. The author intends the rays and grids to help assess trend correction, slope and potential support/resistance. Automatic pivot selection removes some manual drawing work, while historical fans show earlier structures. The source discusses Fibonacci levels as possible areas of reaction, but gives no evidence that those levels deliver a repeatable prediction.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core rules remain unresolved.

- Exact pivot selection and fan projection settings/equations are absent.

## How it works

- Choose a trough and opposing peak or the inverse through a zigzag derived from the built-in auto-retracement approach.
- Project sequential fan lines from percentages of the anchor interval in price and time; extended price grids also form retracement levels.

## Outputs and intended use

- View current or historical fans and set alerts at speed/resistance lines.
- Customize individual line levels and appearance; use the drawing within a broader trading process.

## Parameters and stated settings

- Deviation and Depth adjust pivot thresholds. A 61.8-percent level is discussed as a common reference.
- Line defaults are said to match the platform fan tool but are not enumerated.

## Failure modes and caveats

- Automatic pivot revisions can relocate the fan.
- A ratio level is a geometric reference, not measured probability of a reversal.

## Missing information and implementation boundary

- Pivot deviation calculation, depth defaults, full ratio set, projection equations and alert crossing rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the default input class; this does not establish source-code parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
61.8-percent level
```

### E2: parameters

```text
Pivot threshold can be adjusted via “Deviation” and “Depth” input options
```

### E3: mechanism

```text
time/price percentages of the distance between the beginning and the end of the trend line.
```

### E4: outputs_and_use

```text
Historical Fans option
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_pkhv9soh_auto_fib_speed_resistance_fans_by_dgt](../tv_pkhv9soh_auto_fib_speed_resistance_fans_by_dgt.md)

## Source

https://www.tradingview.com/script/pKhv9SoH-Auto-Fib-Speed-Resistance-Fans-by-DGT/

Publication ID: pKhv9SoH. Source SHA-256: 5db4debc3561f7b4d8c95b4b9402685175fef6a289907a8302ad942a7b1ab92d. Raw-description SHA-256: b47547d3e75fe6b4612d5eb9ddf405a04468c06f0073f0c111ac14ba36b37455.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
