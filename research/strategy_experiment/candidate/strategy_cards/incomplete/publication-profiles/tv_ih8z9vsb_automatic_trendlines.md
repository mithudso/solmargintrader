---

id: tv_profile_ih8z9vsb

name: "Automatic Trendlines"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Maintain automatic support and resistance trendlines from detected swing lows and highs."

registry_key: null

runner: null

evaluation: null

---

# Automatic Trendlines

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Maintain automatic support and resistance trendlines from detected swing lows and highs.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Swing left/right settings, trend-pair replacement, extension logic, breakout handling and risk rules are not documented.

- Swing left/right settings, trend-pair replacement, extension logic, breakout handling and risk rules are not documented.

## How it works

- Detect swings and connect a pair of highs for resistance and a pair of lows for support. Multiple line segments distinguish pivot connections, the moment a trend became detectable and dashed joins that complete the visual line.

## Outputs and intended use

- Read the active pair of trendlines with their pivot circles and detection timing. The display shows structure, not a prescribed breakout trade.

## Parameters and stated settings

- Swing detection can be adjusted. Increasing rightbars delays confirmation while the author says it improves pivot quality; no numerical default is given.

## Failure modes and caveats

- Pivot confirmation is delayed. Old dashed segments are removed when drawing limits are reached, so the historical chart can lose visual context.

## Missing information and implementation boundary

- Swing left/right settings, trend-pair replacement, extension logic, breakout handling and risk rules are not documented.

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
The resistance trend is shown with red circles and is created by joining swing highs together.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The higher you set rightbars, the more lag you will have before a trend is detected.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
When the limit is reached, the oldest line will be removed so the newest can be drawn.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ih8z9vsb_automatic_trendlines](../tv_ih8z9vsb_automatic_trendlines.md)

## Source

https://www.tradingview.com/script/ih8Z9vSB-Automatic-Trendlines/

Publication ID: ih8Z9vSB. Source SHA-256: a6f5bfc3b9104e5d88abcca3d4a725d5c5b5080fa3d88349abc5ec73ff8be239. Raw-description SHA-256: 57e8eb2c2b15ba04678866b023c66eb7a4c744dc895a68506bf42f31852fe645.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
