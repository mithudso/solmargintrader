---

id: tv_profile_fq7ig92h

name: "Deeptest"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Deeptest extends strategy reporting with trade statistics, risk-adjusted metrics, drawdowns, distribution diagnostics, benchmark comparison and robustness-style summaries. It reads closed trades from an existing Pine strategy, so it evaluates supplied simulated outcomes rather than creating a strategy. The documentation includes many heuristic quality labels; those labels are not statistical guarantees and its screenshots are explicitly illustrative."

registry_key: null

runner: null

evaluation: null

---

# Deeptest

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Deeptest extends strategy reporting with trade statistics, risk-adjusted metrics, drawdowns, distribution diagnostics, benchmark comparison and robustness-style summaries. It reads closed trades from an existing Pine strategy, so it evaluates supplied simulated outcomes rather than creating a strategy. The documentation includes many heuristic quality labels; those labels are not statistical guarantees and its screenshots are explicitly illustrative.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Supplied-equity and closed-trade basic metrics is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Extract closed-trade returns and compute profitability, holding-time, exposure, return-distribution and equity-risk summaries; fetch a benchmark for comparison.
- Shuffle historical trade order for Monte Carlo equity scenarios and partition trades into rolling in/out-of-sample segments for comparisons.
- Calculate at last confirmed historical state and render main/complementary tables with tooltips and stress/period cards.
- NetProfit%=100*(FinalEquity-InitialCapital)/InitialCapital. CAGR=(Final/Initial)^(365.25/Days)-1. Payoff=AverageWin/AverageLoss per source sign convention;ProfitFactor=GrossProfit/GrossLoss using absolute totals. Win/BE/Loss rates=count in each class/total trades,shown as percentages;breakeven win%=100/(1+Payoff). Require positive capital/duration,nonzero loss denominators and supplied completed trades. WFA/MC/Sharpe/RoR remain excluded.

## Outputs and intended use

- Import and call runDeeptest in an existing strategy, then assess metric consistency and assumptions rather than relying on a single colored threshold.
- Usable scope: Supplied-equity and closed-trade basic metrics. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Source claims more than 112 calculations and over 1,000 shuffle iterations; WFA defaults to twelve windows with roughly 75% in-sample/25% out-of-sample.
- Basic metrics need at least one closed trade; the source suggests thirty-plus for statistical analysis, which is a heuristic rather than universal sufficiency.

## Failure modes and caveats

- Analytical: shuffling unchanged proportional returns does not change compounded terminal wealth without additional path-dependent assumptions; partitioning already-selected trades is not independent parameter retraining.
- The prose includes inconsistent MAR sign language and overstates p-value/alpha interpretations; no-retraining OOS labels require caution.

## Missing information and implementation boundary

- Trade-return basis, path-dependent sizing, full WFA training procedure, risk-of-ruin assumptions, risk-free rate and all metric implementation details are not supplied.

## Data requirements

Required inputs: caller strategy closed-trade/equity history, S&P 500 benchmark history.

Repository input-class support: unavailable or unresolved. Strategy trade outcomes and external benchmark data are required; OHLCV alone does not define the evaluated strategy.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
112+ statistical calculations
```

### E2: parameters, readiness

```text
1000+ iterations
```

### E3: parameters, readiness

```text
default: 12), IS = ~75%, OOS = ~25%
```

### E4: parameters, readiness

```text
Requires at least 1 closed trade for basic metrics, 30+ trades
```

### E5: mechanism, risks, readiness

```text
randomizing the order of trades while keeping trade returns unchanged.
```

### E6: risks, readiness

```text
solely for visual representation
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Net Profit[/b] — (Final Equity - Initial Capital) / Initial Capital × 100
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]CAGR[/b] — (Final / Initial)^(365.25 / Days) - 1
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Payoff Ratio[/b] — Average Win / Average Loss
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Profit Factor[/b] — Gross Profit / Gross Loss
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Win Rate[/b] — Wins / Total Trades
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]BE Rate[/b] — Breakeven Trades / Total Trades
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/fQ7ig92H-Deeptest/

Publication ID: fQ7ig92H. Source SHA-256: 83806273cb0173beee2f55970c1dc0ac987c46bee893ed76655bcf7efa12d9dd. Raw-description SHA-256: 01bfa1b819d39d170bf2626ca5c394a38c4c4ee95099589ce04c74fa0760a6f8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
