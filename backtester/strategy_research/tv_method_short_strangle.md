---
id: tv_method_short_strangle
name: Short strangle option premium
kind: exposure-strategy
status: spec-only
family: research-method
summary: Specification of Short strangle option premium; not a tested trading strategy.
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [option-chain-bid-ask-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Short strangle option premium

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Sell an out-of-the-money put and an out-of-the-money call on the same underlying
and expiry. The maximum expiry gain is the executable net premium received. Losses
can be very large below the put strike and are unbounded above the call strike.
This is a naked-option position, not a limited-risk iron condor. Freeze strikes,
maturity, margin, early-assignment treatment, stop/exit and tail-risk policy.
Option bid/ask history and financing costs are required; underlying OHLCV is insufficient.

## Documented inputs and source details

> Ah the famous strangle strategy.

The card supplies a conventional payoff definition. Source claims about likely
profit do not establish an edge or a safe margin policy. No numeric trading defaults
are invented.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: option-chain-bid-ask-history.
The complete point-in-time input set has not been verified in the repository. Do not substitute current snapshots or inferred values for historical inputs.

## Implementation and validation

No runner or registry key is assigned. Before implementation, freeze the numerical
formula, seeds, missing-value policy, warm-up and parameter domains. Where the source
does not disclose an algorithm or default, recover it rather than guessing. Specify
entry, exit, stop, holding horizon, exposure and costs separately from the indicator.
Record which choices come from the publication and which define a new experiment.

Compute with closed bars and trailing data only. Confirm pivots and higher-timeframe
values before use; never backdate a signal to a pivot that needed later bars. Test
prefix invariance, flat/zero inputs, unavailable data and one-bar-delayed execution.
Evaluate chronologically out of sample, deduct transaction and financing costs and compare with
buy-and-hold and simpler component rules. Record all searched configurations.

## Failure modes and caveats

An author description is not source code or independent validation. Visual styling,
retrospective drawing anchors, repainting pivots and fitted full-history models can
produce unavailable historical signals. A rule can be numerically correct and lose
after costs. Venue, session, data and asset differences limit transfer to SOL.

## Measured results

Not measured in this repository. Publication examples, advertised accuracy and
screenshots are not repository backtest results.

## Likelihood of success: low

Basis: a-priori. The mechanism has no confirming out-of-sample result here. This rating
does not promote the source author's claims into evidence of profitability.

## Sources

- https://www.tradingview.com/chart/NG1!/W5pU0wcf-The-adventures-of-leveraged-naked-ootm-option-sellers/

The coverage ledger binds the source hash and description excerpt.
