---

id: tv_profile_wtmg0nge

name: "Golden Pocket"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Maintain Fibonacci pullback zones from confirmed swing structure and optionally limit them to the direction of a moving-average trend."

registry_key: null

runner: null

evaluation: null

---

# Golden Pocket

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Maintain Fibonacci pullback zones from confirmed swing structure and optionally limit them to the direction of a moving-average trend.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Average acceptance test, pivot-pair choice, touch definition, invalidation/retirement and stop/exit rules are missing.

- Average acceptance test, pivot-pair choice, touch definition, invalidation/retirement and stop/exit rules are missing.

## How it works

- Detect pivot highs/lows using left/right candle comparisons, calculate retracement boxes between selected Fibonacci levels and extend boxes until price touches them. A selectable higher-timeframe average can filter accepted zones.

## Outputs and intended use

- Inspect pivot-anchor lines and zone states, and create one alert covering touches of the monitored boxes. A touch is a setup notification rather than an independently validated entry.

## Parameters and stated settings

- Default retracements are 0.618 and 0.65. Pivot distance, average settings/timeframe, line style, colors and alert enablement are configurable.

## Failure modes and caveats

- Pivots require future bars for confirmation. Higher-timeframe filters may be developing, and a retracement touch does not bound downside or guarantee a bounce.

## Missing information and implementation boundary

- Average acceptance test, pivot-pair choice, touch definition, invalidation/retirement and stop/exit rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed feature uses ordinary price/volume history; this is input-class support rather than verified implementation or data-cache parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
fibonacci retracement levels of 0.65 and 0.618 by default
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
these boxes will extend with current price until they are hit.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
it must be the highest/lowest to the  left/right of the pivot candle count.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The alerts are set up to trigger as soon as price touches one of the boxes.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wtmg0nge_golden_pocket](../tv_wtmg0nge_golden_pocket.md)

## Source

https://www.tradingview.com/script/wtMG0NgE-Golden-Pocket/

Publication ID: wtMG0NgE. Source SHA-256: 5bad61ad33045a90d826ca1c8602e6f896059dee363d732beebab9fec22c747f. Raw-description SHA-256: 1ae49c37664b7fa3c3d38f4a0d8af9fdd927728caad1f9804e178978bf2047fb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
