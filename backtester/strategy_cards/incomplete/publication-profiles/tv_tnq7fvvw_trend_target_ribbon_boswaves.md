---

id: tv_profile_tnq7fvvw

name: "Trend Target Ribbon [BOSWaves]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Trend Target Ribbon combines ALMA trend confirmation with a chart-based position plan. A directional flip creates an entry reference, structural risk distance and staged reward levels, while a gradient ribbon conveys the strength of the existing trend."

registry_key: null

runner: null

evaluation: null

---

# Trend Target Ribbon [BOSWaves]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trend Target Ribbon combines ALMA trend confirmation with a chart-based position plan. A directional flip creates an entry reference, structural risk distance and staged reward levels, while a gradient ribbon conveys the strength of the existing trend.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for configured trend-state flips and ATR-clamped structural risk with caller calculation settings/initial state; ribbon conviction, target spacing and intrabar event ordering remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Configured trend rule: B=ALMA(source,length,offset,sigma), slope=(B-B[k])/ATR and band width=confirmation*SD(source,deviation length). Flip bullish only if slope>minimum and close>B+width, bearish only if slope<-minimum and close<B-width, and only on a changed state. At a flip entry E=close; long raw risk=E-lowestLow(stop lookback), short raw risk=highestHigh(stop lookback)-E. Clamp risk to [minimumATR*ATR,maximumATR*ATR] and place stop E-risk for long or E+risk for short. Caller supplies all selected calculation settings and initial state.
- The baseline is an ALMA of the selected source. Its change over a configurable slope lookback is divided by ATR. Bullish confirmation requires positive slope above its threshold and a close above the ALMA plus a standard-deviation confirmation band; bearish confirmation reverses both conditions. State changes only when the qualifying direction differs from the current state.
- On a flip, entry is the closing price. The recent swing low for longs or high for shorts supplies raw risk, clamped between minimum and maximum ATR distances. Successive equidistant R targets extend in the trade direction. Bar extremes track stops and target hits; an opposing flip freezes the previous drawing.
- Conviction blends doubled slope magnitude and price separation from ALMA to control a layered ribbon and candle brightness. Old position drawings are removed when the history limit is exceeded.

## Outputs and intended use

- Directional diamonds and alerts identify flips. Entry, stop, risk zone, target lines and persistent checkmarks support visual planning and staged discretionary exits. Proximity glow highlights approaching targets; faded plans preserve recent signal history.

## Parameters and stated settings

- Suggested baseline: ALMA length 34, confirmation 0.65, slope minimum 0.08, structural lookback 12, stop ATR bounds 0.75 and 3.0, four targets and four visible positions. Source, ALMA offset/sigma, slope/deviation lookbacks, projection length and approach radius are configurable.

## Failure modes and caveats

- Choppy markets can produce rapid opposing plans. ATR clamping can move a stop away from actual structure. Drawn target touches do not establish executable fills, intrabar event order or measured returns.

## Missing information and implementation boundary

- ATR and deviation lengths, ALMA offset/sigma defaults, exact conviction normalization and R-spacing coefficient are not supplied. Simultaneous stop/target handling is not defined.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described trend and planning calculations use chart price history and derived volatility; raw OHLCV class is sufficient.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
The ALMA change over the configured slope lookback bars is divided by ATR
```

### E2: mechanism, parameters, readiness

```text
Suggested Baseline Configuration:
```

### E3: mechanism, parameters, readiness

```text
[*][i]ALMA Length[/i]: 34
[*][i]Trend Confirmation[/i]: 0.65
[*][i]Minimum Slope[/i]: 0.08
[*][i]Stop Structure Lookback[/i]: 12
[*][i]Minimum Stop ATR[/i]: 0.75
[*][i]Maximum Stop ATR[/i]: 3.0
[*][i]Profit Targets[/i]: 4
[*][i]Positions On Chart[/i]: 4
```

### E4: mechanism, parameters, readiness

```text
The conviction score combines doubled slope magnitude with distance-weighted separation between price and ALMA, normalized to a 0-1 range
```

### E5: mechanism, parameters, readiness

```text
A bullish flip requires slope above the minimum threshold and close above the upper confirmation band simultaneously. A bearish flip requires slope below the negative threshold and close below the lower confirmation band. Flips are only registered when the new state differs from the current state.
```

### E6: mechanism, parameters, readiness

```text
The swing low over the stop lookback for long positions and swing high for short positions provides the structural stop reference, with the raw risk distance clamped between ATR minimum and ATR maximum bounds.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_tnq7fvvw_trend_target_ribbon_boswaves](../../../strategy_research/tv_tnq7fvvw_trend_target_ribbon_boswaves.md)

## Source

https://www.tradingview.com/script/tnQ7FvvW-Trend-Target-Ribbon-BOSWaves/

Publication ID: tnQ7FvvW. Source SHA-256: f96a1b8beae7a1a2d28406bebc69d3143e7146e63181f90269fca0e68fe823be. Raw-description SHA-256: 0392b85c6571a6975997e941dabe9c6b79e9567adb71a6ee947927e0aa525956.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
