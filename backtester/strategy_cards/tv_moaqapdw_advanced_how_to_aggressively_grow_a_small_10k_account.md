---
id: tv_moaqapdw_advanced_how_to_aggressively_grow_a_small_10k_account
name: "[Advanced] How to aggressively grow a small (10k) account?"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of [Advanced] How to aggressively grow a small (10k) account?; not a tested trading strategy."
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
# [Advanced] How to aggressively grow a small (10k) account?

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Most of the time growing an account is a very slow grind. Make some, lose some, hope to make a little bit more than you lose.

> So how does this work? Going to use an example. The investor gets 100 trades a year because why not (that's 2 a week or a little over 8 a month), has a reward 5 times the risk and a winrate of 21% (PF = 1.33). Account size = $10,000. Risk per trade = $100. The investor was able to grow 4000 into 10,000 over 4 years "slowly" (not that slow) but surely. The biggest drawdown ever was 20%. The yearly return is 26%.

> And if it works out. As I said the example investor (which is already at least in the top 5% by the way) made 7280 rather than 3640. An extra $3640. Actually since his account was $10,000 and he was supposed to make about 3600 in 1.25 year, but instead made 7280 + 4000 = 11,280, well that's an extra of about $7500. Last time investor risked 3400/4000 in 12 trades (6% odds of losing all 12 and perhaps ~15% odds of losing all that money over a longer time), maybe this time investor wants to risk 6000/7500 in 12 trades ($500 each!). 26R = $13,000. If it works out in 2 years investor's account wen

> You might be looking at something like 20% a year. But once in a while, often in September-October, and sometimes at specific times such as March-April 2020, we get these monsters that go way further than usual. Often from a boring tight period, an explosion that grows exponentially, this pushes the reward dramatically. So we can end with a few winners at 10, 15R, rather than the usual ~5.

> An experienced but poor investor, that spent years working on entries, exits, and so on, will need do something rather "dramatic" to grow his account. Doesn't have to be a complete gamble. An idea is after one of these "boost" periods, the investor could put all of that profit at risk. Say he made 32%, losing it all would be a major drawdown of 25%, but if the investor sees it as extra it is not the same as a crippling drawdown. Having a great period is nice (within years of moderate consistency), but it is not life changing.

> For example, with an average risk to reward of 1 to 5, and a win ratio of 21% (not counting once a year outliers), which is pretty good, breakeven being at 16.67%, after 100 trades the result will be - with a risk of 1% (flat) each time:

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_risk_based_sizing`.

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

- https://www.tradingview.com/chart/GBPUSD/mOaqApdW-Advanced-How-to-aggressively-grow-a-small-10k-account/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
