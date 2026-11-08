---

id: tv_profile_xh8tldte

name: "Realtime Delta Volume Action [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Realtime Delta Volume Action builds a custom live candle view from incoming price/volume updates. It supplements price action with signed update counts, signed volume, relative deltas and a volume-weighted update-price reference. The author emphasizes that the accumulated detail cannot be reconstructed from historical bars and disappears on reload, so this is live observational tooling rather than a replayable historical signal model."

registry_key: null

runner: null

evaluation: null

---

# Realtime Delta Volume Action [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Realtime Delta Volume Action builds a custom live candle view from incoming price/volume updates. It supplements price action with signed update counts, signed volume, relative deltas and a volume-weighted update-price reference. The author emphasizes that the accumulated detail cannot be reconstructed from historical bars and disappears on reload, so this is live observational tooling rather than a replayable historical signal model.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Live update-count delta/share is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Assign each feed update a sign from its price change, carrying the last sign through unchanged prices; accumulate signed tick and volume deltas per bar.
- Compute delta shares of totals and a volume-weighted mean of update prices, labeled POC by the author.
- Combine configurable marker conditions with AND logic; use DV polarity/intensity and candle disagreement for body colors and strong-bar borders.
- From ordered update prices assign+1 to increases,-1 to decreases, retaining last sign on unchanged prices. Within each bar DT=sum(sign),T=count(updates),DT%=100*DT/T for T>0. Initial polarity is caller-defined. Volume differencing and strong-bar extras remain unqualified.

## Outputs and intended use

- Inspect live bars and elapsed-live values, configure directional markers and alerts, and compare volume/tick evidence with price and a broader trend context.
- Usable scope: Live update-count delta/share. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Five markers start inactive without conditions; fourteen condition types cover price, delta, update counts, POC and volume. Alerts/markers are described as bar-close.
- Source targets approximately 5-second to 5-minute discretionary analysis; all display/threshold settings are user-configurable without full defaults.

## Failure modes and caveats

- Reload/input changes erase accumulated observations; runtime/chart slowdown is disclosed. Analytical: price-change attribution is not actual buyer/seller aggressor data and the POC is a weighted mean rather than a modal price.
- The author states they have not traded this tool; claimed alert non-repainting is not independently verified.

## Missing information and implementation boundary

- Update-volume differencing, feed aggregation behavior, complete strong-bar defaults and transport/reload persistence are not supplied.

## Data requirements

Required inputs: realtime feed update prices and volume changes.

Repository input-class support: unavailable or unresolved. Historical OHLCV does not preserve the update sequence; source explicitly says the values cannot be recalculated from history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
five available markers.
```

### E2: parameters, readiness

```text
14 —  DT+ rises
```

### E3: parameters, readiness

```text
five markers that will not trigger because no conditions are associated with them.
```

### E4: parameters, readiness

```text
5sec–5min timeframes
```

### E5: mechanism, risks, readiness

```text
It is the volume-weighted average of all price updates during the bar.
```

### E6: risks, readiness

```text
If you refresh the chart or restart the script, the accumulated information will be lost.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
This script monitors each realtime update of the chart's feed. It first determines if price has moved up or down since the last update. The polarity of the price change, in turn, determines the polarity of the volume​​ and tick for that specific update. If price does not move between consecutive updates, then the last known polarity is used. Using this method, we can calculate a running volume​ delta and ticks delta for the bar, which becomes the bar's final​ delta values when the bar closes (you can inspect values of elapsed realtime bars in the Data Window or the indicator's values). Note that these values will all reset if the script re-executes because of a change in inputs or a chart refresh.
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
 • Above the bar: ticks delta​ (DT​), the total ticks​ for the bar, the percentage of total ticks that DT​ represents (DT%)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_xh8tldte_realtime_delta_volume_action_lucf](../../../strategy_research/tv_xh8tldte_realtime_delta_volume_action_lucf.md)

## Source

https://www.tradingview.com/script/Xh8tLDTe-Realtime-Delta-Volume-Action-LucF/

Publication ID: Xh8tLDTe. Source SHA-256: e38a5891090b763400337b65d613a408386f7cc704450c4c9e16406040f4491f. Raw-description SHA-256: 505dd87cf58044171fd615319b68060f59e805e5bb092486c94c31f7eb8dc165.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
