---

id: tv_profile_hkjvjhbt

name: "Breakouts & Pullbacks [Trendoscope®]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Describe historical pullbacks, recoveries and later runups following sufficiently separated all-time-high close breakouts."

registry_key: null

runner: null

evaluation: null

---

# Breakouts & Pullbacks [Trendoscope®]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Describe historical pullbacks, recoveries and later runups following sufficiently separated all-time-high close breakouts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: ATH initialization, cycle closure, gap counting, probability estimator, sample size and treatment of never-recovered breakouts are unspecified.

- ATH initialization, cycle closure, gap counting, probability estimator, sample size and treatment of never-recovered breakouts are unspecified.

## How it works

- Qualify a close above the previous ATH after a minimum bar gap, measure the decline from breakout high to a pre-recovery low, track recovery above the original breakout price and accumulate post-recovery runup. Store completed cycles for percentile comparisons.

## Outputs and intended use

- Polylines, low-point labels/tooltips and a last-bar table compare the developing cycle with historical ones. The author explicitly says no buy/sell signals are generated.

## Parameters and stated settings

- Minimum Gap controls event separation. Suggested values are daily 30-50, four-hour 40-80 and hourly 100-200; these are recommendations, not universally validated settings.

## Failure modes and caveats

- Unrecovered events are censored and completed-cycle-only statistics can look overly favorable. The narrative's recovery/pullback labels differ from its triangle wording, so exact event boundaries need code confirmation.

## Missing information and implementation boundary

- ATH initialization, cycle closure, gap counting, probability estimator, sample size and treatment of never-recovered breakouts are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed feature class; this does not establish implementation parity or complete data coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Daily charts: 30–50
4H charts: 40–80
1H charts: 100–200
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Each completed cycle is stored permanently
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The indicator does not generate buy/sell signals.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
price closes above the previous ATH after at least Minimum Gap bars.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hkjvjhbt_breakouts_pullbacks_trendoscope](../tv_hkjvjhbt_breakouts_pullbacks_trendoscope.md)

## Source

https://www.tradingview.com/script/hkjvjHbt-Breakouts-Pullbacks-Trendoscope/

Publication ID: hkjvjHbt. Source SHA-256: 2377a14e20027a7613da91f6edfffe3aa2368abd3915b409f99e80e4f37d2dac. Raw-description SHA-256: 8a3e46e34ced65a7f2b336478da2641456aec0e2b38eb296e2f96b7dc2c58114.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
