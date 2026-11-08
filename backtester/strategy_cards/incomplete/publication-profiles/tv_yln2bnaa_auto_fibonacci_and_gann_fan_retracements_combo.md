---

id: tv_profile_yln2bnaa

name: "Auto Fibonacci and Gann Fan/Retracements Combo"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Auto Fibonacci and Gann Combo automatically places retracements and fans from detected local extremes. It aims to supply potential support/resistance geometry without manually anchoring every set. A new opposite extreme is needed to confirm the preceding high/low, so automatic anchors inherently arrive late. The Gann component also tries to infer price/time scaling from successive peaks/troughs. That scaling matters more than a screen’s apparent angle; the description’s angle claims are theoretical context rather than proof that levels predict price reactions."

registry_key: null

runner: null

evaluation: null

---

# Auto Fibonacci and Gann Fan/Retracements Combo

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Auto Fibonacci and Gann Combo automatically places retracements and fans from detected local extremes. It aims to supply potential support/resistance geometry without manually anchoring every set. A new opposite extreme is needed to confirm the preceding high/low, so automatic anchors inherently arrive late. The Gann component also tries to infer price/time scaling from successive peaks/troughs. That scaling matters more than a screen’s apparent angle; the description’s angle claims are theoretical context rather than proof that levels predict price reactions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Pivot-search and full Gann scale/line equations are not supplied.

## How it works

- Detect a local high after a lower high follows an intervening low, with inverse logic for local lows.
- Build Fibonacci/Gann retracement and fan sets from those extrema.
- Estimate a scale from price differences over elapsed time and reposition fan labels through line equations.

## Outputs and intended use

- Extrema markers and configurable multiple fan/retracement sets support discretionary geometric level analysis.

## Parameters and stated settings

- Each set has seven lines. Defaults show one Fibonacci fan, one Gann fan, one Fibonacci retracement set and no Gann retracements.
- Listed Fibonacci levels include 23.6/38.2/50/61.8/78.6%; Gann discussion includes halving-based retracements and time/price ratios.

## Failure modes and caveats

- Confirmed extrema are delayed and may look hindsight-selected.
- Gann scale and ratio conventions are not fully specified, limiting cross-chart consistency.

## Missing information and implementation boundary

- Exact pivot candidate search, complete seven-line ratios, Gann scaling equation/defaults and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price extrema, elapsed bars and derived geometry are OHLCV-based.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
consists of 7 lines
```

### E2: parameters

```text
23.6%, 38.2%, 61.8%, and 78.6%
```

### E3: parameters

```text
50% is also used
```

### E4: parameters

```text
1 Fibonacci fan, 1 Gann fan, 1 set of Fibonacci retracements and no Gann retracements
```

### E5: risks, readiness

```text
won't be found until the next high/low point is formed.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_gann](../tv_method_gann.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_yln2bnaa_auto_fibonacci_and_gann_fan_retracements_combo](../tv_yln2bnaa_auto_fibonacci_and_gann_fan_retracements_combo.md)

## Source

https://www.tradingview.com/script/YLn2bNaa-Auto-Fibonacci-and-Gann-Fan-Retracements-Combo/

Publication ID: YLn2bNaa. Source SHA-256: f13965f3e0d73331c143c23d7f24226eb3d94e4ac06f749b67baf3e0438821b1. Raw-description SHA-256: 95f100c7843d0855aa65f15d41243ba0488c1ff3460dc89d3be17eab73993a03.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
