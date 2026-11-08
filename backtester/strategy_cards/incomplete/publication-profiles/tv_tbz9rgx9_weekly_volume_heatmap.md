---

id: tv_profile_tbz9rgx9

name: "Weekly Volume Heatmap"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Map typical weekly trading-volume patterns to identify relatively active and quiet hourly slots."

registry_key: null

runner: null

evaluation: null

---

# Weekly Volume Heatmap

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Map typical weekly trading-volume patterns to identify relatively active and quiet hourly slots.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for slot-average volume divided by average weekly volume on caller-supplied hourly history and weekly/session partitions; calendar and incomplete-week policies must be chosen explicitly.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Group supplied one-hour volume history by weekday/hour slot and calculate each slot’s arithmetic mean from the first through last available bar. Divide that mean by average traded volume per week and multiply by 100 for the corresponding heatmap percentage.
- For an explicitly supplied weekly partition, the denominator is the average of weekly volume totals. Light backgrounds represent lower percentages and dark backgrounds higher percentages; the prose does not specify exact color mapping or incomplete-week treatment.

## Outputs and intended use

- Light cells indicate lower and dark cells higher values. Use the distribution to understand participation seasonality; the author's claims about stop hunting are interpretations, not observations the calculation verifies.

## Parameters and stated settings

- The tool works only on the one-hour timeframe. No timezone, sample-length default or missing-session adjustment is stated.

## Failure modes and caveats

- Historical low volume does not prove manipulation. The author suggests avoiding stop-loss orders in quiet hours, but the heatmap alone cannot justify removing risk controls.

## Missing information and implementation boundary

- Timezone/session alignment, inclusion of partial weeks and missing slots, and exact color thresholds are unspecified. These affect historical/default parity rather than the slot-to-weekly-volume ratio on a supplied partition.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature uses ordinary OHLCV, including lower-timeframe history where selected. This establishes data class only, not a verified implementation or cache.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
First, it calculates the average traded volume of each period (for example Monday 9:00 AM) from the first bar to the last bar.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
It then calculates the ratio of the average traded volume in each period to the average traded volume per week.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
It only works in the 1 hour time frame.
```

### E4: mechanism, parameters, readiness

```text
Finally, the result is displayed as a percentage in each cell.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_tbz9rgx9_weekly_volume_heatmap](../../../strategy_research/tv_tbz9rgx9_weekly_volume_heatmap.md)

## Source

https://www.tradingview.com/script/TbZ9rgX9-Weekly-Volume-Heatmap/

Publication ID: TbZ9rgX9. Source SHA-256: a04a127c3289e7103eccc4d08a2a58ed215feeb2b8292d2061ce69943487a6e4. Raw-description SHA-256: 907e590ca6d1949ed70f27433d92f6b9ecf124fff13df489ec9a5b823c0a2070.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
