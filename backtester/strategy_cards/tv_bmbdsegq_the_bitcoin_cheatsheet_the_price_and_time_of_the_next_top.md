---
id: tv_bmbdsegq_the_bitcoin_cheatsheet_the_price_and_time_of_the_next_top
name: "The BITCOIN Cheatsheet! The price and time of the next Top!"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of The BITCOIN Cheatsheet! The price and time of the next Top!; not a tested trading strategy."
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
# The BITCOIN Cheatsheet! The price and time of the next Top!

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> I know the title is a little bit catchy but what is says seems not to be far from the reality. This is a combination of studies I released in the past and it clearly decodes every Cycle High (practically the All Time High) and duration. Who wouldn't actually want to know when and where Bitcoin's next Top will be? For the record this study is based on the 1W chart (every candle/ bar represents 1 week).

> Let's take it from the beginning. BTC's Cycle 1 made a Bottom on the November 07 2011 candle and it took 67 weeks/ bars (469 days) to reach the May 2011 All Time High (ATH). That 67 bar sequence printed a +1487% rise. That was Phase 1 of Bull Market of Cycle 1. The next ATH was on November 2013 around $1230. That was a +3591% rise and was 2.415 times greater than the previous one of 1487% (i.e. 1487% X 2.415 = 3591%). Make a note of 2.415 because it is a constant we will be using in the following Cycles. The duration of that Phase (Phase 2 we'll call it) from the end of Phase 1 to the new ATH,

> Phase 1 (Cycle bottom until ATH test) = 67 weeks duration and +1487% rise

> Will that be a great prolonged accumulation period for Bitcoin or will add to the anxiety of holders? Is the $270000 overly optimistic or pessimistic? Feel free to share your work and let me know in the comments section!

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

- https://www.tradingview.com/chart/BLX/bMBDsEgq-The-BITCOIN-Cheatsheet-The-price-and-time-of-the-next-Top/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
