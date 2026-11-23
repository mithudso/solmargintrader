---

id: tv_profile_1uw4irtx

name: "All-Time High/Low Widget"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Keep historical price extremes visible and show how the current market relates to those extremes, with notifications when an extreme is exceeded."

registry_key: null

runner: null

evaluation: null

---

# All-Time High/Low Widget

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Keep historical price extremes visible and show how the current market relates to those extremes, with notifications when an extreme is exceeded.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: The source does not state whether extremes use wicks or closes, how distance is scaled, whether alerts wait for the close, or how incomplete history is handled.

- The source does not state whether extremes use wicks or closes, how distance is scaled, whether alerts wait for the close, or how incomplete history is handled.

## How it works

- Track the highest and lowest values in the history accessible to the script. Report when each extreme occurred and the current distance from it.

## Outputs and intended use

- Plot extreme levels, inspect timing/distance statistics and optionally create breakout alerts. These are monitoring outputs; they do not prescribe how to enter or manage a breakout trade.

## Parameters and stated settings

- Level plotting and breakout notifications are disclosed capabilities; numerical settings and a history-start control are not listed.

## Failure modes and caveats

- An all-time label can overstate the coverage of a limited chart dataset. Intrabar breaches and close-confirmed breakouts are different events.

## Missing information and implementation boundary

- The source does not state whether extremes use wicks or closes, how distance is scaled, whether alerts wait for the close, or how incomplete history is handled.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described calculation uses chart price/volume history. This establishes input class only, not a verified implementation or cached market coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
It's a pretty simple widget to track all-time high and all-time low values.
```

### E2: purpose, mechanism, outputs_and_use, parameters

```text
You can plot the levels and display some stats when all-time happened and how far away are we at this moment.
```

### E3: purpose, mechanism, outputs_and_use, parameters

```text
Also, you can create alerts to get notified on ATH/ATL breakout.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_1uw4irtx_all_time_high_low_widget](../../../strategy_research/tv_1uw4irtx_all_time_high_low_widget.md)

## Source

https://www.tradingview.com/script/1UW4IRTx-All-Time-High-Low-Widget/

Publication ID: 1UW4IRTx. Source SHA-256: 541be8ab3ba05726001aa7dfc24a0edd5fb90739126f07147ae66f0a361d9c64. Raw-description SHA-256: b140079206c109eadf5d04ed5fcee5e8e75684bf4a6ed470bdc8653bd6d78b8b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
