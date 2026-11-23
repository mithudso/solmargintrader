---

id: tv_profile_bv2arqnd

name: "Cup Finder"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Find cup-shaped price formations by measuring how much historical price action fits within a proposed circular channel."

registry_key: null

runner: null

evaluation: null

---

# Cup Finder

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Find cup-shaped price formations by measuring how much historical price action fits within a proposed circular channel.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Candidate-circle generation, containment boundaries, breakout timing, duplicate handling and trade risk rules are absent.

- Candidate-circle generation, containment boundaries, breakout timing, duplicate handling and trade risk rules are absent.

## How it works

- Construct a candidate cup circle/channel and count bars contained within it. Display the cup when the contained-bar share meets a user threshold; optionally check a breakout using closes or highs/lows.

## Outputs and intended use

- Inspect plotted cups, their channels and labels as experimental pattern candidates. The author explicitly distinguishes this work from a future cup-and-handle script.

## Parameters and stated settings

- Maximum cup search length, channel width, containment rate, breakout source, channel visibility and old-pattern styling are configurable. Channel width defaults to five percent of the high/low span over the last 300 bars.

## Failure modes and caveats

- Flexible circular fits can select attractive historical shapes by chance. Containment and breakout recognition may occur after most of the apparent formation is visible.

## Missing information and implementation boundary

- Candidate-circle generation, containment boundaries, breakout timing, duplicate handling and trade risk rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the disclosed input class; source code and historical data parity have not been validated.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
if included bars is equal or greater than the value you set then it shows the cup.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
"Channel Width of the Cup"[/i] : Tate by the channel width of highest/lowest levels in last 300 bars, by default it's 5%
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
in the future if I have time I will try to write a script for Cup&Handle
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bv2arqnd_cup_finder](../tv_bv2arqnd_cup_finder.md)
- [tv_method_cup_handle](../tv_method_cup_handle.md)

## Source

https://www.tradingview.com/script/bv2ARQND-Cup-Finder/

Publication ID: bv2ARQND. Source SHA-256: 9f2540bed6fc49030f11733572f52a89074dc095a24eec1d8fc455fb12aa9884. Raw-description SHA-256: 84991e927ce8545faa1102cfcfbc33d2583107303de9568fdcc1ad236d445015.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
