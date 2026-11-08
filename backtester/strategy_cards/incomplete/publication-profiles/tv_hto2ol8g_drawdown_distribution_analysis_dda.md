---

id: tv_profile_hto2ol8g

name: "Drawdown Distribution Analysis (DDA) "

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Place the current asset-price drawdown within its historical distribution and add return/risk summaries. DDA supports contextual risk monitoring and allocation research; it does not establish a portfolio’s realized drawdown unless the supplied price series represents that portfolio."

registry_key: null

runner: null

evaluation: null

---

# Drawdown Distribution Analysis (DDA)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Place the current asset-price drawdown within its historical distribution and add return/risk summaries. DDA supports contextual risk monitoring and allocation research; it does not establish a portfolio’s realized drawdown unless the supplied price series represents that portfolio.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Raw running-maximum drawdown/nearest-rank distribution is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Track the running maximum and express current price decline as a signed percentage. Historical nearest-rank percentiles, mean/deviation bands and z-scores locate the current decline within the selected sample.
- Additional metrics include annualized Sharpe/Sortino, annual return divided by maximum drawdown, drawdown-tail percentile/average measures and volatility-normalized drawdown. A composite score combines Sharpe and percentile rank.
- Percentile tiers classify risk; alerts report tier changes, extreme z-scores, new maximum decline and deteriorating composite/Sharpe conditions.
- Peak(t)=max supplied prices from sample start through t;DD(t)=100*(P(t)-Peak(t))/Peak(t),requiring positive/nonzero peak. For caller trailing window sort DD values and choose nearest-rank percentile p at ceil(p*N/100),p=5,10,25,50,75,90,95. This qualifies unsmoothed distribution only;composite,smoothing,annualized ratios and optional Treasury feed remain limitations.

## Outputs and intended use

- Distribution bands, position lines and tables support comparative risk assessment; suggested allocation and timing rules remain heuristics without measured net results.
- The drawdown-tail measures are labeled VaR/CVaR in the prose but describe historical drawdown observations, not a fixed-horizon return-loss forecast.
- Usable scope: Raw running-maximum drawdown/nearest-rank distribution. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Distribution lookback100–2000 bars, smoothing1–50, price source, live Treasury yield or manual risk-free rate and metric/display toggles.
- Z-score alerts use2.5/3; volatility normalization references20%; risk tiers divide percentile ranks at50/25/10.

## Failure modes and caveats

- Mean ±1.96 standard deviations is not a confidence interval for the estimated mean, and normal-tail probabilities are unjustified for dependent fat-tailed drawdowns.
- Maximum tracking/reset and smoothing choices materially alter the distribution; contradictory minimum-history recommendations and missing costs limit comparability.

## Missing information and implementation boundary

- Risk Efficiency Score formula, annualization/return conventions, smoothing order, peak reset policy and Treasury data contract are absent.

## Data requirements

Required inputs: ohlcv, US10-year Treasury yield history if dynamic risk-free mode selected.

Repository input-class support: unavailable or unresolved. OHLCV supports unsmoothed price drawdown and its historical distribution. Optional dynamic risk-free mode additionally needs US10-year Treasury yield history,whose coverage is unverified;manual-rate mode needs caller rate.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
DD(t) = (P(t) - Peak(t)) / Peak(t) × 100
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Distribution Analysis Period (100-2000 bars), Drawdown Smoothing Period (1-50 bars)
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Adjusted DD = Raw DD / (Volatility / 20%)
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
threshold levels of 2.5 or 3.0 standard deviations
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Low risk designation applies when current drawdowns perform better than 50%
```

### E6: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
moderate risk encompasses the 25th to 50th percentile range
```

### E7: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
high risk covers the 10th to 25th percentile range
```

### E8: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
extreme risk applies to the worst 10%
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
The core calculation methodology centers on a peak-tracking algorithm that continuously monitors the maximum price level achieved and calculates the percentage decline from this peak. The drawdown at any time t is defined as DD(t) = (P(t) - Peak(t)) / Peak(t) × 100, where P(t) represents the asset price at time t and Peak(t) represents the running maximum price observed up to time t.
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
The core calculation methodology centers on a peak-tracking algorithm that continuously monitors the maximum price level achieved and calculates the percentage decline from this peak. The drawdown at any time t is defined as DD(t) = (P(t) - Peak(t)) / Peak(t) × 100, where P(t) represents the asset price at time t and Peak(t) represents the running maximum price observed up to time t.
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
Statistical distribution analysis forms the analytical backbone of the indicator. The system calculates key percentiles using the ta.percentile_nearest_rank() function to establish the 5th, 10th, 25th, 50th, 75th, 90th, and 95th percentiles of the historical drawdown distribution. This approach provides a complete picture of how the current drawdown compares to historical patterns.
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
Statistical distribution analysis forms the analytical backbone of the indicator. The system calculates key percentiles using the ta.percentile_nearest_rank() function to establish the 5th, 10th, 25th, 50th, 75th, 90th, and 95th percentiles of the historical drawdown distribution. This approach provides a complete picture of how the current drawdown compares to historical patterns.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/hTo2OL8G-Drawdown-Distribution-Analysis-DDA/

Publication ID: hTo2OL8G. Source SHA-256: 54a425e27b2cbbdd0d0e8146180d79a4e876b0ba4b7936794d285b8d42e144aa. Raw-description SHA-256: 5fea9acd008eaeee7fb31b32b3d92427a322a5daf528ac7d44f013babdb8948c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
