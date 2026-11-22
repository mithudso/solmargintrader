---

id: tv_profile_o52gurxf

name: "RedK Momentum Bars (RedK Mo_Bars)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Visualize relative momentum between two fast averages while positioning that relationship against a slower trend baseline."

registry_key: null

runner: null

evaluation: null

---

# RedK Momentum Bars (RedK Mo_Bars)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Visualize relative momentum between two fast averages while positioning that relationship against a slower trend baseline.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The structural roles are clear, but the custom average and plotting/color-state calculations are not reproducible from the text.

- RSS Lazy Line equation
- Exact baseline-relative bar equation
- Momentum-change test and numerical lengths

## How it works

- Use a fast price-tracking average and a slightly slower signal average, defaulting the latter to open prices with optional WMA delay. Plot their separation relative to a much slower WMA baseline; default fast/signal types are RSS Lazy Lines.

## Outputs and intended use

- Green/red shows main average above/below signal, and a white bar marks relative-momentum direction changes. Disagreement between bar color and baseline position can reveal chop or convergence/divergence.

## Parameters and stated settings

- Signal length is described as two to three bars longer and baseline roughly five to six times fast length. Actual lengths, delay and exact RSS settings are not disclosed.

## Failure modes and caveats

- Momentum direction differs from price trend direction. The claim that Lazy Lines reduce whipsaws is author experience, not independently verified; correlated smoothed lines can still lag reversals.

## Missing information and implementation boundary

- RSS formula, exact baseline-coordinate transformation, white-bar criterion and default numerical lengths are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; source-code parity and cached historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
2 to 3 bars longer length
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
length 5 to 6 x the fast line
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
if the main MA is below the signal MA, the bar is red
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
a white bar usually shows up when there's a detected change of relative momentum direction
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_o52gurxf_redk_momentum_bars_redk_mo_bars](../tv_o52gurxf_redk_momentum_bars_redk_mo_bars.md)

## Source

https://www.tradingview.com/script/O52gURXf-RedK-Momentum-Bars-RedK-Mo-Bars/

Publication ID: O52gURXf. Source SHA-256: ade3cb5b215e59d7097f8eecad6dee022174b43e3f946745363d3b416bd28843. Raw-description SHA-256: b8aac84f67389c9f29110f35ea4195358aef14d765242eb5f549911d16270304.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
