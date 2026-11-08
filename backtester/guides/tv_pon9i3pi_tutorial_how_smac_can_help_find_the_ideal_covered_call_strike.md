---
id: tv_pon9i3pi_tutorial_how_smac_can_help_find_the_ideal_covered_call_strike
name: "Tutorial: How SMAC can help find the Ideal Covered Call Strike"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Tutorial: How SMAC can help find the Ideal Covered Call Strike; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Tutorial: How SMAC can help find the Ideal Covered Call Strike

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

The source describes an earnings covered-call variant: hold the underlying shares and sell weekly calls shortly before earnings, then close after the announcement or potentially hold to expiry. The SMAC indicator percent envelope is set to 5% to help choose an approximately 5%-out-of-the-money strike. The investor plots the share breakeven and rejects a strike below that breakeven because assignment would realize a loss on the shares. The example uses a $143 share breakeven and considers $151/$152 strikes. The source does not disclose the complete SMAC auto-stepping recurrence or a historical option-pricing model. Its no-lose language is not accepted: the retained underlying can decline, and costs, assignment, dividends and gaps must be modeled.

## Documented inputs and source details

> Background: The earnings covered call volatility play

> Calculating the P&L for both CC scenarios is also easy now on the chart

> assume the CC premium is $1.3 by the time i sell the CC & assume i have 1,000 AAPL shares, that's $1,300 over-night! = 1% return and i still keep the stock

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_covered_call`, `tv_method_risk_based_sizing`.

## Data and availability

Required inputs: ohlcv, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/chart/AAPL/PON9I3pI-Tutorial-How-SMAC-can-help-find-the-Ideal-Covered-Call-Strike/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Additional bound source rules

The following source passages support the mechanism above. They are author
descriptions, not repository performance evidence.

````text
one of the easy earning plays if you hold a portfolio of stocks (or if you're a fan of the wheeling strategy) is to sell Covered Call (CC) right before the earnings announcement - when the volatility is inflated and the premium price peaks - usually using weekly options - which then you can close immediately after the earnings have been announced, or just leave them to expire worthless if they end up out of the money (OTM).
````

````text
- my preferred strike "distance" is 5% Out of the Money (OTM) - which can give a reasonable value of premium while giving me room to still keep the stock if the price doesn't shoot that high due to the earnings.
````

````text
- I plot my breakeven price on the chart - say for the example here, it's $143
````

````text
- Add the SMAC to the chart and set the SMAC Percent Envelop to 5%
````

````text
- This will immediately show what price range i should pick the Covered Call strike if i want a 5% OTM -- it's the $151 or the $152. Maybe i would pick the $152, cause if i get assigned, it would give me a larger gain on the underlying position.
````

````text
Another scenario is, if my breakeven for AAPL is above the 5% strike price level, in which case, i would not consider this trade at all - because if i sell the CC and i get assigned, i would basically close my position at a loss - again, once i set the SMAC and my BE of the chart, i can easily see if that's the case and make a fast trade decision - here's how this would look on the chart
````
