---
id: tv_gjugg1kv_key_ideas_to_trade_big_daily_structures_example_on_amat
name: "Key Ideas to trade big daily structures. Example on AMAT"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Key Ideas to trade big daily structures. Example on AMAT; not a tested trading strategy."
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
# Key Ideas to trade big daily structures. Example on AMAT

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

The source starts from a range in which price has not made a new all-time high for 200 days. It then waits for a new ATH, a two-to-four-week correction without another ATH, and a fresh ATH break to enter. The stop sits below the correction, the target uses the final Fibonacci extension, and reaching the first Fibonacci extension moves the stop to breakeven. The source risks 2% of capital at the stop and rejects the trade if the required sequence does not occur. The Fibonacci anchors/ratios, ATH-history boundary, exact correction definition and order execution are not fully disclosed. Treat the advertised win rate as an author assertion, not repository evidence.

## Documented inputs and source details

> I will keep this post short, so you can get a general idea of this trading style.

> First of all, we have a situation where the price could not make a new ATH in 200 days. It's important to notice that we can draw a clear structure with well-defined limits because the price stayed in a clear range between 146 and 114

> Here is where technical analysis will help you create a map or sequence of movements to say, "Hey, there is a pattern here that I can wait." Once you have defined that, draw it in your chart.

> c) IF that happens, trade on the new ATH, with a stop loss below the 2 to 4 weeks correction and Take profit on the final Fibo extension

> e) Move the stop loss to the entry-level if the price reaches the first Fibo Extension.

> f) Risk: We will use 2% of our capital on the stop loss.

> Remember: Do not try to avoid a stop-loss; create procedures to control them. My win rate right now is 55% - 60%. That means that almost half of the time, I'm wrong; HOWEVER, when I'm right, I make more than 2 dollars of every dollar I'm risking. Trade like a casino!

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

- https://www.tradingview.com/chart/AMAT/gjugg1kV-Key-Ideas-to-trade-big-daily-structures-Example-on-AMAT/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Additional bound source rules

The following source passages support the mechanism above. They are author
descriptions, not repository performance evidence.

````text
a) Wait for a new ATH (that's the confirmation that the structure has been broken)
````

````text
b) Wait for a 2 to 4 weeks correction (that means that after the breakout, the price is not able to make a new ATH)
````

````text
d) IF that doesn't happen, do not trade
````
