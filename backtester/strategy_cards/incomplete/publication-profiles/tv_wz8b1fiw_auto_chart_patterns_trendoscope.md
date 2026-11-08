---

id: tv_profile_wz8b1fiw

name: "Auto Chart Patterns [Trendoscope®]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Automatically identify multiscale chart patterns as pairs of nonintersecting trendlines, then label their geometry, direction and expansion behavior."

registry_key: null

runner: null

evaluation: null

---

# Auto Chart Patterns [Trendoscope®]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Automatically identify multiscale chart patterns as pairs of nonintersecting trendlines, then label their geometry, direction and expansion behavior.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for thirteen-case supplied-line classification with caller tolerances; automatic zigzag/line discovery remains outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For supplied line pairs and caller flat/parallel tolerances, thirteen cases are: both rising/parallel = ascending channel; both falling/parallel = descending channel; both flat = ranging channel. Both rising and widening/narrowing = expanding/contracting rising wedge; both falling and widening/narrowing = expanding/contracting falling wedge. Upper rising/lower flat = expanding ascending triangle; upper flat/lower rising = contracting ascending triangle; upper flat/lower falling = expanding descending triangle; upper falling/lower flat = contracting descending triangle. Upper falling/lower rising = converging triangle; upper rising/lower falling = diverging triangle.
- Generate recursive zigzags from several length/depth combinations and inspect the latest five/six pivots. Require an upper line touching highs, a lower touching lows and no intervening candle outside them. Classify relative slopes as channels,wedges or triangles and converging,diverging or parallel.

## Outputs and intended use

- Draw the accepted pattern and alert on new detections. Rising/falling channels,wedge variants,ascending/descending triangles and bidirectional triangles are geometric descriptions, not complete trades or validated reversal probabilities.

## Parameters and stated settings

- Configure base zigzags,pivot count,error/flat thresholds,last-pivot direction,bar-ratio filtering,overlap policy and group/individual pattern toggles. Avoid Overlap ignores a candidate starting inside an existing pattern; numerical defaults are absent.

## Failure modes and caveats

- Multiple scales generate correlated structures and flexible tolerances can overfit visual history. Latest zigzag pivots may change before confirmation; a valid pattern is not a guaranteed breakout or prescribed direction.

## Missing information and implementation boundary

- Base/recursive swing algorithm, exact trendline fit/touch tolerance,error/flat units,bar-ratio limit and candle containment price definition are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV supports geometric pattern scanning; missing detection equations are algorithm gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, readiness

```text
last 5 pivots or 6 pivots
```

### E2: purpose, mechanism, parameters, readiness

```text
None of the candles from starting pivot to ending pivot should fall outside the trend lines
```

### E3: purpose, mechanism, parameters, readiness

```text
Both trend lines are rising
```

### E4: purpose, mechanism, parameters, readiness

```text
Trend lines are parallel to each other
```

### E5: purpose, mechanism, parameters, readiness

```text
if the new pattern starting point falls between the start and end of an existing pattern, it will be ignored.
```

### E6: mechanism, parameters, readiness

```text
[b]🎯 Individual Pattern Types[/b]
Now we have broader classifications. Let's go through in detail to find out fine-grained classification of each individual patterns.

[b]🚩 Ascending/Uptrend Channel[/b]
This pattern belongs to the broader classifications - Ascending Patterns, Parallel Patterns and Channels. The rules for the Ascending/Uptrend Channel pattern are as below
[list]
[*] Both trend lines are rising
[*] Trend lines are parallel to each other
[/list]
https://www.tradingview.com/x/botk5Hzj

[b]🚩 Descending/Downtrend Channel[/b]
This pattern belongs to the broader classifications - Descending Patterns, Parallel Patterns and Channels. The rules for the Descending/Downtrend Channel pattern are as below
[list]
[*] Both trend lines are falling
[*] Trend lines are parallel to each other
[/list]
https://www.tradingview.com/x/Um1VYOS3

[b]🚩 Ranging Channel[/b]
This pattern belongs to the broader classifications - Flat Patterns, Parallel Patterns and Channels. The rules for the Ranging Channel pattern are as below
[list]
[*] Both trend lines are flat
[*] Trend lines are parallel to each other
[/list]
https://www.tradingview.com/x/fmJk8olo

[b]🚩 Rising Wedge - Expanding[/b]
This pattern belongs to the broader classifications - Rising Patterns, Diverging Patterns and Wedges. The rules for the Expanding Rising Wedge pattern are as below
[list]
[*] Both trend lines are rising
[*] Trend Lines are diverging.
[/list]
https://www.tradingview.com/x/biIGt77G

[b]🚩 Rising Wedge - Contracting[/b]
This pattern belongs to the broader classifications - Rising Patterns, Converging Patterns and Wedges. The rules for the Contracting Rising Wedge pattern are as below
[list]
[*] Both trend lines are rising
[*] Trend Lines are converging.
[/list]
https://www.tradingview.com/x/8bm2MW3Q

[b]🚩 Falling Wedge - Expanding[/b]
This pattern belongs to the broader classifications - Falling Patterns, Diverging Patterns and Wedges. The rules for the Expanding Falling Wedge pattern are as below
[list]
[*] Both trend lines are falling
[*] Trend Lines are diverging.
[/list]
https://www.tradingview.com/x/bgG25U9u

[b]🚩 Falling Wedge - Contracting[/b]
This pattern belongs to the broader classifications - Falling Patterns, Converging Patterns and Wedges. The rules for the Converging Falling Wedge are as below
[list]
[*] Both trend lines are falling
[*] Trend Lines are converging.
[/list]
https://www.tradingview.com/x/CAuBxNzZ

[b]🚩 Rising/Ascending Triangle - Expanding[/b]
This pattern belongs to the broader classifications - Rising Patterns, Diverging Patterns and Triangles. The rules for the Expanding Ascending Triangle pattern are as below
[list]
[*] The upper trend line is rising
[*] The lower trend line is flat
[*] Naturally, the trend lines are diverging from each other
[/list]
https://www.tradingview.com/x/lV4P5N6M

[b]🚩 Rising/Ascending Triangle -  Contracting[/b]
This pattern belongs to the broader classifications - Rising Patterns, Converging Patterns and Triangles. The rules for the Contracting Ascending Triangle pattern are as below
[list]
[*] The upper trend line is flat
[*] The lower trend line is rising
[*] Naturally, the trend lines are converging.
[/list]
https://www.tradingview.com/x/WVNjtW3a

[b]🚩 Falling/Descending Triangle - Expanding[/b]
This pattern belongs to the broader classifications - Falling Patterns, Diverging Patterns and Triangles. The rules for the Expanding Descending Triangle pattern are as below
[list]
[*] The upper trend line is flat
[*] The lower trend line is falling
[*] Naturally, the trend lines are diverging from each other
[/list]
https://www.tradingview.com/x/dT23FxTh

[b]🚩 Falling/Descending Triangle -  Contracting[/b]
This pattern belongs to the broader classifications - Falling Patterns, Converging Patterns and Triangles. The rules for the Contracting Descending Triangle pattern are as below
[list]
[*] The upper trend line is falling
[*] The lower trend line is flat
[*] Naturally, the trend lines are converging.
[/list]
https://www.tradingview.com/x/wehBQlQi

[b]🚩 Converging Triangle[/b]
This pattern belongs to the broader classifications - Bi-Directional Patterns, Converging Patterns and Triangles. The rules for the Converging Triangle pattern are as below
[list]
[*] The upper trend line is falling
[*] The lower trend line is rising
[*] Naturally, the trend lines are converging.
[/list]
https://www.tradingview.com/x/4lhUD1An

[b]🚩 Diverging Triangle[/b]
This pattern belongs to the broader classifications - Bi-Directional Patterns, Diverging Patterns and Triangles. The rules for the Diverging Triangle pattern are as below
[list]
[*] The upper trend line is rising
[*] The lower trend line is falling
[*] Naturally, the trend lines are diverging from each other.
[/list]
https://www.tradingview.com/x/cGmhW2N0


```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_triangle](../tv_method_triangle.md)
- [tv_method_wedge](../tv_method_wedge.md)
- [tv_wz8b1fiw_auto_chart_patterns_trendoscope](../tv_wz8b1fiw_auto_chart_patterns_trendoscope.md)

## Source

https://www.tradingview.com/script/WZ8B1FIW-Auto-Chart-Patterns-Trendoscope/

Publication ID: WZ8B1FIW. Source SHA-256: 485f241fce3a4f799c127744c3ce74a9e600225e321c3b90e37f6fbe2cb1b991. Raw-description SHA-256: 68b7623b5d1476c36684926dc07dc17dad6d4a6b264f18fe3f18b2b43ac38179.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
