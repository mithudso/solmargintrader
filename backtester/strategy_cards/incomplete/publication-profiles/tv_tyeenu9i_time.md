---

id: tv_profile_tyeenu9i

name: "Time"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Time includes condition-persistence timing infrastructure explicitly intended to delay financial exits until an exit condition has remained true long enough. Its example also turns a price-movement condition into a time-delayed chart alert. Generic date formatting and timeframe conversion accompany this financial use, but the core timer cannot be dismissed as a text-formatting utility. The source establishes the interface and intended behavior while contradicting its duration units and omitting enough implementation detail that exact live persistence cannot be reproduced confidently."

registry_key: null

runner: null

evaluation: null

---

# Time

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Time includes condition-persistence timing infrastructure explicitly intended to delay financial exits until an exit condition has remained true long enough. Its example also turns a price-movement condition into a time-delayed chart alert. Generic date formatting and timeframe conversion accompany this financial use, but the core timer cannot be dismissed as a text-formatting utility. The source establishes the interface and intended behavior while contradicting its duration units and omitting enough implementation detail that exact live persistence cannot be reproduced confidently.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Financial timer purpose is explicit, but the seconds/milliseconds contradiction and omitted reset/intrabar recurrence block an exact persistent timer.

- The timer duration units conflict between description and Returns.
- Timer initialization/reset precedence and live update recurrence are not supplied.

## How it works

- secondsSince(cond,resetCond) times how long cond remains continuously true; resetCond true resets its duration. Persistent intrabar state is described through varip so timing can span updates and bars.
- The financial example starts a timer when high minus open, expressed in ticks, exceeds a user input; after the selected duration is exceeded a label turns red to simulate a delayed alert. The intended exit use similarly waits for an exit condition to persist.
- Other exports format timestamps, offset drawing times and convert elapsed durations/timeframe strings; they do not resolve timer initialization or its contradictory time units.

## Outputs and intended use

- Elapsed condition duration and a delayed high/open movement label support financial condition timing; no broker exit order is implemented.

## Parameters and stated settings

- Condition and reset condition are Boolean series. Example price-movement tick threshold and duration are user-selected; no numeric defaults are stated.
- Documentation calls the duration milliseconds in the description but seconds in Returns. Do not silently choose one as verified implementation units.

## Failure modes and caveats

- Intrabar elapsed-time behavior cannot be reconstructed from historical OHLC bars.
- Timer behavior during feed gaps, restarts or brief false intervals depends on unprovided implementation details; the example is not a verified execution delay.

## Missing information and implementation boundary

- Timer unit conflict, initialization/reset precedence, false-condition handling and intrabar time-source/update details are unresolved.

## Data requirements

Required inputs: live timestamped financial condition updates, price high/open and tick size for the example.

Repository input-class support: unavailable or unresolved. Live condition-update timing and clock behavior are not supplied by historical chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
enable trades to exit only when the exit condition has been true for a period of time
```

### E2: purpose, mechanism, readiness

```text
If the difference between the high and the open in ticks exceeds the input value, a timer starts and will turn the label red once the input time is exceeded
```

### E3: purpose, mechanism, readiness

```text
The duration in milliseconds that a condition has been true.
```

### E4: purpose, mechanism, readiness

```text
Returns: The duration in seconds for which `cond` is continuously true.
```

### E5: purpose, mechanism, readiness

```text
When `true`, the duration resets.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)

## Source

https://www.tradingview.com/script/tyeeNU9I-Time/

Publication ID: tyeeNU9I. Source SHA-256: 43630f5e866e13380db93de011c4c925f734eab128f18a5fe7920a85ad0b9982. Raw-description SHA-256: 24e0ed0c66e3dc119a71bad8bdba3fe4ba664fe73f900e3dc39a9994e521a6a5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
