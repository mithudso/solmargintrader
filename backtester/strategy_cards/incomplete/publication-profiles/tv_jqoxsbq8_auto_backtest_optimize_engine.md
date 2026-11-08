---

id: tv_profile_jqoxsbq8

name: "*Auto Backtest & Optimize Engine"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Search stop-loss and take-profit parameter combinations and inspect simulated outcomes for built-in examples or connected signals. The engine offers batch exploration and recommendations, rather than establishing that the selected historical optimum will generalize."

registry_key: null

runner: null

evaluation: null

---

# *Auto Backtest & Optimize Engine

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Search stop-loss and take-profit parameter combinations and inspect simulated outcomes for built-in examples or connected signals. The engine offers batch exploration and recommendations, rather than establishing that the selected historical optimum will generalize.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Stop equations, genetic update rules, LCG constants/seed, score weights, fill sequencing and trading-cost assumptions are absent.

- Stop equations, genetic update rules, LCG constants/seed, score weights, fill sequencing and trading-cost assumptions are absent.

## How it works

- Generate pseudorandom parameter combinations with an LCG/prime-based mixing scheme and evaluate batches; a purported genetic selection process suggests narrower ranges for subsequent manual testing.
- Stop families include static/dynamic volatility, trailing/fast trailing, chandelier, activator, moving average and SAR. Targets derive from risk/reward or volatility.
- A composite score combines trade count, profit, win rate, profit factor, drawdown and risk-adjusted ratios using generated weights. Sorting/filtering and result IDs support visual replay.

## Outputs and intended use

- Tables show candidate metrics and a chosen result can be plotted. Manual Start anchors a test to a selected chart point, potentially informing an existing position.
- The connector example encodes buy as positive one, sell as negative one and otherwise zero; it is an example interface, not the engine’s own trading edge.

## Parameters and stated settings

- Backtest window, test mode, parameter min/max/step ranges, stop family toggles, external source, manual start and displayed result ID.
- Author reports batches of 300 combinations and recommends browsing parts before narrowing ranges; these are workflow claims, not measured search guarantees.

## Failure modes and caveats

- Random sampling cannot guarantee locating an optimum or represent sparse profitable regions. Repeated selection on the same sample creates severe overfitting risk.
- The hypothesis example incorrectly calls 1,000 of 1,000,000 elements one percent; unsupported uniformity claims should not become statistical guarantees.

## Missing information and implementation boundary

- Stop equations, genetic update rules, LCG constants/seed, score weights, fill sequencing and trading-cost assumptions are absent.

## Data requirements

Required inputs: ohlcv, external signal series and caller parameter search definitions.

Repository input-class support: unavailable or unresolved. External connector series and caller test definitions must be supplied and verified alongside OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
generate and verify 300 unique combinations per batch
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Signal = buy ? +1 : sell ?  -1 : 0
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Score ━ based on Trade, Profit, WinRate, Profit Factor, Drawdown, Sharpe & Sortino & Omega & Calmar Ratio.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Select 1,000 random elements (1%) for validation.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)

## Source

https://www.tradingview.com/script/JQoXsbQ8-Auto-Backtest-Optimize-Engine/

Publication ID: JQoXsbQ8. Source SHA-256: af19fbe5d83b5d1442545bd8d28a3f484c36b1b58095a52a3c77bb49862b3a0c. Raw-description SHA-256: 47fe31854a044b4645b97ce2c9a67a32d703d50e61e076e2d3fdebd16bf49422.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
