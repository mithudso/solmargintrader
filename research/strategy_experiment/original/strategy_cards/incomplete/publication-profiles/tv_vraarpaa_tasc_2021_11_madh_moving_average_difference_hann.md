---

id: tv_profile_vraarpaa

name: "TASC 2021.11 MADH Moving Average Difference, Hann"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Produce a smooth band-limited momentum oscillator from the difference between differently smoothed price components."

registry_key: null

runner: null

evaluation: null

---

# TASC 2021.11 MADH Moving Average Difference, Hann

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Produce a smooth band-limited momentum oscillator from the difference between differently smoothed price components.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Hann coefficient normalization, precise ROC denominator, long-filter relation, initialization and crossover/exit rules are not given.

- Hann coefficient normalization, precise ROC denominator, long-filter relation, initialization and crossover/exit rules are not given.

## How it works

- Apply two Hann-windowed finite-impulse-response filters using a short length and a dominant-cycle length, then pass their outputs into a rate-of-change calculation returned by madh().

## Outputs and intended use

- Color fill by zero-line position or by oscillator rise/fall. These alternatives distinguish signed trend context from immediate momentum; neither is a complete trading plan.

## Parameters and stated settings

- Short Length defaults eight, Dominant Cycle twenty-seven and ZeroCross is the default coloring mode. Price source and Momentum coloring are selectable.

## Failure modes and caveats

- The source suggests the dominant-cycle input may be a placeholder for adaptation; it does not establish automatic cycle detection. Smoothness still entails response tradeoffs and does not demonstrate profitability.

## Missing information and implementation boundary

- Hann coefficient normalization, precise ROC denominator, long-filter relation, initialization and crossover/exit rules are not given.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supplies the described input class; this does not verify code parity, complete historical data or measured returns.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
A "Short Length" with a default of 8
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The "Dominant Cycle", originally set at 27
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
"ZeroCross", the default
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
two independent Hann windowed FIR filters having two different periods
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
These are then passed to a "rate of change" calculation
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_vraarpaa_tasc_2021_11_madh_moving_average_difference_hann](../tv_vraarpaa_tasc_2021_11_madh_moving_average_difference_hann.md)

## Source

https://www.tradingview.com/script/vraaRpAA-TASC-2021-11-MADH-Moving-Average-Difference-Hann/

Publication ID: vraaRpAA. Source SHA-256: 3dd60d9805be7cdf1641ed1d01aa241947340772312027fb2de12959011c2465. Raw-description SHA-256: ab5c57255497e482474462cc57ae9d31c0c401fb966d632e3ad8ea766da1fadf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
