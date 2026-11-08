---
id: tv_oe3v6w93_new_technical_tools_back_tested_on_old_extreme_markets
name: "New Technical Tools Back Tested on Old Extreme Markets"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of New Technical Tools Back Tested on Old Extreme Markets; not a tested trading strategy."
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
# New Technical Tools Back Tested on Old Extreme Markets

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> If traders back in the day would have had the modern technical analysis tools they could have forecasted the market crashes more easily. Once the past is gone it's gone forever, but we can always go back to learn from it. Those who ignore the past are doomed to repeat it. In this publication I back tested a couple of tools which basically detect the trend direction, trend strength and momentum.

> Once the Madrid Ribbon signaled the trend reversal going from red to green, the Bull Market was pinpointed to start in July 1984, from that point the Market went up, it reached 100% return from bottom to top, it corrected about 10% and kept on going until it peaked at 2700 points. By 1987 the computers had taken over the stock market, when several bulls took profit at around the target level, this event triggered the circuit breakers and liquidated the positions, the Flash crash took a dive of 35% from top to bottom. The Madrid Vector detected the last low momentum and the Madrid Ribbon detect

> When the market sells, it sells, at first there is no way to know if this is a selloff or just a profit taking and an opportunity to buy the dip. By looking at the indicators, I can determine if the vector is in the red, then it's a selloff, and probably the start of a bear market, if the vector is showing weak momentum, or if it is in the brink of going in the opposite direction. A selloff is not always the same, and the indicator can help to determine the best strategy to follow.

> "The Roaring 20's" The feverish Stock Market. The time when everybody wanted to get in because everybody was making money. The Bull Market of 29 started in June 1924, when the Madrid Ribbon confirmed a Green Bull after a double bottom from November 1923 and May 1924. There was a reversal of the Bear trend in November 1921. The "Madrid Attack Vector'' indicator confirms the times of the duration of the trend. It shows a dull market in November 1922, a Peak and an exhaustion with a Bearish reversal. In May 1926 there was a painful correction, pinpointed by both the Vector and the Ribbon, a conso

> The charts should follow the K.I.S.S. principle, (Keep It Simple and Stupid), the simpler the better. An indicator should provide as much meaningful information as possible without being overwhelming and without pushing the limit to the analysis paralysis level. I use the classical Madrid Ribbon indicator to determine the Bias at a Glance. This indicator is very simple, and it only needs one parameter, exponential moving average or the default simple moving average, the rest is done by the script. At a glance I can get the bullish or bearish bias by just looking at the color of the indicator,

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_double_top_bottom`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/chart/DJ30/oE3V6w93-New-Technical-Tools-Back-Tested-on-Old-Extreme-Markets/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
