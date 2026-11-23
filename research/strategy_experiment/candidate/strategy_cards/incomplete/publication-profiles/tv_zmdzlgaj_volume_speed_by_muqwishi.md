---

id: tv_profile_zmdzlgaj

name: "Volume Speed [By MUQWISHI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume Speed displays directional volume dominance and an estimated rate of volume arrival over a chosen lower-timeframe window. It aims to provide a compact tape-like activity widget, with a visual flash when a volume event is unusually large relative to average. The description emphasizes flow speed and up/down totals but does not disclose their exact calculation. Its current-update timing information suggests live monitoring, so a historical candle-only reconstruction should not be assumed. The author explicitly advises against using it as the primary basis of a trade."

registry_key: null

runner: null

evaluation: null

---

# Volume Speed [By MUQWISHI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Speed displays directional volume dominance and an estimated rate of volume arrival over a chosen lower-timeframe window. It aims to provide a compact tape-like activity widget, with a visual flash when a volume event is unusually large relative to average. The description emphasizes flow speed and up/down totals but does not disclose their exact calculation. Its current-update timing information suggests live monitoring, so a historical candle-only reconstruction should not be assumed. The author explicitly advises against using it as the primary basis of a trade.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Directional-volume allocation and speed/average computations are undisclosed.

## How it works

- Fetch a selected lower timeframe, aggregate up/down volume over a chosen bar count and estimate average flow speed.
- Compare an individual volume event with an average multiple to trigger a brief flash.

## Outputs and intended use

- Dynamic scale bar, large-volume notice, speed tooltip with extrema/update age and length/timeframe information support activity observation.

## Parameters and stated settings

- Flash lasts three seconds; multiplier example two means twice average.
- Timezone, widget layout, colors, LTF, count and volume-versus-price-volume selection are inputs.

## Failure modes and caveats

- Directional volume and speed are proxies with undisclosed denominators.
- Feed update cadence and lower-timeframe depth can materially change readings.

## Missing information and implementation boundary

- Buy/sell assignment, volume-speed unit/window, average formula, reset/history behavior and defaults are absent.

## Data requirements

Required inputs: lower-timeframe ohlcv, live feed timing for speed/update display.

Repository input-class support: unavailable or unresolved. Requires intrabar volume and possibly live timing beyond historical chart OHLCV; coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
flash gradually for 3 seconds
```

### E2: parameters

```text
2 → means double the average volume.
```

### E3: mechanism, readiness

```text
speed of the average volume flow
```

### E4: required_data

```text
Fetch data from the selected lower timeframe.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zmdzlgaj_volume_speed_by_muqwishi](../tv_zmdzlgaj_volume_speed_by_muqwishi.md)

## Source

https://www.tradingview.com/script/ZMdZlGaJ-Volume-Speed-By-MUQWISHI/

Publication ID: ZMdZlGaJ. Source SHA-256: f3c66bb997d123709d903d9cf6b46a5b4303f3eed44bb68b7f79f762fbfd71a1. Raw-description SHA-256: 6f4c43fbe167203c72d9c988ef45e6272ecc601db738cfa7273e0ed8bbd3bd06.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
