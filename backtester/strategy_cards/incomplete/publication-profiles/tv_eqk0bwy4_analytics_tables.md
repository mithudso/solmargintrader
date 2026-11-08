---

id: tv_profile_eqk0bwy4

name: "analytics_tables"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "analytics_tables supplies reusable strategy-performance tables rather than a standalone market signal. It separates caller-provided win/loss statistics from table presentation and also maintains seasonality data for calendar performance views. The intended integration is a trailing-strategy framework, while the exposed objects let other strategy scripts reuse the reporting layer."

registry_key: null

runner: null

evaluation: null

---

# analytics_tables

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

analytics_tables supplies reusable strategy-performance tables rather than a standalone market signal. It separates caller-provided win/loss statistics from table presentation and also maintains seasonality data for calendar performance views. The intended integration is a trailing-strategy framework, while the exposed objects let other strategy scripts reuse the reporting layer.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Metric equations, trade-return definitions, risk-free assumptions, seasonal/eon semantics and caller data aggregation are not fully documented.

- Metric equations, trade-return definitions, risk-free assumptions, seasonal/eon semantics and caller data aggregation are not fully documented.

## How it works

- Initialize table/data objects once and update them with win/loss SideStats and inconclusive exits.
- Render statistics and metrics, including a caller buy-and-hold comparison, and maintain seasonal matrices of balances, returns, drawdowns and annualized summaries.

## Outputs and intended use

- Use StatsTable, MetricsTable and SeasonalTable to display strategy outcomes with configurable placement/colors and extended seasonal columns.

## Parameters and stated settings

- Initial release provides three table types. Height/width default zero for automatic sizing; seasonal mode, maximum years and display colors are configurable.

## Failure modes and caveats

- Analytical: table output is only as valid as the caller’s fill/cost/statistics inputs, and reporting does not independently validate backtest results.

## Missing information and implementation boundary

- Metric equations, trade-return definitions, risk-free assumptions, seasonal/eon semantics and caller data aggregation are not fully documented.

## Data requirements

Required inputs: caller strategy win/loss aggregates, strategy equity/seasonality observations, buy-and-hold comparison.

Repository input-class support: unavailable or unresolved. Requires simulated or actual strategy statistics supplied by a caller; market OHLCV alone does not define those outcomes.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
three types of tables
```

### E2: parameters, readiness

```text
By default, 0 auto-adjusts the height
```

### E3: mechanism, readiness

```text
wins (SideStats)
```

### E4: parameters, readiness

```text
buyAndHoldPerc (float)
```

### E5: mechanism, readiness

```text
returnPercs (matrix<float>)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)
- [tv_method_seasonality](../tv_method_seasonality.md)

## Source

https://www.tradingview.com/script/eQk0bwY4-analytics-tables/

Publication ID: eQk0bwY4. Source SHA-256: 8af7b0606733af673fb7544a74e7260b3add39f458946a03975f3b464a3c413e. Raw-description SHA-256: 21640f2f64ebfda50b0c53adba5282b99be64b4b90078502841af8dd8bb1d969.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
