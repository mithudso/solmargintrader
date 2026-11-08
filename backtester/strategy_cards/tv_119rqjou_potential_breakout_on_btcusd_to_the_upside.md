---
id: tv_119rqjou_potential_breakout_on_btcusd_to_the_upside
name: "Potential breakout on BTCUSD to the upside"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Potential breakout on BTCUSD to the upside; not a tested trading strategy."
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
# Potential breakout on BTCUSD to the upside

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

The source places a buy-stop at the 10-period Donchian upper channel. Once filled, it sets an initial stop 7% below entry. It cancels unfilled orders at the end of the session at 00:00 UTC. At each 00:00 UTC update, the stop is the higher of the initial 7% stop and the 2-period Donchian lower channel. A separate optional PFZone signal exits at the stated midnight market open; PFZone is proprietary and must remain disabled unless its definition is recovered. The author says the system can run without PFZone. Freeze channel bar availability, order lifetime, session boundaries and gap/fill semantics before implementation. The source numeric trade example is not a current order instruction.

## Documented inputs and source details

> A systematic breakout strategy designed to capture short-term trends with an average holding period of 6 days.

> Place Buy Stop at 9497.2, If done place Stop Loss at 8832.4.

> IntStp(7%) := Initial Stop Loss set at 7% below entry price.

> 1. At 00:00 UTC+0, if the DC(2) Low is higher then the IntStp(7%), than adjust stop loss to the DC(2) Low price.

> DC(10) Up := Donchian Channels upper band (10 length).

> DC(2) Low := Donchian Channels lower band (2 length).

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

- https://www.tradingview.com/chart/BTCUSD/119RQjOu-Potential-breakout-on-BTCUSD-to-the-upside/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Additional bound source rules

The following source passages support the mechanism above. They are author
descriptions, not repository performance evidence.

````text
1. Place a Buy Stop at the DC(10) Up Price.
````

````text
2. If buy stop is filled, place the IntStp(7%).
````

````text
3. However, if orders are not filled, cancel orders at the end of the trading session at 24:00 UTC+0.
````

````text
2. However, If IntStp(7%) is above the DC(2) Low, then use the IntStp(7%).
````

````text
3. If the PFZone has been triggered then exit at open on market at 00:00 UTC+0.
````

````text
The Profit Zone is a proprietary indicator designed to improve the performance as an alternative exit rule.
````

````text
However, the strategy is a stand-alone system and does not require the profit zone indicator.
````
