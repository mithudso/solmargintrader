---

id: tv_profile_yclsgmij

name: "Random Synthetic Asset Generation"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Random Synthetic Asset Generation creates pseudo-random price and volume series for testing financial scripts under artificial scenarios. The source explicitly proposes embedding the generator into another script for random-data backtests, making this a financial research utility rather than decorative randomness. It warns that applying another indicator to the displayed generator instance does not reliably share the same generated path."

registry_key: null

runner: null

evaluation: null

---

# Random Synthetic Asset Generation

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Random Synthetic Asset Generation creates pseudo-random price and volume series for testing financial scripts under artificial scenarios. The source explicitly proposes embedding the generator into another script for random-data backtests, making this a financial research utility rather than decorative randomness. It warns that applying another indicator to the displayed generator instance does not reliably share the same generated path.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Random-return distribution, OHLC construction and RNG progression are undisclosed.

- Random-return distribution, OHLC construction and RNG progression are undisclosed.

## How it works

- Generate synthetic candle-like data with a selected pseudo-random-number method and seed; vary wick amplitude and price scale.
- Generate random volume and expose true-range/candle-change series for optional plotting.

## Outputs and intended use

- Embed the generator into a test script to keep analysis and synthetic data in one instance; separate identically configured displays can show price and volume.

## Parameters and stated settings

- Two generator methods are offered: Ricardo Santos and Wichmann-Hill. Seed, Intrabar Volatility and Price Multiplier are inputs; zero intrabar volatility means no wicks.

## Failure modes and caveats

- The author says indicator-on-indicator use produces different instances; analytical: arbitrary random paths may omit market dependence, tails and volume-price structure.

## Missing information and implementation boundary

- Exact return distribution, random-state progression, OHLC consistency and cross-instance reproducibility are not documented.

## Data requirements

Required inputs: generator settings and seed.

Repository input-class support: unavailable or unresolved. This generates synthetic data rather than requiring market OHLCV, but caller settings and an embedded implementation are necessary to reproduce a specific path.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, readiness

```text
to make it possible to backtest on random data, for example
```

### E2: parameters, readiness

```text
two methods for generating the pseudo-random numbers
```

### E3: parameters, readiness

```text
0 = no wicks
```

### E4: risks, readiness

```text
impossible to use this indicator as input for other indicators
```

## Source

https://www.tradingview.com/script/YcLSGMIJ-Random-Synthetic-Asset-Generation/

Publication ID: YcLSGMIJ. Source SHA-256: 9725886b9ac0f4092303dc90bf2706e8cf9061bd8dc4799b5b6aa73393a3b71c. Raw-description SHA-256: 02e0e58e4f80e96b93ac73e51d21961d75962974142d36de8890ab1ec002a728.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
