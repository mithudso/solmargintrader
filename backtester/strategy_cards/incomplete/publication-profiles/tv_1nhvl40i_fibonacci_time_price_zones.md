---

id: tv_profile_1nhvl40i

name: "Fibonacci Time-Price Zones"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Visualize Fibonacci relationships jointly in elapsed chart time and price. The tool offers curved and straight constructions from manually selected anchors, helping a trader compare potential interaction zones rather than producing a predictive entry signal."

registry_key: null

runner: null

evaluation: null

---

# Fibonacci Time-Price Zones

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Visualize Fibonacci relationships jointly in elapsed chart time and price. The tool offers curved and straight constructions from manually selected anchors, helping a trader compare potential interaction zones rather than producing a predictive entry signal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Exact radial/logarithmic and aspect-ratio equations, straight projection coordinates and C/D derivation are absent.

- Exact radial/logarithmic and aspect-ratio equations, straight projection coordinates and C/D derivation are absent.

## How it works

- User-selected time/price points A and B anchor the constructions; changes synchronize between chart dragging and settings.
- Circular mode expands partial circles using logarithmic radial scaling and an aspect ratio derived from the swing distances; orthogonal mode separates time and price into L-shaped paths, while sloped mode projects along the trend. Horizontal mode supplies conventional ratio levels.
- Retracement and extension zones can coexist. The author notes that distinct circular and straight scaling methods prevent perfect simultaneous alignment.

## Outputs and intended use

- Inspect potential support/resistance and temporal turning zones; compare horizontal references with the dynamic shapes.
- Optional A/B/C/D labels, ratio labels and base/projection/pullback lines explain the construction visually.

## Parameters and stated settings

- Configurable ratio visibility, values, color and width; retracement, extension or both; circular, orthogonal, sloped or horizontal shapes.
- Fill ranges from 0% to 100%; anchors are manual and must be adjusted when instrument price scales change.

## Failure modes and caveats

- The author explicitly rejects standalone predictive use. Hindsight alignment and subjective anchor choice can exaggerate apparent usefulness.
- The prose alternately describes circular origins at A and at B; a faithful recreation must resolve this ambiguity.

## Missing information and implementation boundary

- Exact radial/logarithmic and aspect-ratio equations, straight projection coordinates and C/D derivation are absent.

## Data requirements

Required inputs: ohlcv, user-defined time and price anchors.

Repository input-class support: unavailable or unresolved. Caller-defined chart anchors must accompany market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
The indicator's calculations are anchored to user-defined start and end points on the chart.
```

### E2: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
The [b]Circular[/b] shape employs logarithmic scaling with radial expansion
```

### E3: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
[i]0%[/i]: No fill between levels
[i]100%[/i]: Maximum fill between levels
```

### E4: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
It is not intended as a predictive or standalone trading signal indicator.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_1nhvl40i_fibonacci_time_price_zones](../tv_1nhvl40i_fibonacci_time_price_zones.md)
- [tv_method_fib_extensions](../../../strategy_research/tv_method_fib_extensions.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/1NHVL40I-Fibonacci-Time-Price-Zones/

Publication ID: 1NHVL40I. Source SHA-256: 60a8ce7487acf5f50ee9c5c4e701ac35ee03a7f201fb18fbfa2fd5e5fe667ac0. Raw-description SHA-256: 2b604a1a9f23082e5d3bef3a519e389cdb8f65477b203815271c06f422fe8b1c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
