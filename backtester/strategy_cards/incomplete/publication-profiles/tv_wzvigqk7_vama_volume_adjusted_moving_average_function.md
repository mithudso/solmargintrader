---

id: tv_profile_wzvigqk7

name: "VAMA Volume Adjusted Moving Average Function"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Make a moving average advance according to accumulated volume participation rather than a fixed number of elapsed bars."

registry_key: null

runner: null

evaluation: null

---

# VAMA Volume Adjusted Moving Average Function

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

Make a moving average advance according to accumulated volume participation rather than a fixed number of elapsed bars.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The exact weighting/interpolation, bucket truncation, zero-volume treatment and initialization require the absent code or prior publication.

- The exact weighting/interpolation, bucket truncation, zero-volume treatment and initialization require the absent code or prior publication.

## How it works

- Estimate average volume over a sample, form volume-ratio buckets and accumulate enough buckets to reach the requested VAMA length. A strict mode keeps adding bars until the volume target is met.

## Outputs and intended use

- The function is demonstrated as a fast/slow moving-average pair for live research. The source explicitly says the example is not an actual strategy and notes limitations in redrawing past values on time charts.

## Parameters and stated settings

- SampleN sets the volume sample and zero uses all bars. Source, VAMA length, volume-increment factor and strictness are configurable; numerical defaults are not given.

## Failure modes and caveats

- Volume-based windows vary in calendar duration, and live historical redrawing limitations can complicate comparisons with ordinary time-window averages.

## Missing information and implementation boundary

- The exact weighting/interpolation, bucket truncation, zero-volume treatment and initialization require the absent code or prior publication.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the disclosed calculation class; this is not a verified implementation or historical-feed coverage claim.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
VAMA utilizes a period length that is based on volume increments rather than time.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
N volume bars used as sample to calculate average volume , 0 equals all bars.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Must meet desired volume requirements, even if number of bars has to exceed VAMA Length to do it.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wzvigqk7_vama_volume_adjusted_moving_average_function](../tv_wzvigqk7_vama_volume_adjusted_moving_average_function.md)

## Source

https://www.tradingview.com/script/WzvigqK7-VAMA-Volume-Adjusted-Moving-Average-Function/

Publication ID: WzvigqK7. Source SHA-256: 9dbabe197dbad1e6012d06874f2cbbd86826839809bcdcbca61e947386e52f13. Raw-description SHA-256: 57f33b136ac6337c2a1ca3cff969aaa839492cdf694c949ff9e52ac66a86b554.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
