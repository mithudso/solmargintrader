---

id: tv_profile_biczyhq0

name: "ta"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Supply reusable technical-analysis,performance and volatility-stop functions beyond the built-ins described at publication time."

registry_key: null

runner: null

evaluation: null

---

# ta

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Supply reusable technical-analysis,performance and volatility-stop functions beyond the built-ins described at publication time.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for conditional extrema, percentage change and Donchian ranges with caller initialization/zero/NA conventions; complete library and removed historical exports remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow documented functions: highestSince(cond,source=high) resets its running extreme when cond is true and otherwise takes max(previous,source); lowestSince(source=low) analogously takes min. changePercent(new,old)=100*(new-old)/old. Donchian(length) returns max(high), min(low) over that window and their midpoint. Caller must explicitly choose pre-first-condition initialization, incomplete-window/NA behavior and old=0 handling because those edge conventions are unprinted. These functions are independent of undisclosed adaptive recurrences elsewhere in the library.
- Expose named oscillator/trend/filter functions and alternate averages/ATR/Supertrend accepting dynamic lengths. Add timestamp-based CAGR,condition-reset extrema,Donchian ranges,matched-offset relative volume and ATR trailing stops. Preserve version history: all-time extrema and trima2 listed earlier are explicitly removed in the final documented version.

## Outputs and intended use

- Return scalars or tuples for importer-defined indicators/strategies; the library does not itself prescribe entries. RelativeVolume returns current,matched historical average and their ratio,while stop functions return stop plus direction. CAGR compares endpoints and ignores drawdowns.

## Parameters and stated settings

- CAGR requires at least one day. RelativeVolume defaults daily anchor,cumulative true and realtime adjustment false. Volatility-stop ATR factor defaults1; Supertrend wick reversal defaults false. Ichimoku defaults9/26/52 and EOM divisor10000. Other lengths are caller inputs.

## Failure modes and caveats

- Dynamic lengths need valid ranges and consistent initialization. Version-specific exports can break callers; shifted Ichimoku plots must not be interpreted as future-known data. The historical no-lookahead claim for extrema is not independently verified.

## Missing information and implementation boundary

- Most named-function equations,initialization,zero/NA handling,relative-volume realtime estimator and stop ratchet/reversal details are absent; descriptive signatures alone do not reproduce the entire library.

## Data requirements

Required inputs: ohlcv or caller numerical series, timestamps and condition inputs.

Repository input-class support: available. Chart-derived numerical series and caller conditions suffice; no proprietary feed is intrinsically required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, readiness

```text
technical ​analysis functions calculating values for which no Pine built-in exists.
```

### E2: purpose, mechanism, parameters, readiness

```text
minimum of one day
```

### E3: purpose, mechanism, parameters, readiness

```text
Default is "D".
```

### E4: purpose, mechanism, parameters, readiness

```text
The default is `true`.
```

### E5: purpose, mechanism, parameters, readiness

```text
The default is `false`.
```

### E6: purpose, mechanism, parameters, readiness

```text
The default is 9 periods
```

### E7: purpose, mechanism, parameters, readiness

```text
The default is 26 periods
```

### E8: purpose, mechanism, parameters, readiness

```text
The default is 52 periods
```

### E9: purpose, mechanism, parameters, readiness

```text
The default is 10000.
```

### E10: purpose, mechanism, parameters, readiness

```text
Removed Functions:
```

### E11: mechanism, parameters, readiness

```text
[b]highestSince(cond, source)[/b]
  Tracks the highest value of a series since the last occurrence of a condition.
  Parameters:
    [b]cond (bool)[/b]: (series bool) A condition which, when `true`, resets the tracking of the highest `source`.
    [b]source (float)[/b]: (series int/float) Series of values to process. Optional. The default is `high`.
  Returns: (float) The highest `source` value since the last time the `cond` was `true`.
```

### E12: mechanism, parameters, readiness

```text
[b]lowestSince(cond, source)[/b]
  Tracks the lowest value of a series since the last occurrence of a condition.
  Parameters:
    [b]cond (bool)[/b]: (series bool) A condition which, when `true`, resets the tracking of the lowest `source`.
    [b]source (float)[/b]: (series int/float) Series of values to process. Optional. The default is `low`.
  Returns: (float) The lowest `source` value since the last time the `cond` was `true`.
```

### E13: mechanism, parameters, readiness

```text
[b]changePercent(newValue, oldValue)[/b]
  Calculates the percentage difference between two distinct values.
  Parameters:
    [b]newValue (float)[/b]: (series int/float) The current value.
    [b]oldValue (float)[/b]: (series int/float) The previous value.
  Returns: (float) The percentage change from the `oldValue` to the `newValue`.
```

### E14: mechanism, parameters, readiness

```text
[b]donchian(length)[/b]
  Calculates the values of a Donchian Channel using `high` and `low` over a given `length`.
  Parameters:
    [b]length (int)[/b]: (series int) Number of bars (length).
  Returns: ([][float, float, float[]]) A tuple containing the channel high, low, and median, respectively.
```

## Source

https://www.tradingview.com/script/BICzyhq0-ta/

Publication ID: BICzyhq0. Source SHA-256: 8472c0f7fe3535abda91ce250964eb6798349004a3c1d9e75ee2b87013477a30. Raw-description SHA-256: 5506943a7881c3f11f47806be853e9f0849e6dd5f79bd567d25432d3eb742e9e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
