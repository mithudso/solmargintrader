---

id: tv_profile_asr7nob2

name: "Liquidity Sentiment Profile [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Pair an anchored activity-at-price profile with a directional sentiment profile to inspect concentrations and low-activity regions."

registry_key: null

runner: null

evaluation: null

---

# Liquidity Sentiment Profile [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Pair an anchored activity-at-price profile with a directional sentiment profile to inspect concentrations and low-activity regions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Volume allocation, sentiment sign, automatic anchor mapping, node thresholds and multi-value-area construction are not supplied.

- Volume allocation, sentiment sign, automatic anchor mapping, node thresholds and multi-value-area construction are not supplied.

## How it works

- Aggregate price/volume over anchored periods. Draw traded activity on the right and sentiment on the left, identify high/average/low nodes and trace the price with greatest developing activity.

## Outputs and intended use

- Use profiles to review possible support/resistance, several significant value regions and developing POC changes. The tool derives these from traded price/volume rather than directly measuring available orders.

## Parameters and stated settings

- Anchor defaults Auto. Activity/sentiment visibility, node thresholds/colors, significance line, price labels, row count, relative width and range fill are configurable.

## Failure modes and caveats

- High row counts can reduce retained history or produce incomplete profiles because of drawing-object limits. Historical traded activity is not equivalent to current liquidity availability.

## Missing information and implementation boundary

- Volume allocation, sentiment sign, automatic anchor mapping, node thresholds and multi-value-area construction are not supplied.

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
right part of the profile displays the distribution of the traded activity
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
left part displays the market sentiment
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the default option is AUTO.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
using a high number of rows can display fewer historical profiles and occasionally incomplete profiles.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_asr7nob2_liquidity_sentiment_profile_luxalgo](../tv_asr7nob2_liquidity_sentiment_profile_luxalgo.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/asr7nOb2-Liquidity-Sentiment-Profile-LuxAlgo/

Publication ID: asr7nOb2. Source SHA-256: 767329213ebf30dfbe8522e0629db09ad9f4a0818e3f43d2f75f911427269b48. Raw-description SHA-256: 143054e211c45d20aac587f2ea5e063d4cd5482c573d3d7144cbbb3012c9eea8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
