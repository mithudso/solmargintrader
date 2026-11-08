---

id: tv_profile_lr5qd0kk

name: "Screener - Mean Reversion Channel"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Screen a user-defined watchlist for instruments currently inside the overbought or oversold zones of a separate Mean Reversion Channel model."

registry_key: null

runner: null

evaluation: null

---

# Screener - Mean Reversion Channel

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Screen a user-defined watchlist for instruments currently inside the overbought or oversold zones of a separate Mean Reversion Channel model.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: The companion channel formula, numerical zone cutoffs, category sorting and bar-close confirmation are absent from this description.

- The companion channel formula, numerical zone cutoffs, category sorting and bar-close confirmation are absent from this description.

## How it works

- Evaluate the companion channel on selected symbols and classify qualifying zones as strong, normal or weak. Sort/list symbols by these zone categories.

## Outputs and intended use

- A Nothing Interesting result means no configured asset currently meets a selected zone test. Use the list to focus further chart review rather than assuming that an extreme must reverse.

## Parameters and stated settings

- Up to forty symbols, scan zones and timeframe are configurable. The default list is empty and must be configured.

## Failure modes and caveats

- The author warns that many cross-symbol requests can slow the screen. Channel extremes can persist through trends, and an arbitrary current watchlist is not a historical universe.

## Missing information and implementation boundary

- The companion channel formula, numerical zone cutoffs, category sorting and bar-close confirmation are absent from this description.

## Data requirements

Required inputs: OHLCV for user-defined watchlist, companion Mean Reversion Channel rules.

Repository input-class support: unavailable or unresolved. No assets are configured by default and no aligned multi-symbol history is supplied; a historical screening universe cannot be inferred.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
scanning through up to 40 symbols
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
By default, no asset is define.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
If the screener displays "Nothing Interesting". It simply means none of the screened assets are within the Overbought/Oversold Zone.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lr5qd0kk_screener_mean_reversion_channel](../tv_lr5qd0kk_screener_mean_reversion_channel.md)

## Source

https://www.tradingview.com/script/Lr5QD0kK-Screener-Mean-Reversion-Channel/

Publication ID: Lr5QD0kK. Source SHA-256: ea4a75d243ad03b55f89e43d2e9739679a08c4747710b2c82a031768638f0668. Raw-description SHA-256: f7551d398bac4b6952405dd932809f089a772827f8fa0065acb0fe54992fdc4f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
