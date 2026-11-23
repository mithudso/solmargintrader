---

id: tv_profile_mi5dl7bi

name: "Sharpe and Sortino Ratios"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Evaluate risk-adjusted price-return performance relative to a fixed annual benchmark or an aligned comparison asset."

registry_key: null

runner: null

evaluation: null

---

# Sharpe and Sortino Ratios

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Evaluate risk-adjusted price-return performance relative to a fixed annual benchmark or an aligned comparison asset.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for periodic Sharpe and active-return information ratios with supplied aligned samples and caller dispersion/zero conventions; annual conversion and Sortino parity remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For supplied same-period returns r and periodic risk-free return f, Sharpe=(mean(r)-f)/SD(r). For aligned investment/benchmark returns r,b, information ratio=mean(r-b)/SD(r-b). Caller must select sample/population dispersion and zero-dispersion policy because the description does not fix them. These periodic formulas avoid guessing annual-to-period conversion.
- Request chosen-timeframe percentage changes,compound them into monthly samples when history spans two months or daily samples when it spans two days,and compute excess mean divided by total/downside dispersion. Benchmark-symbol mode uses active-return/tracking-error style ratios with aligned spread requests and dividend/extended-session adjustments.

## Outputs and intended use

- Display return series,benchmark line,new-period highlights and a table/data-window of ratios/sample information. These describe asset price returns,not an actual trading portfolio.

## Parameters and stated settings

- Returns timeframe defaults one month,maximum samples sixty and annual fixed benchmark two percent. Less than two days produces no collected returns. Benchmark choice/timeframe/sample count are configurable.

## Failure modes and caveats

- Yield-valued symbols are unsuitable price-return benchmarks,as the author warns. Results depend on sampling,adjustments and downside convention; a high historical ratio does not establish future sustainability.

## Missing information and implementation boundary

- Exact annual-to-period conversion,downside-deviation denominator/zero cases,partial-period compounding and benchmark request mappings require the RiskMetrics library/code.

## Data requirements

Required inputs: chart price history, manual annual benchmark or aligned benchmark-price series.

Repository input-class support: unavailable or unresolved. Fixed-rate mode can use chart prices,while the full benchmark-symbol feature requires additional aligned dividend-adjusted price histories.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Sharpe Ratio = (𝑅𝑎 − 𝑅𝑓) / 𝜎𝑎
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Sortino Ratio = (𝑅𝑎 − 𝑅𝑓) / 𝜎𝑑
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default value of 2%
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default timeframe is "1M"
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default value is 60 periods.
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Track returns over monthly periods if the chart's data spans at least two months.
```

### E7: mechanism, parameters, readiness

```text
Sharpe Ratio = (𝑅𝑎 − 𝑅𝑓) / 𝜎𝑎
```

### E8: mechanism, parameters, readiness

```text
𝐼𝑅 = (𝑅𝑝 − 𝑅𝑏) / 𝑇𝐸
```

### E9: mechanism, parameters, readiness

```text
𝑇𝐸 = Tracking error (volatility of 𝑅𝑝 − 𝑅𝑏)
```

## Source

https://www.tradingview.com/script/Mi5DL7bi-Sharpe-and-Sortino-Ratios/

Publication ID: Mi5DL7bi. Source SHA-256: a4033d018d0d00d0c116824b5c73c88f00010beb477b6bcc62f93d828dbebb0b. Raw-description SHA-256: 8555883720d1eb25ede55769eb37c439697bf4f6721047fb7c30813047d0ee38.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
