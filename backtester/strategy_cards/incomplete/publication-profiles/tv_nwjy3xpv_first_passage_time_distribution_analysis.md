---

id: tv_profile_nwjy3xpv

name: "First Passage Time - Distribution Analysis"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "First Passage Time Distribution Analysis simulates when price might first reach user-defined upper or lower percentage targets. It separates time-to-target summaries from which boundary is reached first, making it a scenario tool for holding-period and risk planning. Its estimates are conditional on a geometric-Brownian-motion model fitted to recent history; the source expressly notes that it runs only on the last bar and does not provide historical signals."

registry_key: null

runner: null

evaluation: null

---

# First Passage Time - Distribution Analysis

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

First Passage Time Distribution Analysis simulates when price might first reach user-defined upper or lower percentage targets. It separates time-to-target summaries from which boundary is reached first, making it a scenario tool for holding-period and risk planning. Its estimates are conditional on a geometric-Brownian-motion model fitted to recent history; the source expressly notes that it runs only on the last bar and does not provide historical signals.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** First-passage censoring/non-hit denominator and path/annualization rules are missing.

- First-passage censoring/non-hit denominator and path/annualization rules are missing.

## How it works

- Estimate drift and log-return volatility, annualize them and simulate GBM paths.
- Track first threshold hits, aggregate first-hit direction probabilities and summarize target times with percentiles, mean and median.

## Outputs and intended use

- Inspect threshold lines, risk zones and a statistics table when evaluating targets, stops or time horizons; these are model scenarios, not option-assignment probabilities.

## Parameters and stated settings

- Source describes over 1,000 paths. Distribution percentiles are 10/25/50/75/90, with optional one/two-sigma display.
- Historical drift is default, with zero drift and half-drift scenarios available; threshold size and simulation horizon defaults are not disclosed.

## Failure modes and caveats

- GBM omits jumps, fat tails, regime changes and fundamental events. Analytical: reported direction percentages may condition on paths that hit, so non-hit treatment matters.
- The text’s low-hit warning refers to an unnamed parameter, and its option assignment example conflates touching a price with assignment.

## Missing information and implementation boundary

- Simulation horizon, non-hit denominator/censoring, annualization convention, random seed and exact displayed-time units are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; source-code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
1,000+ price path simulations
```

### E2: parameters, readiness

```text
10th, 25th, 50th, 75th, 90th
```

### E3: parameters, readiness

```text
standard deviation levels (1σ, 2σ)
```

### E4: parameters, readiness

```text
Historical: Uses actual recent trend (default
```

### E5: parameters, readiness

```text
50% Reduced: Dampens trend effect
```

### E6: risks, readiness

```text
Runs only on last bar—doesn't give historical signals
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_nwjy3xpv_first_passage_time_distribution_analysis](../tv_nwjy3xpv_first_passage_time_distribution_analysis.md)

## Source

https://www.tradingview.com/script/NWJy3xPv-First-Passage-Time-Distribution-Analysis/

Publication ID: NWJy3xPv. Source SHA-256: 151730020834e21445c65ac7b42785e649d81a4e5a523f0ae8e3c86cf9965607. Raw-description SHA-256: 6210b8abcffb05e2b087ad6ecd3c64914a9cf315704848e243f144eea0c1bb38.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
