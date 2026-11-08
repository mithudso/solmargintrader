---

id: tv_profile_mombnm8e

name: "Tick CVD [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Accumulate a live tick-rule estimate of cumulative volume delta alongside a tick-oriented price display."

registry_key: null

runner: null

evaluation: null

---

# Tick CVD [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Accumulate a live tick-rule estimate of cumulative volume delta alongside a tick-oriented price display.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Unchanged-tick handling, volume increments, reset/persistence, peak detection and event deduplication are missing. Historical tick entitlement claims are dated prose, not verified current access.

- Unchanged-tick handling, volume increments, reset/persistence, peak detection and event deduplication are missing. Historical tick entitlement claims are dated prose, not verified current access.

## How it works

- Record observed live ticks, treat up ticks as buying volume and down ticks as selling volume, accumulate delta/CVD and calculate optional tick-based HMA/WMA/EMA/SMA. Identify price/CVD peaks and troughs.

## Outputs and intended use

- Display price and CVD as lines/candles, delta as wavy lines or sized/color-intensity boxes, and key levels/average references. Price color compares with script-load origin, while CVD color compares with zero.

## Parameters and stated settings

- Average type, presentation and efficiency mode are configurable. Efficiency mode reduces extra visuals in fast markets; default lengths/reset horizon are not stated.

## Failure modes and caveats

- Uptick/downtick classification is a proxy, not verified bid/ask aggression. The author acknowledges tick aggregation, and observed history depends on loading time and delivered updates.

## Missing information and implementation boundary

- Unchanged-tick handling, volume increments, reset/persistence, peak detection and event deduplication are missing. Historical tick entitlement claims are dated prose, not verified current access.

## Data requirements

Required inputs: live ordered price and volume tick updates.

Repository input-class support: unavailable or unresolved. An observed live tick stream is required and cannot be reconstructed from saved OHLCV candles.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
it records up ticks as buying volume and down ticks as selling volume.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
tick aggregation can occur.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Green price tick graph = price is greater than its origin point (first script load)
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
HMA, WMA, EMA, SMA.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../tv_method_volume_delta.md)
- [tv_mombnm8e_tick_cvd_kioseff_trading](../tv_mombnm8e_tick_cvd_kioseff_trading.md)

## Source

https://www.tradingview.com/script/moMbNm8e-Tick-CVD-Kioseff-Trading/

Publication ID: moMbNm8e. Source SHA-256: 80df2b362c7604a5f82abfa2d31cdb3359bca46b05ea91cf02fe0d5a14b7bfcb. Raw-description SHA-256: ee927b8b01e3d837f81c7a7654a50b6cab02b4d1934fffb728db5a7bf97499bf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
