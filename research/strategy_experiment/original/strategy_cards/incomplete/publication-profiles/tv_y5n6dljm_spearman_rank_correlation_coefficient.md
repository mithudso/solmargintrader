---

id: tv_profile_y5n6dljm

name: "Spearman Rank Correlation Coefficient"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Measure whether two selected market series tend to move monotonically together by comparing their ranked observations."

registry_key: null

runner: null

evaluation: null

---

# Spearman Rank Correlation Coefficient

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Measure whether two selected market series tend to move monotonically together by comparing their ranked observations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Tie ranking, price-versus-return choice, sample alignment and missing-value handling are absent.

- Tie ranking, price-versus-return choice, sample alignment and missing-value handling are absent.

## How it works

- Use Spearman rank correlation, described as a nonparametric alternative to Pearson correlation, on two ticker symbols. Ranking emphasizes ordering rather than raw-value linear distance.

## Outputs and intended use

- The coefficient ranges from negative one to positive one. Positive extremes indicate similar ordering and negative extremes opposite ordering; near zero means little monotonic association, not proof of independence.

## Parameters and stated settings

- The first version compares two tickers. Lookback, timeframe and default symbols are not stated.

## Failure modes and caveats

- A high rank correlation does not prove causality, cointegration or a profitable spread trade. Nonstationary price levels can create misleading associations.

## Missing information and implementation boundary

- Tie ranking, price-versus-return choice, sample alignment and missing-value handling are absent.

## Data requirements

Required inputs: aligned histories for two selected tickers.

Repository input-class support: unavailable or unresolved. The chosen pair and its aligned histories are not provided; this cannot be established from one chart's OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The value oscillates between +1 and -1.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
It is best used to discover if two variables (and in this first version of the indicator, two ticker symbols) increase and decrease together.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_y5n6dljm_spearman_rank_correlation_coefficient](../tv_y5n6dljm_spearman_rank_correlation_coefficient.md)

## Source

https://www.tradingview.com/script/y5n6dlJm-Spearman-Rank-Correlation-Coefficient/

Publication ID: y5n6dlJm. Source SHA-256: 903afaa2645423b32f123514d5ee102bf5cf57d64f6ad55731f42334f7e25132. Raw-description SHA-256: 159a2a0573dad9e7c026ed447c05e991b1a7a778aa02bd107ec4a04e08ff5baa.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
