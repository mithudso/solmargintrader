---

id: tv_profile_oogzrqim

name: "RiskMetrics"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "RiskMetrics exposes periodic-return collection and risk-adjusted ratios to financial scripts without requiring a strategy declaration. Its metrics analyze the supplied return series rather than executed trades or a realized account. The library also supports excess-return comparisons against a risky benchmark. The documentation provides equations, aggregation and benchmark conventions, so a caller can reproduce the intended calculation while choosing its own return source and retained history."

registry_key: null

runner: null

evaluation: null

---

# RiskMetrics

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

RiskMetrics exposes periodic-return collection and risk-adjusted ratios to financial scripts without requiring a strategy declaration. Its metrics analyze the supplied return series rather than executed trades or a realized account. The library also supports excess-return comparisons against a risky benchmark. The documentation provides equations, aggregation and benchmark conventions, so a caller can reproduce the intended calculation while choosing its own return source and retained history.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Equations and parameterized processing rules define the financial computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Compound nonmissing percentage returns within closed daily or monthly periods and queue the completed values, removing oldest values beyond maxPeriods.
- Select monthly periods when chart history spans at least two months, daily at least two days otherwise, and no calculation below that coverage.
- Sharpe divides mean return minus periodic benchmark by return standard deviation; Sortino uses downside deviation. Benchmark overload separately compounds aligned asset and benchmark values before subtraction.

## Outputs and intended use

- Consume scalar ratios and return arrays in a financial report or indicator.
- Use annualBenchmark zero for already-excess returns and preserve gaps when requesting higher-timeframe returns to avoid duplicate compounding.

## Parameters and stated settings

- Example annual benchmark defaults to 2%. Automatic divisors are 12 monthly or 365 daily; periodsPerYear can override, such as 252.
- forceCalc defaults false, limiting ratio evaluation to the last bar.

## Failure modes and caveats

- Ratios are sensitive to return frequency, sample size and benchmark selection; they do not establish future performance.
- Boundary wording alternates between at least and more than two periods.

## Missing information and implementation boundary

- Sample-versus-population deviation and zero-risk handling are not specified; confirm these for bitwise parity.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the default input class; this does not establish source-code parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
Sharpe Ratio = (𝑅𝑎 − 𝑅𝑓) / 𝜎𝑎
```

### E2: mechanism

```text
Sortino Ratio = (𝑅𝑎 − 𝑅𝑓) / 𝜎𝑑
```

### E3: parameters

```text
default risk-free rate of 2%
```

### E4: parameters

```text
divides the `annualBenchmark` value by 12
```

### E5: parameters

```text
divides the value by 365.
```

### E6: parameters

```text
dividing by 252
```

### E7: parameters

```text
The default is `false`.
```

### E8: mechanism

```text
compounds all non-na `percentChange` values
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)

## Source

https://www.tradingview.com/script/oOgZRqiM-RiskMetrics/

Publication ID: oOgZRqiM. Source SHA-256: c1c2d848abad8dc26f9841da9730ef69ea48bc5f0b775674d5a107f81baa7894. Raw-description SHA-256: adbfe8780ad7690e02cb92fd7aebb4eee0630afbd683f79227d1b28abd433fff.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
