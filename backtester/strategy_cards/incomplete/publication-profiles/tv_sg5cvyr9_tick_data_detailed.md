---

id: tv_profile_sg5cvyr9

name: "Tick Data Detailed"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Tick Data Detailed accumulates realtime price-update volume into size buckets and compares current-bar detail with cumulative observations. It aims to distinguish large and small activity and flag disagreement between candle direction and classified buy/sell volume. The author’s whale/small-trader interpretation is speculative: update size does not identify a participant, and the source explicitly limits the tool to realtime bars."

registry_key: null

runner: null

evaluation: null

---

# Tick Data Detailed

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Tick Data Detailed accumulates realtime price-update volume into size buckets and compares current-bar detail with cumulative observations. It aims to distinguish large and small activity and flag disagreement between candle direction and classified buy/sell volume. The author’s whale/small-trader interpretation is speculative: update size does not identify a participant, and the source explicitly limits the tool to realtime bars.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Realtime buy/sell classification and update-volume/reset behavior are undefined.

- Realtime buy/sell classification and update-volume/reset behavior are undefined.

## How it works

- At each realtime tick, inspect volume, multiply by close to estimate notional volume and assign tick count/volume to a configured size zone.
- Maintain separate current-bar and cumulative tables; mark an anomaly when candle direction conflicts with the larger buy/sell volume component.

## Outputs and intended use

- Read bucket counts/notional totals, total-text direction color and exclamation marks for volume/candle disagreement.

## Parameters and stated settings

- Seven default zones have boundaries 0, 10000, 20000, 50000, 100000, 200000 and 400000, with an open-ended top bucket; levels and colors are adjustable.

## Failure modes and caveats

- Realtime-only operation prevents ordinary historical OHLCV reconstruction. Analytical: feed updates may aggregate transactions and the notional conversion depends on volume units.

## Missing information and implementation boundary

- Buy/sell tick attribution, volume-delta calculation, reset/reload behavior and contract-volume treatment are missing.

## Data requirements

Required inputs: realtime tick/update price and volume stream.

Repository input-class support: unavailable or unresolved. Requires realtime update-level observations; historical candle OHLCV lacks the observed sequence.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: risks, readiness

```text
only works on real-time bars too.
```

### E2: parameters, readiness

```text
There are 7 levels/zones
```

### E3: parameters, readiness

```text
0 - 10.000
10.000 - 20.000
20.000 - 50.000
50.000 - 100.000
100.000 - 200.000
200.000 - 400.000
> 400.000
```

### E4: mechanism, readiness

```text
volume is multiplied by close price
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_sg5cvyr9_tick_data_detailed](../../../strategy_research/tv_sg5cvyr9_tick_data_detailed.md)

## Source

https://www.tradingview.com/script/SG5CvYR9-Tick-Data-Detailed/

Publication ID: SG5CvYR9. Source SHA-256: 792c1ac57ec45eb246f5a3bb8f6780fbfe9113d2582cb07549e357e7ab9aad2e. Raw-description SHA-256: cff85710bcf5e722151dcfb1f5d5fb25953c483e008c72db7d6ae36a373fa552.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
