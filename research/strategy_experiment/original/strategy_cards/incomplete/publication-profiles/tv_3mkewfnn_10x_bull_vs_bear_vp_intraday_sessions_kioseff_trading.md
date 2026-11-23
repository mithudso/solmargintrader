---

id: tv_profile_3mkewfnn

name: "10x Bull Vs. Bear VP Intraday Sessions [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare estimated buying and selling participation across selected intraday ranges by separating volume-at-price distributions and their important price levels."

registry_key: null

runner: null

evaluation: null

---

# 10x Bull Vs. Bear VP Intraday Sessions [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare estimated buying and selling participation across selected intraday ranges by separating volume-at-price distributions and their important price levels.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: The prose omits volume allocation, delta classification, lower-timeframe requirements, value-area expansion and tie-breaking rules.

- The prose omits volume allocation, delta classification, lower-timeframe requirements, value-area expansion and tie-breaking rules.

## How it works

- Construct fixed-range volume profiles, a range-anchored delta ladder and separate bullish/bearish distributions. Combined and separated points of control and value areas can be displayed.

## Outputs and intended use

- Green and red profiles identify the author-labeled buying and selling volume. Compare their concentration and value-area placement as contextual evidence of participation, rather than as a self-contained entry rule.

## Parameters and stated settings

- Configure up to ten session ranges, a value-area target, profile styles and colors. The author permits up to 2000 rows per visible range.

## Failure modes and caveats

- More rows increase display granularity but do not establish true bid/ask trade classification. The terms buying and selling require a disclosed allocation rule before they can be treated as aggressor flow.

## Missing information and implementation boundary

- The prose omits volume allocation, delta classification, lower-timeframe requirements, value-area expansion and tie-breaking rules.

## Data requirements

Required inputs: intraday price and volume, buy/sell volume classification inputs.

Repository input-class support: unavailable or unresolved. Intraday OHLCV is a possible profile input, but the author does not disclose how volume is classified or allocated; precise data requirements remain unresolved.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
[*] Up To 10 Fixed Ranges!
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]Up to 2000 Profile Rows per Visible Range
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]Standard Poc and Value Area Lines, in Addition to Separated POCs and Value Area Lines for Bull Profiles and Bear Profiles
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Green profiles = buying volume
Red profiles = selling volume
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_3mkewfnn_10x_bull_vs_bear_vp_intraday_sessions_kioseff_trading](../tv_3mkewfnn_10x_bull_vs_bear_vp_intraday_sessions_kioseff_trading.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/3mKewfnN-10x-Bull-Vs-Bear-VP-Intraday-Sessions-Kioseff-Trading/

Publication ID: 3mKewfnN. Source SHA-256: 98dd5ea3d410a2a7db4cfafd2d62feb55925ee54b6d35b09093250e5bd3ca7c9. Raw-description SHA-256: 16ac5e0dc393da019248c2e2d1811233090ff23a9842f33e3acfa8d998b6c204.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
