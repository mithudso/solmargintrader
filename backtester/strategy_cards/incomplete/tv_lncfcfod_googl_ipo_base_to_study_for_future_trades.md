---
id: tv_lncfcfod_googl_ipo_base_to_study_for_future_trades
name: "GOOGL: IPO Base to study for Future trades"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of GOOGL: IPO Base to study for Future trades; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# GOOGL: IPO Base to study for Future trades

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

The source screens for an IPO base with at least five days of sideways movement. The base must start within the first 25 trading days, last no more than six weeks, have average daily dollar volume of at least $10 million, and not substantially undercut the first-day IPO low. The author also considers institutional sponsorship and increasing quarterly sales/earnings. It discusses buying at a pivot or entering early and using a 7% stop. Exact base geometry, the meaning of substantially, the entry trigger and the stop reference are not fully defined. These are documented screening constraints, not a fully executable or validated strategy.

## Documented inputs and source details

> This Tutorial is used in conjunction with the Stocks Over Coffee Podcast on Technical Education series on IPO Bases

> Every year there are typically over 100 IPOs that come out and one way to filter through all of them and know when to buy is to find the IPO Base. Google is one of the model example I use when I am confusing about my own trading rules. Why Google? Lets talk about the technical Formation.

> Using these criteria you can try to get in early on the stock even before the base happens, which is a little bit riskier but always have a stop loss in place of 7%. After investing in IPOs you get a sense from your winners how IPOs should make you feel and once they break character then it is time to take the profits and reinvest.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/chart/GOOGL/lncfCFOD-GOOGL-IPO-Base-to-study-for-Future-trades/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Additional bound source rules

The following source passages support the mechanism above. They are author
descriptions, not repository performance evidence.

````text
Minimum 5 days long in a sideways movement
````

````text
Base Starts in the iin the first 25 trading days
````

````text
Bases are maximum 6 weeks long
````

````text
Minimum liquidity of $10mm average daily volume
````

````text
Doesn't substantially undercut the first day IPO price low
````

````text
From this criteria you can already eliminate over 50% of stocks that IPO. From here you can get even more specific to looking if A+ institutions with great and long time managers are in this stock. Then again even more specific if they are increasing sales and earnings quarter over quarter.
````
