---

id: tv_profile_tk7fhng9

name: "Adaptive Trend Finder (log)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Automatically choose a short- or long-horizon trend channel using statistical fit on logarithmically scaled price data."

registry_key: null

runner: null

evaluation: null

---

# Adaptive Trend Finder (log)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Automatically choose a short- or long-horizon trend channel using statistical fit on logarithmically scaled price data.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Selection objective, candidate ranges, residual-band calculation, refresh timing and any entry/exit rules are missing.

- Selection objective, candidate ranges, residual-band calculation, refresh timing and any entry/exit rules are missing.

## How it works

- Use Pearson correlation to locate an optimal regression channel and report the selected channel length and trend strength. Logarithmic regression describes proportional price movement rather than a constant absolute-price slope.

## Outputs and intended use

- Read the channel as trend direction/intensity context and choose the horizon family relevant to the analysis. Marketing claims of precision do not establish accuracy or profitable trading results.

## Parameters and stated settings

- The disclosed choice is long-term versus short-term detection. Candidate lengths, correlation thresholds and band widths are not specified.

## Failure modes and caveats

- Optimizing channel fit can overfit a recent segment. Log prices require positive values, and strong fitted correlation does not mean a trend will continue.

## Missing information and implementation boundary

- Selection objective, candidate ranges, residual-band calculation, refresh timing and any entry/exit rules are missing.

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
the choice between automatic detection of the long-term or short-term trend channel.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Leveraging the robust statistical measure of the Pearson coefficient
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
its strategic use of the logarithmic scale for regression channels.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_linear_regression_channel](../tv_method_linear_regression_channel.md)
- [tv_tk7fhng9_adaptive_trend_finder_log](../tv_tk7fhng9_adaptive_trend_finder_log.md)

## Source

https://www.tradingview.com/script/tk7fHng9-Adaptive-Trend-Finder-log/

Publication ID: tk7fHng9. Source SHA-256: 76328337c4559410ac1555c974e5609397f8ad70426dc17ca13da31f16259822. Raw-description SHA-256: 0b95a94a826cdd8fe5e43b5cc93f50ff43f253d0716fb1e2bfd3e059e41bdda5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
