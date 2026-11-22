---

id: tv_profile_cdu6e9rm

name: "Volume Footprint [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Footprint estimates how realtime volume is distributed across price intervals inside a candle. It automatically derives interval width from ATR or accepts a user width, then displays accumulated volume as absolute amounts or candle-volume shares. The tool’s purpose is local participation analysis, not identifying buyer/seller counterparties or guaranteeing a venue-accurate footprint."

registry_key: null

runner: null

evaluation: null

---

# Volume Footprint [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Footprint estimates how realtime volume is distributed across price intervals inside a candle. It automatically derives interval width from ATR or accepts a user width, then displays accumulated volume as absolute amounts or candle-volume shares. The tool’s purpose is local participation analysis, not identifying buyer/seller counterparties or guaranteeing a venue-accurate footprint.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Manual-width tick-volume histogram is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Separate candles into equally spaced price intervals using ATR-based or manual width and accumulate tick-data volume into them.
- Draw the completed footprint on confirmation of a new bar, with selectable box/gradient/regular styles.
- With supplied tick price/volume and caller bin width/origin/edges,assign ticks to price intervals and sum volume. Percent mode=100*bin_volume/candle_total for positive total. This unsigned histogram does not use candle direction as aggressor attribution; automatic width/feed behavior excluded.

## Outputs and intended use

- Inspect high-participation intervals within candles; gradient darkness corresponds to larger relative volume and trend colors reflect candle direction.
- Usable scope: Manual-width tick-volume histogram. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Method controls ATR versus manual width, Width supplies ATR period or interval size, and As Percent normalizes to total candle volume. Default display uses colored boxes.

## Failure modes and caveats

- Changing settings resets footprints; source suggests lower timeframes because new footprints appear on bar confirmation. Analytical: feed-update granularity limits reconstruction.

## Missing information and implementation boundary

- Tick-volume attribution, interval boundaries, ATR/default width, zero-volume handling and historical persistence are not fully defined.

## Data requirements

Required inputs: realtime tick/update price and volume data.

Repository input-class support: unavailable or unresolved. Tick observations are required; historical OHLCV alone cannot reconstruct the accumulated intervals.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
estimates a volume footprint using tick data.
```

### E2: risks, readiness

```text
changing the settings afterward will reset the volume footprint
```

### E3: outputs_and_use, readiness

```text
A new footprint will appear on the confirmation of a new bar
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
This indicator estimates a volume footprint using tick data. The script automatically separates a candle into equidistant intervals with a width obtained from the average true range or a user-given width.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
[*]As Percent: Returns the accumulated volume within each interval as a percentage of the total candle volume.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
This indicator estimates a volume footprint using tick data. The script automatically separates a candle into equidistant intervals with a width obtained from the average true range or a user-given width.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cdu6e9rm_volume_footprint_luxalgo](../tv_cdu6e9rm_volume_footprint_luxalgo.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/cdU6E9rm-Volume-Footprint-LuxAlgo/

Publication ID: cdU6E9rm. Source SHA-256: 689808d9b999cc8f3e815514ddad913007402155b70d671ed5d21a3e92b8bb46. Raw-description SHA-256: 0031005d0f00ca099352a2f2f113e8e734ba7a7705b99c2ac6e870f6daa99b4b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
