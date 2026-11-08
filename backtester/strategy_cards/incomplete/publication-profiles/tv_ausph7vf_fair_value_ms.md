---

id: tv_profile_ausph7vf

name: "Fair Value MS"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Define market swings from opposite-direction fair-value-gap events and form support/resistance areas only after additional structural confirmation."

registry_key: null

runner: null

evaluation: null

---

# Fair Value MS

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Define market swings from opposite-direction fair-value-gap events and form support/resistance areas only after additional structural confirmation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The event sequence is described, but core gap/state/AOI lifecycle rules remain ambiguous for reproducible output.

- Exact FVG test and swing update state
- FVG/structure-break association
- AOI mitigation and reflection-color filter

## How it works

- Use the first opposite-direction FVG after a directional extreme to recognize a swing. A close beyond a recent swing establishes a structure break; combine the relevant FVG and break to form an AOI from the swing toward the nearest FVG edge. Sum volume from swing through the FVG closing bar.

## Outputs and intended use

- Monitor later reactions/breaks at AOIs rather than treating their creation as an entry. Reflection lines remain after zone mitigation and use averaged price for color; optional session start/end lines add context.

## Parameters and stated settings

- There are no length settings for structure. FVG is described as a three-bar formation. Default session is NYSE in America/New_York; zone/volume and reflection display choices are mentioned.

## Failure modes and caveats

- FVGs and accumulated candle volume do not establish actual institutional staging or a causal buyer/seller identity. A steady trend without gaps may produce no new structure.

## Missing information and implementation boundary

- Exact three-candle gap inequality, high/low state updates, AOI association/mitigation, average-color filter and gap overlap handling are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described financial input class; missing algorithm details do not imply missing raw data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
only the first FVG in the opposite direction of the previous direction
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
only considered when price [b]closes[/b] outside the recent swing points.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
FVG is a 3 bar formation
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
By Default, the indicator uses "America/New_York" Timezone.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ausph7vf_fair_value_ms](../tv_ausph7vf_fair_value_ms.md)
- [tv_method_fair_value_gap](../../../strategy_research/tv_method_fair_value_gap.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/AUsPh7VF-Fair-Value-MS/

Publication ID: AUsPh7VF. Source SHA-256: 825922dd29aabf209bd72215c9c814a7d601b6ba0b1f1423cbfb68de2b863a09. Raw-description SHA-256: cd20f4a31d164a9fdf8ae38d4c13ea4b208abe23370382f46048397faf7dbf67.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
