---

id: tv_profile_seduwoij

name: "Zeiierman Trend Pressure (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Zeiierman Trend Pressure separates fast local pressure, persistent range-based trend and a candle-structure pressure core. It aims to distinguish a short pullback within an intact trend from broader deterioration, then track sustained extreme states through confirmation and release hysteresis. The author suggests trend-following alignment and treating pressure release as a possible reversal cue, explicitly warning that an active box alone is not an entry. The several equations improve transparency, but the full persistence and release engines remain undisclosed."

registry_key: null

runner: null

evaluation: null

---

# Zeiierman Trend Pressure (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Zeiierman Trend Pressure separates fast local pressure, persistent range-based trend and a candle-structure pressure core. It aims to distinguish a short pullback within an intact trend from broader deterioration, then track sustained extreme states through confirmation and release hysteresis. The author suggests trend-following alignment and treating pressure release as a possible reversal cue, explicitly warning that an active box alone is not an entry. The several equations improve transparency, but the full persistence and release engines remain undisclosed.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Persistence, component normalization and state confirmation/release equations are not disclosed.

## How it works

- Normalize close within recent range and blend with a stochastic transformation to form EMA-smoothed Z-Pulse.
- Blend fast/trend/macro range readings and adapt persistence according to agreement/efficiency.
- Combine candle location, body, wick and impulse into reactive/regime Pressure Core; enter extreme states when pulse/trend align and release after separate confirmation rules.

## Outputs and intended use

- Three pressure views, core colors, dots, event triangles and active-state price boxes support trend/continuation/reversal context.

## Parameters and stated settings

- Scale 0 to -100. Pulse blend weights 0.72/0.28; trend weights 0.10/0.18/0.72.
- Core weights close/mean/body/wick/impulse 0.42/0.23/0.13/0.12/0.10; impulse spans five bars.
- Range/stochastic/smoothing lengths, persistence, exhaustion zone, sensitivity and regime weight are configurable.

## Failure modes and caveats

- Reversal release indicates weakening pressure, not a guaranteed price reversal.
- Sensitivity changes state stability and may create inconsistent behavior at low settings.

## Missing information and implementation boundary

- Component normalization, efficiency adaptation, persistence equation, confirmation/release thresholds and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. All disclosed range/candle/impulse components are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
normalized 0 to -100 range.
```

### E2: parameters, mechanism

```text
rangePosition * 0.72
  + stochasticPulse * 0.28
```

### E3: parameters, mechanism

```text
Fast Range   * 0.10
  + Trend Range  * 0.18
  + Macro Range  * 0.72
```

### E4: parameters, mechanism

```text
closeLocation * 0.42
  + meanLocation  * 0.23
  + bodyBias      * 0.13
  + wickBias      * 0.12
  + impulse       * 0.10
```

### E5: parameters

```text
recent five-bar price impulse
```

### E6: readiness, mechanism

```text
entry confirmation and a separate release distance
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_seduwoij_zeiierman_trend_pressure_zeiierman](../tv_seduwoij_zeiierman_trend_pressure_zeiierman.md)

## Source

https://www.tradingview.com/script/SEdUWOIJ-Zeiierman-Trend-Pressure-Zeiierman/

Publication ID: SEdUWOIJ. Source SHA-256: 5ab439798e4adf9637f11b08be57b59d51ffe7e96514204d62b5ff0991743e2a. Raw-description SHA-256: 338288be0318484df626dedd82b8aa2f2f4de7e648d61b87ba7438aa2efbae49.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
