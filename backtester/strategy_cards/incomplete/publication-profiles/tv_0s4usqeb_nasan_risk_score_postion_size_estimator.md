---

id: tv_profile_0s4usqeb

name: "Nasan Risk Score & Postion Size Estimator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Nasan estimates a trade risk percentage and position size by combining the stock’s return relative to a benchmark, its historical volatility and drawdown, and the trader’s own performance assumptions. It attempts to refine a generic capital-risk allowance for the particular stock and trader. The result is a sizing aid rather than a signal to buy the stock, and the description restricts its risk and size calculations to daily charts."

registry_key: null

runner: null

evaluation: null

---

# Nasan Risk Score & Postion Size Estimator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Nasan estimates a trade risk percentage and position size by combining the stock’s return relative to a benchmark, its historical volatility and drawdown, and the trader’s own performance assumptions. It attempts to refine a generic capital-risk allowance for the particular stock and trader. The result is a sizing aid rather than a signal to buy the stock, and the description restricts its risk and size calculations to daily charts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Annual weighting, ATR adaptation and ambiguous sizing parentheses prevent reproducible risk and quantity outputs.

- Annual weighting, ATR adaptation and ambiguous sizing parentheses prevent reproducible risk and quantity outputs.

## How it works

- Compute minimum and maximum risk from weighted annual stock-minus-benchmark returns divided by annual maximum and minimum ATR percentages respectively.
- Blend transformed minimum and maximum risks using exponent and scaling factors derived from trader win rate and profit ratio. Aggressive and conservative modes exchange which factor receives the larger value.
- Multiply the unadjusted risk score by a drawdown-tolerance adjustment, then combine capital, risk and a condition-dependent ATR multiplier to estimate size.

## Outputs and intended use

- Use the estimated risk percentage and size to plan exposure; by default an underperforming stock receives no position-size calculation.

## Parameters and stated settings

- Historical metrics use five-year weighted annual values; trader defaults are win factor 50% and profit ratio 1.5.
- Optional underperformer calculation substitutes minimum 1% and maximum 2%; the adaptive ATR multiplier ranges from 1 to 3.5.

## Failure modes and caveats

- Analytical: estimated risk depends on trader-supplied performance and tolerance; historical relative strength does not establish safe exposure.
- The written position-size expression is ambiguous about parentheses and ATR placement, so it must not be translated directly into an order quantity.

## Missing information and implementation boundary

- Annual weighting, precise ATR adaptation rules, default drawdown tolerance and intended parentheses in the sizing formula remain undisclosed.

## Data requirements

Required inputs: ohlcv, benchmark historical prices, trader win rate and profit ratio, capital and maximum acceptable drawdown.

Repository input-class support: unavailable or unresolved. Daily stock and a selected benchmark history plus trader/account assumptions are required; benchmark identity and personal inputs are not supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, readiness

```text
THE RISK SCORE AND POSITION SIZE WILL ONLY BE CALCUTAED ON DIALY TIMEFRAME NOT IN OTHER TIMEFRAMES.
```

### E2: mechanism, parameters, readiness

```text
Min Risk = ( 5 year weighted avg Annual Stock Return  -  5 year weighted avg Annual Bench Return) / 5 year weighted avg Annual Max ATR%
```

### E3: parameters, readiness

```text
A default of 50% is used for win factor and 1.5 for profit ratio.
```

### E4: parameters, readiness

```text
it will use 1% for Min Risk% and 2% for Max Risk%
```

### E5: missing_information, risks, readiness

```text
Position Size = (Capital * Risk% )/ ATR-Multiplier * ATR
```

### E6: parameters, readiness

```text
It would range between 1 - 3.5.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_0s4usqeb_nasan_risk_score_postion_size_estimator](../tv_0s4usqeb_nasan_risk_score_postion_size_estimator.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/0S4UsqEb-Nasan-Risk-Score-Postion-Size-Estimator/

Publication ID: 0S4UsqEb. Source SHA-256: 9bb65632d224d9ca806e230148b053fade25a5d4059818f3100291f44e3fa120. Raw-description SHA-256: 103304aa86f2e578d070bfed884469bb2b99a0806f5efeefd306530316838773.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
