---

id: tv_profile_dksawola

name: "Next Pivot Projection [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Project likely price/time locations of forthcoming zigzag pivots from historical swing-transition statistics."

registry_key: null

runner: null

evaluation: null

---

# Next Pivot Projection [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Project likely price/time locations of forthcoming zigzag pivots from historical swing-transition statistics.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Transition conditioning, sample selection, probability/ratio formulas, bar-time estimation and outlier treatment are absent. The lower-cloud color explanation repeats pivot high wording and is ambiguous.

- Transition conditioning, sample selection, probability/ratio formulas, bar-time estimation and outlier treatment are absent. The lower-cloud color explanation repeats pivot high wording and is ambiguous.

## How it works

- Collect occurrence counts, average ratios and average bar spacing for HH, HL, LH and LL transitions. Project the current unconfirmed pivot from the preceding two confirmed pivots, and the following pivot using the latest two pivots including the developing one.

## Outputs and intended use

- Inspect projection labels/tooltips and historical average-range clouds. Upper/lower clouds compare typical higher/lower high/low outcomes, with ratio-dependent colors.

## Parameters and stated settings

- The source describes ratio comparisons to one for cloud colors but gives no zigzag length, sample window or default settings.

## Failure modes and caveats

- The next-pivot forecast can repaint when the latest unconfirmed pivot moves. The source says the current-pivot projection remains fixed relative to its confirmed anchors, but code behavior is not independently verified.

## Missing information and implementation boundary

- Transition conditioning, sample selection, probability/ratio formulas, bar-time estimation and outlier treatment are absent. The lower-cloud color explanation repeats pivot high wording and is ambiguous.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class. Code parity, complete history and forward performance remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
this script we try to project next 2 pivots (including one unconfirmed pivot)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
projection of the unconfirmed pivot will not change as it will be based on previous two pivots - both of which are confirmed.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
these projections can potentially repaint based on the last pivot repaint.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Cloud color is green if average ratio of pivot high is more than 1.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dksawola_next_pivot_projection_trendoscope](../tv_dksawola_next_pivot_projection_trendoscope.md)

## Source

https://www.tradingview.com/script/dkSaWOLA-Next-Pivot-Projection-Trendoscope/

Publication ID: dkSaWOLA. Source SHA-256: b75b9b516636861eadf6851e72a68f9639f5239bc44d9a1489614607d781c584. Raw-description SHA-256: cb36226d21bef3d17e085a17683706864383f0f2561270bedf7783dd0c4686a4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
