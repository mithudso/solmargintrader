---

id: tv_profile_tcwijygr

name: "Sigma Spike Filtered Binned OPR ( Adam H. Grimes )"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Study where a day opens within its eventual range, specifically on unusually volatile days, to explore possible early-session directional behavior."

registry_key: null

runner: null

evaluation: null

---

# Sigma Spike Filtered Binned OPR ( Adam H. Grimes )

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Study where a day opens within its eventual range, specifically on unusually volatile days, to explore possible early-session directional behavior.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Sigma Spike construction, OPR denominator, bin widths, session boundaries and executable early-day criteria are missing.

- Sigma Spike construction, OPR denominator, bin widths, session boundaries and executable early-day criteria are missing.

## How it works

- Bin historical open-location-in-range observations into a histogram. Retain observations only when Grimes' Sigma Spike volatility measure exceeds a threshold.

## Outputs and intended use

- Heavy histogram tails indicate opens clustered near the day's highs or lows. The author tentatively connects this with early trades in the direction away from the open on high-volatility days.

## Parameters and stated settings

- A volatility threshold and histogram bins are implied, but formulas, cutoffs and defaults are absent.

## Failure modes and caveats

- The completed day's range is unavailable at its open. Using the retrospective OPR or full-day volatility filter as a live entry condition could create lookahead.

## Missing information and implementation boundary

- Sigma Spike construction, OPR denominator, bin widths, session boundaries and executable early-day criteria are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The OPR histogram displays the binned distribution of OPR values for the chart history.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
So that OPR values are only recorded when volatility exceeds a threshold (relative high range days).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_tcwijygr_sigma_spike_filtered_binned_opr_adam_h_grimes](../tv_tcwijygr_sigma_spike_filtered_binned_opr_adam_h_grimes.md)

## Source

https://www.tradingview.com/script/TcwiJYgr-Sigma-Spike-Filtered-Binned-OPR-Adam-H-Grimes/

Publication ID: TcwiJYgr. Source SHA-256: 28fc4cba5951db86c835fdcb0e3d9bdb97d498d98f613bce6288c2a7db3e6b60. Raw-description SHA-256: b8464e827018d4a8efd2399ae9d16b63cb3d3d349d261d3f5b60e51bc7b0a92a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
