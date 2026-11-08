---

id: tv_profile_o2toj6ez

name: "Bitcoin Monthly Seasonality [Alpha Extract]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Summarize Bitcoin performance by calendar month to compare historical seasonal tendencies and their consistency."

registry_key: null

runner: null

evaluation: null

---

# Bitcoin Monthly Seasonality [Alpha Extract]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Summarize Bitcoin performance by calendar month to compare historical seasonal tendencies and their consistency.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source gives explicit return equations, a parameterized lookback and positive-return counting code sufficient for the principal discrete monthly statistics. Optional cumulative/display boundaries need implementation choices.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate each monthly close/open percentage return or absolute price change, group observations by month, average them and compute the fraction strictly above zero. Optionally display compounded successive monthly behavior.

## Outputs and intended use

- Bars, an optional line and statistics table identify positive/negative months and highlight the strongest/weakest averages. Use the display as historical seasonality context, not a guarantee of future monthly direction.

## Parameters and stated settings

- Lookback spans one to fifteen years. Return type, cumulative mode, bar/line/axis visibility and best/worst colors are configurable; percentage and price modes are explicitly defined.

## Failure modes and caveats

- At most a modest number of observations supports each calendar bucket. Selection of the best months can overfit, while incomplete months or changing Bitcoin regimes alter interpretation.

## Missing information and implementation boundary

- The Bitcoin venue/history contract, partial-month handling, rolling-year cutoff and cumulative-mode aggregation are not fully specified. The discrete monthly statistics are nevertheless explicitly reproducible on supplied monthly bars.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; source-code parity and cached historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Percentage: (monthEndPrice / monthStartPrice - 1) × 100
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Price: monthEndPrice - monthStartPrice
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
User-defined lookback period (1-15 years).
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
if array.get(arr, i) > 0
                winCount += 1
        (winCount / totalCount) * 100
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_o2toj6ez_bitcoin_monthly_seasonality_alpha_extract](../../tv_o2toj6ez_bitcoin_monthly_seasonality_alpha_extract.md)

## Source

https://www.tradingview.com/script/o2toJ6Ez-Bitcoin-Monthly-Seasonality-Alpha-Extract/

Publication ID: o2toJ6Ez. Source SHA-256: defd6d6c1318d00cd42332435baea299432d799a8ec9861c7d649d56c3ca27c1. Raw-description SHA-256: 4c26eb438d956b1664f79173608393485fe43f97c31f3c3dd83ec78b46477800.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
