---

id: tv_profile_4nmghanl

name: "RedK Slow_Smooth Average (RSS_WMA)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "RSS_WMA deliberately favors a slow, smooth trend baseline over rapid response. It seeks to suppress small fluctuations so the trader can see broader price behavior and compare a stable reference with a faster moving average. The author also suggests considering direction changes as exit context, because the line is intended to respond only after a sustained move. This is a conscious lag tradeoff rather than a claim that smoothing removes trading risk."

registry_key: null

runner: null

evaluation: null

---

# RedK Slow_Smooth Average (RSS_WMA)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

RSS_WMA deliberately favors a slow, smooth trend baseline over rapid response. It seeks to suppress small fluctuations so the trader can see broader price behavior and compare a stable reference with a faster moving average. The author also suggests considering direction changes as exit context, because the line is intended to respond only after a sustained move. This is a conscious lag tradeoff rather than a claim that smoothing removes trading risk.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Three consecutive standard WMA passes and cyclic allocation of smoothness increments define the principal smoother; rounding/source choices can be explicit caller parameters.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Apply weighted-moving-average smoothing repeatedly; the combined smoothness value is distributed across consecutive WMA passes.
- Allocate increments first to the first pass, then the second, then the third, cycling through the passes.

## Outputs and intended use

- Use the line for macro trend inspection, noise filtering or comparison with a fast average; a sustained change in direction can inform discretionary exits.

## Parameters and stated settings

- There are three WMA passes; initial first-pass length is one third of the Smoothness setting. Settings below 3 simply track the source.
- The control is Smoothness rather than a conventional single-window length; no default value or source-price default is supplied.

## Failure modes and caveats

- Analytical: deliberate slowness may delay recognition of a reversal and exit response.

## Missing information and implementation boundary

- Rounding of pass lengths, full weighting implementation and mechanical exit confirmation are not documented.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart price/volume data supports the described calculation class; matching Pine implementation remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
the initial length used for the first WMA pass calculation is 1/3 of that smoothness value selected in the settings
```

### E2: parameters, readiness

```text
because we utilize 3 WMA passes, a settings below 3 will have no effect on the line and it will just track the "source" price.
```

### E3: purpose, risks, readiness

```text
sacrifices low-lag and fast responsiveness for the sake of smoothness.
```

### E4: readiness, mechanism

```text
Increments in the combined smoothness value will be allocated first to 1st WMA pass, then 2nd WMA pass, then 3rd pass consecutively then back to 1st pass.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_4nmghanl_redk_slow_smooth_average_rss_wma](../tv_4nmghanl_redk_slow_smooth_average_rss_wma.md)

## Source

https://www.tradingview.com/script/4nmGHAnL-RedK-Slow-Smooth-Average-RSS-WMA/

Publication ID: 4nmGHAnL. Source SHA-256: 1a178a227ce35bb56758ea7b191766613228c8b9fe9a06ebff62ba08a6c3ff23. Raw-description SHA-256: 7dc850b548295849eee253d175f51c5cfff91c90f4456048d051fda30ca74efc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
