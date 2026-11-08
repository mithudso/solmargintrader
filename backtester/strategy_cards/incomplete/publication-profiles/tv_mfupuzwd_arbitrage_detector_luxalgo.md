---

id: tv_profile_mfupuzwd

name: "Arbitrage Detector [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Monitor cross-venue prices/volumes and classify the largest observed spread relative to its own historical distribution."

registry_key: null

runner: null

evaluation: null

---

# Arbitrage Detector [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Monitor cross-venue prices/volumes and classify the largest observed spread relative to its own historical distribution.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The dashboard concept is clear but the venue/data and spread/smoothing contracts are not sufficiently defined.

- Selected venue histories and symbol mapping
- Spread and percentile equations
- Adaptive smoothing recurrence

## How it works

- Query crypto exchanges or forex brokers, display sortable last/average price and volume columns and calculate a maximum-spread histogram. Split it into percentile categories and optionally smooth with EMA or an adaptive average whose efficiency ratio uses percent rank.

## Outputs and intended use

- Use source deltas and unusually wide historical spreads to investigate venue differences. The author suggests arbitrage and reversal context, but displayed last-price differences do not establish executable net returns.

## Parameters and stated settings

- Up to nineteen exchanges/thirteen brokers are described. Source mode, average length, percentile sample/full-history mode, category cutoffs, dashboard sorting and smoothing are configurable; gradient and auto smoothing default on. An EMA-nine alternative is illustrative.

## Failure modes and caveats

- Stale quotes, unit mismatches, fees, bid/ask depth and transfers can dominate apparent spreads. Full-dataset percentile mode can exceed runtime resources.

## Missing information and implementation boundary

- Venue-symbol mapping, synchronized quote policy, maximum-spread equation, percentile estimator and adaptive-average recurrence are absent.

## Data requirements

Required inputs: synchronized multi-venue prices and volumes.

Repository input-class support: unavailable or unresolved. The external source universe and aligned observations are not established by saved OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
up to 19 crypto exchanges and 13 forex brokers.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
gradient and smoothing auto features enabled.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
exponential moving average with a length of 9.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
data percent rank as the efficiency ratio.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_mfupuzwd_arbitrage_detector_luxalgo](../tv_mfupuzwd_arbitrage_detector_luxalgo.md)

## Source

https://www.tradingview.com/script/MFupUZWD-Arbitrage-Detector-LuxAlgo/

Publication ID: MFupUZWD. Source SHA-256: 70efc38d29933e570186aac49c640ce6838813ddb6f3ab6e5953e514bbb47483. Raw-description SHA-256: 917f29139e3d032aa486dbebc53a480c8ee84bd9683f24029eec3b42147c1572.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
