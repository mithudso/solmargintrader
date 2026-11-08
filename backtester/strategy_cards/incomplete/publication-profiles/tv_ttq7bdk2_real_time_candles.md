---

id: tv_profile_ttq7bdk2

name: "real_time_candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "real_time_candles builds candle objects from live samples of prices or other financial series. It supports chart-synchronized candles and independently sampled time/count candles, exposing both their OHLC state and drawing helpers. Its financial uses include watching an oscillator change within a bar or examining short-lived price structures. This is not merely a graphics utility: its central output is sampled financial-series candles, although the claimed trading edge is not validated by the description."

registry_key: null

runner: null

evaluation: null

---

# real_time_candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

real_time_candles builds candle objects from live samples of prices or other financial series. It supports chart-synchronized candles and independently sampled time/count candles, exposing both their OHLC state and drawing helpers. Its financial uses include watching an oscillator change within a bar or examining short-lived price structures. This is not merely a graphics utility: its central output is sampled financial-series candles, although the claimed trading edge is not validated by the description.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for synchronized ordinary sampled-source OHLC under the documented current/history state and carried-close reset. Custom-time units/overshoot, Heikin-Ashi and EMA implementations remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow chart-synchronized ordinary sampled-source OHLC: select candlestick style and wait_for_sync; begin at a new chart bar. Within a bar retain current source as Close, maximum/minimum of included source samples as High/Low and starting sample as Open. At subsequent chart boundaries the shown reset carries prior sampled Close into Open, seeds the new sample buffer with that Open and appends new observations; thus the carry is included in High/Low. Current object is index0 and completed objects are inserted at index1.
- Capture source values, elapsed milliseconds and sequential update indices with persistent intrabar state.
- Update the current candle at array index zero and preserve completed candles at later indices. Custom candles close when accumulated update count or elapsed time reaches the configured threshold.
- Expose candle arrays, single objects or tuples, standard/Heikin-Ashi styles, extracted components and EMA/drawing methods.

## Outputs and intended use

- Use candles as inputs for custom indicators or render them with time/bar-index coordinates and optional moving averages.
- The example labelled fast RSI actually extracts candle closes; it does not itself calculate a custom-timeframe RSI.

## Parameters and stated settings

- Examples include RSI length 14, 20-second candles with EMA 9 and 15-update candles. Recommended history is 5000 bars and drawing limits 500 each.
- Timezone display offsets span -12 to +12; tied_open connects a new open to the preceding close.
- Choose source (default close), ordinary CandleType.candlestick and synchronization to a new bar. For exact parity preserve the shown carried-close reset; starting/reconnection behavior outside synchronized complete bars is not specified.

## Failure modes and caveats

- Historical bars cannot recover missing live updates, so custom candles cannot be historically backtested from this source.
- An execution update is not necessarily a single exchange trade.

## Missing information and implementation boundary

- Full boundary overshoot/gap behavior, Heikin-Ashi recurrence and sampling-time units need clarification; the shown time threshold compares seconds against a duration documented in milliseconds.

## Data requirements

Required inputs: live timestamped sampled price or indicator updates.

Repository input-class support: unavailable or unresolved. Required live updates, detailed lower-timeframe observations or multi-asset inputs are not supplied by ordinary historical chart bars.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
number_of_seconds = 20
```

### E2: parameters

```text
ema_period = 9
```

### E3: parameters

```text
number_of_ticks = 15
```

### E4: parameters

```text
ta.rsi(close, 14)
```

### E5: parameters

```text
max_bars_back = 5000
```

### E6: parameters

```text
max_lines_count = 500, max_boxes_count = 500, and max_labels_count = 500
```

### E7: parameters

```text
Timezone offset from UTC (-12 to +12)
```

### E8: missing_information

```text
Time elapsed since the previous tick in milliseconds
```

### E9: mechanism, missing_information

```text
SampleType.Time => cumulative_time_delta >= settings.number_of_seconds
```

### E10: risks

```text
Custom timeframe candles cannot be backtested
```

### E11: mechanism, parameters, readiness

```text
Chart-Time Candles: Generate real-time OHLC data for any variable
```

### E12: mechanism, parameters, readiness

```text
Whether to wait for a new bar before starting
```

### E13: mechanism, parameters, readiness

```text
Open := Close
    price.push(Open)
```

### E14: mechanism, parameters, readiness

```text
Highest price of the candle
```

### E15: mechanism, parameters, readiness

```text
Lowest price of the candle
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)

## Source

https://www.tradingview.com/script/ttq7BdK2-real-time-candles/

Publication ID: ttq7BdK2. Source SHA-256: 00df0bc8ea6fc4ccfdddc631a38e260c81d730ddc5d4b8c0010fab62b39cfa86. Raw-description SHA-256: 3b482d0bd2c2d01f1bc4cb121c54e51563060491f76d4cd2813188483e302363.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
