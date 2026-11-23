---

id: tv_profile_0enoetmo

name: "SmartPhase Analyzer"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Summarize a market regime from a selectable collection of statistical diagnostics, allowing the reader to compare a blended condition score with its recent distribution."

registry_key: null

runner: null

evaluation: null

---

# SmartPhase Analyzer

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Summarize a market regime from a selectable collection of statistical diagnostics, allowing the reader to compare a blended condition score with its recent distribution.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: Normalization formulas, aggregation weights, the meaning of PLF/SRI, handling of missing benchmark data and exact regime boundaries are not provided.

- Normalization formulas, aggregation weights, the meaning of PLF/SRI, handling of missing benchmark data and exact regime boundaries are not provided.

## How it works

- Normalize enabled metrics, blend them into a composite score and evaluate that score against rolling mean-and-standard-deviation thresholds.
- The menu includes risk-adjusted measures, benchmark-relative statistics, dispersion, entropy, drawdown and momentum diagnostics. The author identifies StatMetrics as the underlying library.

## Outputs and intended use

- A colored histogram shows the composite. A chart label and background communicate strongly bullish, mildly bullish, sideways, mildly bearish or strongly bearish regimes.
- Use those regimes as context for discretionary or separately specified systematic rules; the publication does not define entries and exits.

## Parameters and stated settings

- Metrics can be enabled or disabled individually; no lookback defaults, weights or benchmark symbol are disclosed.

## Failure modes and caveats

- Combining correlated diagnostics can overrepresent the same market property. Rolling thresholds can change regime interpretation as recent volatility changes.

## Missing information and implementation boundary

- Normalization formulas, aggregation weights, the meaning of PLF/SRI, handling of missing benchmark data and exact regime boundaries are not provided.

## Data requirements

Required inputs: ohlcv, benchmark return series.

Repository input-class support: unavailable or unresolved. Chart history supports local metrics, but the selected benchmark and aligned benchmark history are not established by the saved description.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Composite score calculated from 13+ toggleable statistical indicators:
```

### E2: purpose, mechanism, outputs_and_use, parameters

```text
Sharpe, Sortino, Omega, Alpha, Beta, CV, R², Entropy, Drawdown, Z-Score, PLF, SRI, and Momentum Rank
```

### E3: purpose, mechanism, outputs_and_use, parameters

```text
Uses dynamic thresholds (mean ± std deviation) to classify regime states:
```

### E4: purpose, mechanism, outputs_and_use, parameters

```text
Benchmark-aware metrics (Alpha, Beta, etc.)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_0enoetmo_smartphase_analyzer](../tv_0enoetmo_smartphase_analyzer.md)

## Source

https://www.tradingview.com/script/0eNOetmO-SmartPhase-Analyzer/

Publication ID: 0eNOetmO. Source SHA-256: 00b2fb7605e4cb22859d39298b430052d9f52a02794d6fec440fe996fa752cca. Raw-description SHA-256: 0d3a712713c4607a188a8bb5c43fdfe3221666421f45c5302d7d95540c777ea3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
