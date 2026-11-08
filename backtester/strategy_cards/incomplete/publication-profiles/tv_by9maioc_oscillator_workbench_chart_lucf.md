---

id: tv_profile_by9maioc

name: "Oscillator Workbench — Chart [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Oscillator Workbench translates oscillator behavior into price-chart channels so traders can explore configurations in market context. It normalizes an oscillator’s position above or below its centerline, weights a price source with that percentage, and compares a weighted average with an unweighted reference. Separate divergence channels mark transition/consolidation regions without assigning an immediate bullish or bearish prediction. Direction follows later price breaches. The author suggests aligned strong states as one possible use, while emphasizing that settings must fit the reader’s methodology and that a neutral divergence region is generally a no-trade area."

registry_key: null

runner: null

evaluation: null

---

# Oscillator Workbench — Chart [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Oscillator Workbench translates oscillator behavior into price-chart channels so traders can explore configurations in market context. It normalizes an oscillator’s position above or below its centerline, weights a price source with that percentage, and compares a weighted average with an unweighted reference. Separate divergence channels mark transition/consolidation regions without assigning an immediate bullish or bearish prediction. Direction follows later price breaches. The author suggests aligned strong states as one possible use, while emphasizing that settings must fit the reader’s methodology and that a neutral divergence region is generally a no-trade area.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for alternate close-RSI20 versus close-change divergence channels, including high/low expansion and whole-bar breaches. Default weighted-price channel, cap, strong-state labels and complex oscillator modes remain underspecified.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Track historical oscillator extrema separately above/below the centerline and convert relative position into signed weight; optionally include relative volume.
- Average original and weighted price sources with the same MA settings and cap weighted displacement.
- Detect mismatched slopes, form/expand a channel from divergence-bar prices until breached, and classify states by breach direction and oscillator-channel alignment.
- Independent alternate mode: use close-based RSI of length 20 and flag a divergence when the polarity of its one-bar change differs from close-to-close price-change polarity. At a divergence, save that bar high/low as channel top/bottom. Further divergences before breach expand top upward or bottom downward only when their extremes lie outside the current channel. After a breach, the next divergence starts a new channel.
- For default whole-bar breaches, bullish means the bar low is above channel top; bearish means the bar high is below channel bottom. An unbreached channel is neutral. Strong-state labels still require the separately underspecified weighted oscillator channel and are excluded from this usable alternate-channel scope.

## Outputs and intended use

- Oscillator channel, divergence levels, bar colors, optional closing-bar markers/alerts and Data Window raw values support exploratory analysis.
- Strong-to-ordinary trend-state weakening can motivate discretionary stop tightening, not an automatic reversal.

## Parameters and stated settings

- Thirty internal oscillators or an external plot with specified centerline are selectable.
- Defaults use close-based RSI 20 and ALMA 20, oscillator-only weight, three-standard-deviation cap, divergence-bar high/low and whole-bar breach conditions.
- Cap can instead use ATR; channel prices, divergence mode, bias estimation, coloring and marker filters are adjustable.

## Failure modes and caveats

- Early-history normalization is explicitly fragile. Volume-dependent choices fail when volume is unavailable.
- Realtime values change; the author says markers appear only at bar close, which does not independently verify all historical behavior.

## Missing information and implementation boundary

- Complex oscillator subparameters, exact weighting/cap formulas, MA defaults beyond length and detailed alert filters require unavailable code.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Default RSI/price-channel calculations use OHLCV; optional external oscillator plots require their own inputs and are not covered by this availability judgment.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Thirty oscillators are available
```

### E2: parameters

```text
a length of 20 bars.
```

### E3: parameters

```text
capped to three standard deviations
```

### E4: risks

```text
fragile in the early history of datasets
```

### E5: outputs_and_use, risks

```text
markers only appear on bar closes
```

### E6: mechanism, readiness

```text
slope of the reference line does not match that of the weighted line.
```

### E7: mechanism, readiness

```text
differences in polarity between the oscillator's slope and the polarity of close-to-close values.
```

### E8: mechanism, readiness

```text
Until that new channel is breached, bars where additional divergences occur will expand the channel's levels if the bar's price points are outside the channel.
```

### E9: mechanism, readiness

```text
Breaches of the channel require a bar's [url=https://www.tradingview.com/pine-script-reference/v5/#var_low]low[/url] to move above the top of the channel, and the bar's [url=https://www.tradingview.com/pine-script-reference/v5/#var_high]high[/url] to move below the channel's bottom.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_by9maioc_oscillator_workbench_chart_lucf](../tv_by9maioc_oscillator_workbench_chart_lucf.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/BY9mAioc-Oscillator-Workbench-Chart-LucF/

Publication ID: BY9mAioc. Source SHA-256: 9dbcdb990da69f878d059bd48b60e2718a6ad560ef254a71bd12df40eee20c2a. Raw-description SHA-256: fffa5b36bd7398b493c6eb28360968917e652c5761e78b6de2ecd2376909e8f4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
