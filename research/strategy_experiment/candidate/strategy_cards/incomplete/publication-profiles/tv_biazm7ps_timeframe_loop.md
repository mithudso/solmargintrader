---

id: tv_profile_biazm7ps

name: "Timeframe Loop"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Visualize the sequence of price changes inside a parent candle as a loop with optional finer loops and miniature candles."

registry_key: null

runner: null

evaluation: null

---

# Timeframe Loop

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Visualize the sequence of price changes inside a parent candle as a loop with optional finer loops and miniature candles.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact price-coordinate scaling, gap handling, live incomplete segments, retained history and any analytical signal rules are absent.

- Exact price-coordinate scaling, gap handling, live incomplete segments, retained history and any analytical signal rules are absent.

## How it works

- Place the first half of lower-timeframe progression toward the right, then return left toward the close. A still lower base timeframe can show nested progression and optionally follow its own out-and-back loop.

## Outputs and intended use

- Inspect chronological intrabar price movement without switching charts. Mini-candles, steps and left/right labels explain the transformed coordinates; the shape is a display convention rather than a cyclical forecast.

## Parameters and stated settings

- Choose two lower timeframes, lowest-frame visibility, looping, mini-candles and steps. Both must be below chart resolution; LTF/BTF must be at least two and CTF/BTF below five hundred.

## Failure modes and caveats

- Very fine base intervals can cause runtime errors and limited history. Odd half-counts alter turning geometry, so shape alone should not be mistaken for market symmetry.

## Missing information and implementation boundary

- Exact price-coordinate scaling, gap handling, live incomplete segments, retained history and any analytical signal rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary OHLCV supports the disclosed calculation class; this does not establish source-code parity or verified historical coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
going to the right during the first half and returning to the left towards its closing point.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The ratio LTF / BTF should be equal or higher than 2
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the ratio CTF / BTF should be lower than 500
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)

## Source

https://www.tradingview.com/script/bIaZM7ps-Timeframe-Loop/

Publication ID: bIaZM7ps. Source SHA-256: 041afb71a8f9859661c85597719f5adad27c4ec173ca5d945068d9c2facff575. Raw-description SHA-256: afe71700d1b1c7af12580559ffe5f0fb9500ab17b55efc43efbc2d9d1ab9cd79.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
