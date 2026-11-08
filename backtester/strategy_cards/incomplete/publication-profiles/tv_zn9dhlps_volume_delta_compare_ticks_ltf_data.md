---

id: tv_profile_zn9dhlps

name: "Volume Delta Compare [Ticks ~ LTF data]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Delta Compare contrasts live-update and lower-timeframe estimates of directional volume. Its purpose is to show why the same chart candle can yield different delta values depending on observation granularity. It preserves a neutral category instead of forcing unchanged-price volume into a directional side. The outputs describe price-direction-classified volume rather than verified exchange aggressor flow, and the live path loses accumulated information when re-executed."

registry_key: null

runner: null

evaluation: null

---

# Volume Delta Compare [Ticks ~ LTF data]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Delta Compare contrasts live-update and lower-timeframe estimates of directional volume. Its purpose is to show why the same chart candle can yield different delta values depending on observation granularity. It preserves a neutral category instead of forcing unchanged-price volume into a directional side. The outputs describe price-direction-classified volume rather than verified exchange aggressor flow, and the live path loses accumulated information when re-executed.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The directional allocation and delta computation are explicitly defined.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Assign incremental live volume to up, down or neutral according to the direction of the observed price change.
- For the lower-timeframe path assign each sub-bar volume by its price movement, which can disagree with the intrabar sequence.
- Subtract down from up volume for delta and sum delta for cumulative delta; compare candle direction with delta sign for divergence colors.

## Outputs and intended use

- View category columns, delta stepline, cumulative-only view and per-bar/tick details.
- Choose whether live calculation begins immediately on a partially formed bar or waits for a fresh bar.

## Parameters and stated settings

- Lower-timeframe choices are 1,5,10,15,30 seconds or one minute. Detail text stops before a 4096-character limit.

## Failure modes and caveats

- Live history is unrecoverable after reset; lower-timeframe aggregation hides internal reversals.
- An update need not represent one trade, despite the tick terminology.

## Missing information and implementation boundary

- Cumulative reset and live first-update baseline require care; these do not prevent reproducing the explicitly described directional-volume/delta computation.

## Data requirements

Required inputs: live price/volume updates, lower-timeframe OHLCV.

Repository input-class support: unavailable or unresolved. Calendar or detailed live/lower-timeframe data are not available from ordinary chart bars.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
UP volume (uV): volume when price rises
```

### E2: mechanism

```text
DOWN volume (dV): volume when price falls
```

### E3: mechanism

```text
NEUTRAL volume (nV): volume when price stays the same
```

### E4: mechanism

```text
Volume Delta (ΔV): uV minus dV
```

### E5: mechanism

```text
Cumulative Delta Volume (cΔV): sum of ΔV
```

### E6: parameters

```text
1, 5, 10, 15, 30 Seconds or 1 minute
```

### E7: parameters

```text
string max_length = 4096 limit
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../tv_method_volume_delta.md)
- [tv_zn9dhlps_volume_delta_compare_ticks_ltf_data](../tv_zn9dhlps_volume_delta_compare_ticks_ltf_data.md)

## Source

https://www.tradingview.com/script/zn9dhLPS-Volume-Delta-Compare-Ticks-LTF-data/

Publication ID: zn9dhLPS. Source SHA-256: 51cac88512187ddaf5f63f863b5516883f8927bb4da6408a824616532220ec57. Raw-description SHA-256: 5afb76535c8a4fa3ebf64a8626d5b1b96b0f9bf4f18111b778872b49e35d12f1.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
