---

id: tv_profile_eos9u1qm

name: "Fair value bands / Flowly Indicators"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Fair Value Bands estimates typical price excursions from a selected smooth basis using pivot deviations rather than continuously varying standard deviation. It aims to provide steadier normal/extreme zones and separate minor crosses from meaningful trend-state changes. It also records time and relative volume in band-defined lots, enabling descriptive comparison of how activity varies with distance from the basis."

registry_key: null

runner: null

evaluation: null

---

# Fair value bands / Flowly Indicators

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fair Value Bands estimates typical price excursions from a selected smooth basis using pivot deviations rather than continuously varying standard deviation. It aims to provide steadier normal/extreme zones and separate minor crosses from meaningful trend-state changes. It also records time and relative volume in band-defined lots, enabling descriptive comparison of how activity varies with distance from the basis.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pivot rules, deviation sample window, median updates, threshold deviation population and exact band-cross confirmation remain unspecified.

- Pivot rules, deviation sample window, median updates, threshold deviation population and exact band-cross confirmation remain unspecified.

## How it works

- Build a selectable smoothed price basis, collect pivots above/below it and form median-deviation threshold and outer bands.
- Color trend by basis direction or selected-source crossing with a threshold buffer; track time and volume-relative-to-average in band lots.

## Outputs and intended use

- Inspect threshold retests for trend context or extreme deviations plus price exhaustion for mean-reversion research; configure band/trend alerts.

## Parameters and stated settings

- Basis defaults to OHLC4/SMA 20; cross-based trend with low/high sources is default. Threshold and deviation widths default to one median deviation, with outer multiples up to three. Relative-volume reference is SMA 20.

## Failure modes and caveats

- Analytical: pivot confirmation and accumulated deviation samples can lag structural change; claims of normal-shaped time distribution or low risk are not guarantees.

## Missing information and implementation boundary

- Pivot rules, deviation sample window, median updates, threshold deviation population and exact band-cross confirmation remain unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
OHLC4 and SMA 20 as basis
```

### E2: parameters, readiness

```text
By default, threshold band is calculated based on 1x median deviation
```

### E3: parameters, readiness

```text
multiplied up to 3
```

### E4: parameters, readiness

```text
volume moving average (SMA 20)
```

### E5: parameters, readiness

```text
default, the script uses cross based trend mode with low and high as sources.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eos9u1qm_fair_value_bands_flowly_indicators](../tv_eos9u1qm_fair_value_bands_flowly_indicators.md)

## Source

https://www.tradingview.com/script/eos9U1qM-Fair-value-bands-Flowly-Indicators/

Publication ID: eos9U1qM. Source SHA-256: 9ac107953b9246ec98f5527bd1758faddbd3b998528a65ce5f5f78b7b327b634. Raw-description SHA-256: 013dcc333beaf2d585b579c909c7b2084240f3ba15884beadb8d31b430f2c690.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
