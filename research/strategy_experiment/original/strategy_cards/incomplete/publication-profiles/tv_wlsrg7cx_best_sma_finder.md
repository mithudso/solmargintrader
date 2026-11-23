---

id: tv_profile_wlsrg7cx

name: "Best SMA Finder"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Select a historically favorable simple-moving-average length using a composite backtest ranking rather than manual trial and error."

registry_key: null

runner: null

evaluation: null

---

# Best SMA Finder

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Select a historically favorable simple-moving-average length using a composite backtest ranking rather than manual trial and error.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Exact entry/exit triggers, robustness weights, transaction costs, fill timing, sample split and zero-loss profit-factor treatment are missing.

- Exact entry/exit triggers, robustness weights, transaction costs, fill timing, sample split and zero-loss profit-factor treatment are missing.

## How it works

- Run individual tests for candidate lengths, collect profit factor, win rate and trade count, reject candidates below a minimum-trade requirement and select the highest robustness score. The score incorporates log-scaled trade frequency.

## Outputs and intended use

- Plot the selected SMA in blue and optionally display its length and backtest statistics in a top-right table. The selected fit is exploratory and the publication explicitly lacks full sizing/stop logic.

## Parameters and stated settings

- Lengths span 10 through 1000, described as 991 candidates. Choose Long Only or Buy & Sell, minimum trade count and table visibility, which defaults on.

## Failure modes and caveats

- Selecting the winner on the same history creates multiple-testing and overfitting risk. An impressive in-sample score is not an out-of-sample performance result.

## Missing information and implementation boundary

- Exact entry/exit triggers, robustness weights, transaction costs, fill timing, sample split and zero-loss profit-factor treatment are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class. Code parity, complete history and forward performance remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
from 10 to 1000
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Exhaustive SMA optimization across 991 values
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
A composite Robustness Score, which integrates Profit Factor, number of trades (log-scaled), and win rate.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Enable or disable the summary stats table (default: enabled)
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Not a full trading strategy with position sizing or stop-loss logic
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/WLSrG7cX-Best-SMA-Finder/

Publication ID: WLSrG7cX. Source SHA-256: ab4b2b62ef67c6d8b84a95d87e3d1174cb32e9636abeff873fc26fdd4299c72a. Raw-description SHA-256: fe8a9ca1b9cba048e5aa4bd47e90d67275cbda3dff8b11a484b1dea3dc4c6e99.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
