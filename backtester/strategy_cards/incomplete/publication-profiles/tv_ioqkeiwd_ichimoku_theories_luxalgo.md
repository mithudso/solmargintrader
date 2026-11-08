---

id: tv_profile_ioqkeiwd

name: "Ichimoku Theories [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Combine conventional Ichimoku equilibrium lines with cycle, wave and price-target analysis. The tool supplies market-structure expectations and timing references; the author frames them as understanding rather than guaranteed forecasts."

registry_key: null

runner: null

evaluation: null

---

# Ichimoku Theories [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine conventional Ichimoku equilibrium lines with cycle, wave and price-target analysis. The tool supplies market-structure expectations and timing references; the author frames them as understanding rather than guaranteed forecasts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Five-line Ichimoku/cloud is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Tenkan/Kijun are rolling range midpoints, span A their midpoint, span B a longer range midpoint; the cloud lies between projected spans and Chikou offsets closing price backward.
- Detected crosses, cloud changes, swing events or selected wave patterns define cycles. Forecasts project either basic-number intervals or repeats of a selected historical cycle from its anchor.
- Swing sequences form I/V/N legs or contracting, expanding and double-top/bottom structures. Developing N waves supply potential price targets, but their formulas are only referenced in an image.
- For supplied OHLC,Tenkan=(highestHigh(9)+lowestLow(9))/2;Kijun same over26;SpanA=(Tenkan+Kijun)/2;SpanB=(highestHigh(52)+lowestLow(52))/2. Plot spans26 bars ahead and close26 bars back as Chikou;cloud fills SpanA–SpanB. Lengths/offset can be caller parameters. Automatic waves/cycle anchors and image-only targets remain excluded.

## Outputs and intended use

- Line/cloud overlays, historical cycle markers, future timing lines, wave drawings and price targets can be selectively combined.
- Swing confirmation takes time; time projections convey hypothesized turning windows without a disclosed entry or execution system.
- Usable scope: Five-line Ichimoku/cloud. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Conventional horizons are 9,26,52 with 26-bar span offsets. Basic timing sequence: 9,17,26,33,42,51,65,76,129,172,200,257.
- Swing confirmation length, cycle mode/anchor, wave overlap, target visibility and retained drawing counts are adjustable.

## Failure modes and caveats

- Historical swing labels and backward-plotted Chikou require careful information timing. Calendar projections do not independently establish turning-point probabilities.
- The source says three extended targets but names only 2E and 3E, an unresolved count inconsistency.

## Missing information and implementation boundary

- Swing/pattern acceptance equations and price-target formulas are absent from readable prose; image-only calculations cannot establish them.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical OHLCV supplies the chart-data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
short (9 periods), medium (26 periods), and long (52 periods)
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
plotted 26 candles into the future
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
9, 17, 26, 33, 42, 51, 65, 76, 129, 172, 200, 257
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The tool displays 4 basic targets (V, E, N, and NT) and 3 extended targets (2E and 3E)
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Number of candles to confirm a swing high or swing low.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Tenkan sen:[/b] middle point of the range of the last 9 candles
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Kinjun sen:[/b] middle point of the range of the last 26 candles
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Senkou span B:[/b] midpoint of the range of the last 52 candles, plotted 26 candles into the future
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Senkou span A:[/b] middle point between Tankan Sen and Kijun Sen, plotted 26 candles into the future
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Chikou span:[/b] closing price plotted 26 candles into the past
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ioqkeiwd_ichimoku_theories_luxalgo](../tv_ioqkeiwd_ichimoku_theories_luxalgo.md)
- [tv_method_double_top_bottom](../tv_method_double_top_bottom.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/ioQKeiwD-Ichimoku-Theories-LuxAlgo/

Publication ID: ioQKeiwD. Source SHA-256: 5609e21b1482bd88379d9b926cf5b064365d95f9ebe69ad6d31c82cbb62fa22a. Raw-description SHA-256: 6b6e88631501f584e26dba08fbdac6dd60c495cff96a1c26dd7636d86c53446c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
