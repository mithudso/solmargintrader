---
id: tv_eos9u1qm_fair_value_bands_flowly_indicators
name: "Fair value bands / Flowly Indicators"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Fair value bands / Flowly Indicators; not a tested trading strategy."
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
# Fair value bands / Flowly Indicators

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Fair value bands, like other band tools, depict dynamic points in price where price behaviour is normal or abnormal, i.e. trading at/around mean (price at fair value) or deviating from mean (price outside fair value). Unlike constantly readjusting standard deviation based bands, fair value bands are designed to be smooth and constant, based on typical historical deviations. The script calculates pivots that take place above/below fair value basis and forms median deviation bands based on this information. These points are then multiplied up to 3, representing more extreme deviations.

> Trend modes affect fair value basis color that indicates trend direction. Direction based trend considers only the direction of the defined fair value basis, i.e. pointing up is considered an uptrend, vice versa for downtrend. Cross based trends activate when selected source (same options as price source) crosses fair value basis. These sources can be set individually for uptrend/downtrend cross conditions. By default, the script uses cross based trend mode with low and high as sources.

> Threshold band is calculated using typical deviations when price is trading at fair value basis. In other words, a little bit of "wiggle room" is added around the mean based on expected deviation. This feature is useful for cross based trends, as it allows filtering insignificant crosses that are more likely just noise. By default, threshold band is calculated based on 1x median deviation from mean. Users can increase/decrease threshold band width via input menu for more/less noise filtering, e.g. 2x threshold band width would require price to cross wiggle room that is 2x wider than typical, 0

> Ideal trend stays inside fair value and provides sufficient cool offs between the moves. When this is the case, fair value bands can be used for sensible entry/exit levels within the trend.

> Width of deviation bands by default is based on 1x median deviations and can be increased/decreased in a similar manner to threshold bands.

> Metric calculation highlights can be enabled from the input menu, resulting in a lot based coloring and visibility of each lot counter (time, cumulative relative volume and average relative volume) in data window:

> Depending on the asset, timeframe and chosen fair value basis, shape of the distributions vary. However, practically always time is distributed in a normal bell curve shape, being highest at lots +1 to -1, gradually decreasing the further price is from the mean. This is hardly surprising, but it allows accurately determining dynamic areas of normal and abnormal price behaviour (i.e. low risk area between +1 and -1, high risk area between +-2 to +-3). Volume on the other hand is typically distributed the other way around, being lowest at lots +1 to -1 and highest at +-2 to +-3. When time and vo

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

- https://www.tradingview.com/script/eos9U1qM-Fair-value-bands-Flowly-Indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
