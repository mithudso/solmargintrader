---
id: tv_ektpaxcq_bloomberg_financial_conditions_index_proxy
name: "Bloomberg Financial Conditions Index (Proxy)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bloomberg Financial Conditions Index (Proxy); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-macro-and-derivatives-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Bloomberg Financial Conditions Index (Proxy)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Bloomberg Financial Conditions Index (BFCI): A Proxy Implementation

> Financial conditions indices (FCIs) have become essential tools for economists, policymakers, and market participants seeking to quantify and monitor the overall state of financial markets. Among these measures, the Bloomberg Financial Conditions Index (BFCI) has emerged as a particularly influential metric. Originally developed by Bloomberg L.P., the BFCI provides a comprehensive assessment of stress or ease in financial markets by aggregating various market-based indicators into a single, standardized value (Hatzius et al., 2010).

> The original Bloomberg Financial Conditions Index synthesizes approximately 50 different financial market variables, including money market indicators, bond market spreads, equity market valuations, and volatility measures. These variables are normalized using a Z-score methodology, weighted according to their relative importance to overall financial conditions, and then aggregated to produce a composite index (Carlson et al., 2014). The resulting measure is centered around zero, with positive values indicating accommodative financial conditions and negative values representing tighter conditi

> Despite these limitations, research by Arregui et al. (2018) indicates that even simplified financial conditions indices constructed from a limited set of variables can provide valuable signals about market stress and future economic activity. The proxy BFCI implemented here still offers significant insight into the relative ease or tightness of financial conditions, particularly during periods of market stress when correlations among financial variables tend to increase (Rey, 2015).

> The implementation presented in this Pine Script indicator represents a proxy of the original Bloomberg Financial Conditions Index, attempting to capture its essential features while acknowledging several significant constraints. Most critically, while the original BFCI incorporates approximately 50 financial variables, this proxy version utilizes only six key market components due to data accessibility limitations within the TradingView platform.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_vix_timing`.

## Data and availability

Required inputs: ohlcv, point-in-time-macro-and-derivatives-history.
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

- https://www.tradingview.com/script/EktpAXcq-Bloomberg-Financial-Conditions-Index-Proxy/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
