---

id: tv_profile_k6olgkao

name: "Relative Candle"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Distinguish a stock's own behavior from broad-market movement by drawing a candle relative to a selected index or comparison symbol."

registry_key: null

runner: null

evaluation: null

---

# Relative Candle

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Distinguish a stock's own behavior from broad-market movement by drawing a candle relative to a selected index or comparison symbol.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact relative OHLC transformation, color thresholds, price normalization and session alignment are unspecified.

- Exact relative OHLC transformation, color thresholds, price normalization and session alignment are unspecified.

## How it works

- Encode relative positive/negative movement in candle location, relative performance in color and the relative closing-range relationship in its wick. Add a background average of relative close.

## Outputs and intended use

- Use the view to notice unusual resilience, weakness or divergence from the benchmark, such as a stock rising while the market falls.

## Parameters and stated settings

- The background uses a ten-day simple moving average. The index or comparison symbol can differ; a default symbol is not given.

## Failure modes and caveats

- Relative candle geometry is synthetic and should not be read as an executable OHLC price. Benchmark choice can dominate the apparent strength.

## Missing information and implementation boundary

- Exact relative OHLC transformation, color thresholds, price normalization and session alignment are unspecified.

## Data requirements

Required inputs: chart OHLCV, aligned comparison-symbol OHLCV.

Repository input-class support: unavailable or unresolved. The study requires an index or other comparison series; the source neither identifies a fixed benchmark nor supplies aligned history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The area graph in the background shows the average relative close over a 10-day simple moving average.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The color of the candle indicates how the candle moved relative to the index.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_k6olgkao_relative_candle](../tv_k6olgkao_relative_candle.md)

## Source

https://www.tradingview.com/script/k6OlgKAO-Relative-Candle/

Publication ID: k6OlgKAO. Source SHA-256: 23b088f19d9716dc702ab2f09e03897289f6ea89a03726b73abc655ebeebe3bf. Raw-description SHA-256: 8863f25bdf40f6b23d89a1b3b29c105a193f0e61b631ebca2df1f5c16370dd73.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
