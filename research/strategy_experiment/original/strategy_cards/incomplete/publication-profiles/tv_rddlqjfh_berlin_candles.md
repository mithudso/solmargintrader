---

id: tv_profile_rddlqjfh

name: "BERLIN Candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Retain a Heikin-Ashi-like trend view while keeping synthetic candle bodies inside actual price extremes and marking the true close."

registry_key: null

runner: null

evaluation: null

---

# BERLIN Candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Retain a Heikin-Ashi-like trend view while keeping synthetic candle bodies inside actual price extremes and marking the true close.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Open smoothing formula, baseline settings, color rules and exact initialization are missing.

- Open smoothing formula, baseline settings, color rules and exact initialization are missing.

## How it works

- Use a smoothed previous Heikin Ashi close as the new open and current Heikin Ashi close as the new close. Clamp both to the underlying bar's actual high/low, retain those real extremes as wicks and add a plus sign at the real close.

## Outputs and intended use

- Read synthetic direction alongside actual traded bounds and the close marker. Optional Ichimoku baseline and ATR annotations provide additional context.

## Parameters and stated settings

- ATR period is fourteen for latest-candle and data-window displays. The baseline is optional; open smoothing defaults are not disclosed.

## Failure modes and caveats

- Clamping reduces out-of-range synthetic prices but does not make the body executable market OHLC. Smoothing can still delay reversals.

## Missing information and implementation boundary

- Open smoothing formula, baseline settings, color rules and exact initialization are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the disclosed input class; source code and historical data parity have not been validated.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
using a smoothed out version of the previous Heikin Ashi candle close as the current BERLIN Candle open
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
setting hard limits for BERLIN Candle open and close values so that they can never exceed the high and low of the underlying japanese candlestick.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The close of the underlying japanese candlesticks are indicated with a plus-sign.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The addition of the 14 period ATR at the latest candle
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)
- [tv_rddlqjfh_berlin_candles](../tv_rddlqjfh_berlin_candles.md)

## Source

https://www.tradingview.com/script/RdDlqjfh-BERLIN-Candles/

Publication ID: RdDlqjfh. Source SHA-256: 07f41e260eb14a790e0008d85cebd239c7fb1f0960bcab73e1496a9458a5c2c2. Raw-description SHA-256: 9591cefabdc337a7a1e7e2bd3f5cc379dbac4c47195368f47cc65644db38c8bd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
