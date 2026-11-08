---

id: tv_profile_94iacmva

name: "MovingAverages"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "MovingAverages provides reusable averaging and filtering calculations for financial series, with special support for anchors, fractional lengths and long histories. Rather than inventing a new trading signal, it extends common smoothing tools so another indicator or strategy can reset calculations at events and choose a noninteger effective window. Its numerical and performance advantages are source assertions rather than independently measured results."

registry_key: null

runner: null

evaluation: null

---

# MovingAverages

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

MovingAverages provides reusable averaging and filtering calculations for financial series, with special support for anchors, fractional lengths and long histories. Rather than inventing a new trading signal, it extends common smoothing tools so another indicator or strategy can reset calculations at events and choose a noninteger effective window. Its numerical and performance advantages are source assertions rather than independently measured results.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Fractional-window interpolation and anchored incremental filter algorithms are undisclosed.

- Fractional-window interpolation and anchored incremental filter algorithms are undisclosed.

## How it works

- Incrementally update averages with interpolation and circular-buffer state instead of recomputing each historical window.
- Support classic price/volume averages, regression and ATR alongside several DSP filters and rate limiters.
- Reset on a supplied boolean anchor; optional session detection and anchor stabilization support sessional use. Kahan compensation is described for custom calculations.

## Outputs and intended use

- Import the functions into another financial script and consume their returned series; warmup values are returned and an omitted length continues until the next anchor.

## Parameters and stated settings

- The author claims O(1) updates and lengths up to 100k bars; the sample uses length 9.5.
- Common inputs are source, optional length, optional anchor and optional parity; parity can favor built-ins and can be disabled.

## Failure modes and caveats

- Analytical: custom and built-in behavior may differ around anchors and warmup; source-stated numerical closeness is not a verified guarantee.

## Missing information and implementation boundary

- Exact implementations, per-function restrictions, default lengths and verification of complexity/numerical claims require source code.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
fractional lengths up to 100k bars.
```

### E2: parameters, readiness

```text
length = 9.5
```

### E3: mechanism, parameters, readiness

```text
O(1) computation, fractional lengths, and 100k bars.
```

### E4: mechanism, readiness

```text
When no length is provided, the series continues indefinitely until a new anchor is set.
```

### E5: mechanism, readiness

```text
Kahan summation error compensation is used when calculating an average.
```

## Source

https://www.tradingview.com/script/94IaCMvA-MovingAverages/

Publication ID: 94IaCMvA. Source SHA-256: 7d56afeb4823276ebb7ee9dd368484e712037c4421c934652124de0d7afff9aa. Raw-description SHA-256: af0d1c3da609cc54c7fa8e29702debf12ea27d8e336ed36be1d42ee507e280f6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
