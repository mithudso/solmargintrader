---

id: tv_profile_tng177sv

name: "Realtime 5D Profile [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Realtime 5D Profile accumulates live chart updates into price-level distributions of volume or update counts. It encodes level activity, directional imbalance and age, offering an evolving view of where observed participation occurred. Unlike a historical profile, it starts when loaded and loses its accumulated state when refreshed or re-executed. The source carefully distinguishes chart updates from exchange transactions, so its tick label must not be interpreted as a complete trade tape on aggregated charts."

registry_key: null

runner: null

evaluation: null

---

# Realtime 5D Profile [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Realtime 5D Profile accumulates live chart updates into price-level distributions of volume or update counts. It encodes level activity, directional imbalance and age, offering an evolving view of where observed participation occurred. Unlike a historical profile, it starts when loaded and loses its accumulated state when refreshed or re-executed. The source carefully distinguishes chart updates from exchange transactions, so its tick label must not be interpreted as a complete trade tape on aggregated charts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for up/down update-count totals/delta on supplied ordered updates with explicit first-update convention and timeframe reset. Volume extraction, level rebinning, age rendering and trend-reset parity remain incomplete.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independent aggregate activity counts: for ordered chart updates, compare price with the previous update; increment UpCount on higher price, DownCount on lower price, and carry the last known direction when unchanged. Totals are UpCount+DownCount and delta UpCount−DownCount. Use a selected timeframe reset; seed from the first observed price and begin counting once a comparison/known polarity exists. This explicit first-update exclusion is a caller convention because source initialization is not stated.
- Assign each update to up/down using price versus the preceding update, retaining the last direction when unchanged.
- Bin updates around dynamic price levels; rebalance historical updates when the profile range changes. Line lengths scale to the largest level and age comes from average update times.
- Render double-sided down/up profiles or single-sided totals/deltas; reset by selected timeframes or trend changes.

## Outputs and intended use

- Compare participation and recency with line width, thickness, totals, tooltips and Data Window values.
- No alerts are included; the author suggests small-timeframe use with infrequent chart changes.

## Parameters and stated settings

- Four line thicknesses encode age. An example 20-level double profile needs 42 labels against a 500-label limit.
- The author reports handling upwards of 60K updates per profile, not a guaranteed capacity.
- Choose tick/update-count mode and a timeframe reset (chart timeframe resets each new bar). Caller first-update policy is explicitly excluded until direction is known; this is not claimed as default-code parity.

## Failure modes and caveats

- Live-only state cannot be reconstructed from historical OHLCV.
- Uptick/downtick classification can misclassify true aggressor flow; prolonged accumulation may exhaust memory.

## Missing information and implementation boundary

- Precise rebinning boundaries, age-to-thickness thresholds and trend-reset implementations are not fully disclosed.

## Data requirements

Required inputs: live timestamped price and volume chart updates.

Repository input-class support: unavailable or unresolved. Required live updates, detailed lower-timeframe observations or multi-asset inputs are not supplied by ordinary historical chart bars.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: required_data, risks

```text
The indicator only works in real time.
```

### E2: mechanism, parameters, readiness

```text
When price does not move between chart updates, the last known direction is used.
```

### E3: parameters

```text
Four thicknesses are used
```

### E4: parameters

```text
20-level double-sided profile with totals requires 42 labels.
```

### E5: parameters

```text
last 500 labels
```

### E6: parameters

```text
upwards of 60K updates per profile
```

### E7: outputs_and_use

```text
I have not included alerts in the script.
```

### E8: mechanism, parameters, readiness

```text
total value of down/up values for the profile appears at the top.
```

### E9: mechanism, parameters, readiness

```text
Values can represent the simple total of ​volume or ticks at each level, or their delta.
```

### E10: mechanism, parameters, readiness

```text
the profile will reset on each new chart bar.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_profile](../tv_method_market_profile.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_tng177sv_realtime_5d_profile_lucf](../tv_tng177sv_realtime_5d_profile_lucf.md)

## Source

https://www.tradingview.com/script/tNG177SV-Realtime-5D-Profile-LucF/

Publication ID: tNG177SV. Source SHA-256: 734c3d5fba81a8f55e649e9c2d9db64bb92e53e5b443a05fab58d8f4983bc8eb. Raw-description SHA-256: f40732fc4cfeeb934d4ab788ab69fb6dda28a616ed338ef27ad426c6b79f534d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
