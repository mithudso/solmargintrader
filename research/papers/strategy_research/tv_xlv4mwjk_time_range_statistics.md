---
id: tv_xlv4mwjk_time_range_statistics
name: "Time Range Statistics"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Time Range Statistics; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Time Range Statistics

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> A good amount of users requested a text box showing various price statistics, the following script returns various of these stats in a user-selected range, and include classical ones such as a central tendency measurement (mean), dispersion (normalized range) and percent change, but also include less common statistics such as average traded volume and number of gaps. The script also calculates the correlation between the closing price and another user-selected instrument.

> The setting evaluate to last bar will use a range starting at Start and ending at the last bar, as such you can use a full range by using Start = 0 and select evaluate to last bar

> The range is highlighted by an area on the chart. By default Start = 9000 and End = 10000, you might not have this amount of data in your chart, as such use the displayed bar index to select Start and End, then set the settings as default.

> The second stat is the normalized range, and determine how spread is the price in the user-selected range, why not the standard deviation? Because the standard deviation might return results varying widely depending on the scale of the closing price, you could get measures such as 0.0156 or 16 or even 56 depending on the instrument, as such using a normalized range can be more appropriate as it lays in a range of (0,1). Lower values indicate a low degree of price variation. Note that I still want to find another measure in the future.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv.
The repository supports OHLCV history. Verify symbol, cadence, timezone and complete bars for the chosen experiment; this is not a claim that every source market is cached.

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

- https://www.tradingview.com/script/XLV4MwjK-Time-Range-Statistics/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
