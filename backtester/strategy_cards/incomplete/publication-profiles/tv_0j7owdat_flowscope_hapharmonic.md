---

id: tv_profile_0j7owdat

name: "FlowScope [Hapharmonic]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Combine several chart candles into a summary candle and a volume-at-price-style profile to inspect activity distribution within a broader interval."

registry_key: null

runner: null

evaluation: null

---

# FlowScope [Hapharmonic]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine several chart candles into a summary candle and a volume-at-price-style profile to inspect activity distribution within a broader interval.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for composite OHLCV on caller-defined group boundaries; profile distribution, ATR sizing and lower-timeframe buy/sell allocation remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For caller-specified candle groups, grouped open is the first bar’s open, high is maximum high, low is minimum low, close is the final bar’s close and volume is the sum of component volumes. This independent OHLCV aggregation does not require the opaque profile or directional-volume algorithms.
- Aggregate first open, maximum high, minimum low and last close across each group. Estimate lower-timeframe buy/sell participation and build horizontal profile boxes, using ATR divided by ten as an ideal row height but capping row count.

## Outputs and intended use

- Inspect high/low volume nodes and total/buy/sell summaries alongside the grouped candle. The author suggests acceptance, rejection and absorption interpretations, which are hypotheses rather than observed institutional intent.

## Parameters and stated settings

- Group count is adjustable; four five-minute bars illustrate twenty minutes. Maximum profile boxes defaults fifty. Palette use defaults unchecked with ten optional presets; candle/body/background/gradient and widths are configurable.

## Failure modes and caveats

- A profile inferred from candle data cannot claim exact trade-by-price truth without its allocation algorithm. Grouping changes apparent structure and a developing group updates before completion.

## Missing information and implementation boundary

- ATR period, volume allocation, buy/sell classification, grouping origin, partial groups and conservation/row-boundary rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price/volume history supports the input class; missing equations are specification gaps rather than missing raw data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
ATR / 10
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
setting (defaulting to 50)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
setting "[i]Group Candles[/i]" to 4 on a 5-minute chart
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The open of the [i]first[/i] candle
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The close of the [i]last[/i] candle
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
choose from 10
```

### E7: mechanism, parameters, readiness

```text
The open of the [i]first[/i] candle in the group.
```

### E8: mechanism, parameters, readiness

```text
The absolute [i]highest price[/i] reached within the group.
```

### E9: mechanism, parameters, readiness

```text
The absolute [i]lowest price[/i] reached within the group.
```

### E10: mechanism, parameters, readiness

```text
The close of the [i]last[/i] candle in the group.
```

### E11: mechanism, parameters, readiness

```text
The total volume for the entire group.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_0j7owdat_flowscope_hapharmonic](../tv_0j7owdat_flowscope_hapharmonic.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/0j7OWDAT-FlowScope-Hapharmonic/

Publication ID: 0j7OWDAT. Source SHA-256: ff1dcdbdf477229cbdeba1f33e48549348f6a75c83902eb60234ec45b16d55d6. Raw-description SHA-256: 86e4fd3b6c807fbee5be83162e6c6c5bab6c0d48307493606e2b55136bee0867.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
