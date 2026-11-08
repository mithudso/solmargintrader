---

id: tv_profile_gqklw3yv

name: "TASC 2026.05 The AutoTune Filter"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "AutoTune Filter estimates a dominant cycle from negative autocorrelation of high-pass-filtered data and uses that estimate to tune a bandpass filter. It aims to preserve cycle alignment while avoiding abrupt center-period changes. The author proposes turning-point context from the tuned filter’s rate of change, but cycle structure in recent data does not guarantee the next market oscillation."

registry_key: null

runner: null

evaluation: null

---

# TASC 2026.05 The AutoTune Filter

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

AutoTune Filter estimates a dominant cycle from negative autocorrelation of high-pass-filtered data and uses that estimate to tune a bandpass filter. It aims to preserve cycle alignment while avoiding abrupt center-period changes. The author proposes turning-point context from the tuned filter’s rate of change, but cycle structure in recent data does not guarantee the next market oscillation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Highpass and bandpass recursions/bandwidth, ACF estimator/window endpoints, initialization and window default are not provided.

- Highpass and bandpass recursions/bandwidth, ACF estimator/window endpoints, initialization and window default are not provided.

## How it works

- Apply a two-pole highpass filter, calculate rolling autocorrelation over the cutoff/window length and choose the smallest lag attaining minimum correlation.
- Double that lag for candidate cycle length, limit per-bar period movement and use the result as a bandpass center.

## Outputs and intended use

- Display highpass data, minimum correlation, dominant cycle or final tuned bandpass; a zero derivative with positive/negative filter sign is proposed as local-high/low context.

## Parameters and stated settings

- Cycle estimate is twice selected lag and period change is capped at two per bar. Four output modes exist, with tuned bandpass default; Window controls ACF/cutoff.

## Failure modes and caveats

- Analytical: autocorrelation minima can be unstable in nonstationary data and an apparent half-cycle can reflect noise rather than persistent periodicity.

## Missing information and implementation boundary

- Highpass and bandpass recursions/bandwidth, ACF estimator/window endpoints, initialization and window default are not provided.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Apply a two-pole high-pass filter
```

### E2: parameters, mechanism, readiness

```text
Multiply that lag by two
```

### E3: parameters, readiness

```text
limit the result for the current bar to two greater or less
```

### E4: parameters, readiness

```text
"Tuned band-pass filter"[/b] (default)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gqklw3yv_tasc_2026_05_the_autotune_filter](../tv_gqklw3yv_tasc_2026_05_the_autotune_filter.md)
- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)

## Source

https://www.tradingview.com/script/GqKlw3yv-TASC-2026-05-The-AutoTune-Filter/

Publication ID: GqKlw3yv. Source SHA-256: b4a9da96edb6f45f8fcac7841f994add65f140b5251ee8b75e83cc0ad7337194. Raw-description SHA-256: ed0c52ab71c7d144c34ded3fa1859ed7482dd31e163df73e26172d68e7a4cc91.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
