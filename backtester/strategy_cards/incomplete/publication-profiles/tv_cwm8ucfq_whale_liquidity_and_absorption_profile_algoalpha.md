---

id: tv_profile_cwm8ucfq

name: "Whale Liquidity and Absorption Profile [AlgoAlpha]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Map lower-timeframe participation and wick-based absorption proxies into profiles to inspect possible price-reaction regions."

registry_key: null

runner: null

evaluation: null

---

# Whale Liquidity and Absorption Profile [AlgoAlpha]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Map lower-timeframe participation and wick-based absorption proxies into profiles to inspect possible price-reaction regions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core absorption proxy is described, but its directional-volume allocation and percentile/peak contracts are not reproducible.

- Intrabar directional-volume and wick allocation
- Percentile sample and binning equations
- Absorption peak/zone lifecycle

## How it works

- Rank intrabar volume by percentile into strong/weak classes, aggregate bullish/bearish samples into price bins and subtract sell from buy volume for delta. Treat bullish volume in upper wicks and bearish volume in lower wicks as absorption; detect local profile peaks as zones.

## Outputs and intended use

- Display stacked activity, delta cells, absorption profile, rolling absorption heatmap and tiered bubbles. Strong-only mode excludes weak samples; the author recommends two instances when drawing limits prevent simultaneous views.

## Parameters and stated settings

- Lookback, profile resolution, percentile strength and display modes are configurable. Historical absorption snapshots roll over five bars; numerical threshold defaults are omitted.

## Failure modes and caveats

- Directional lower-timeframe volume is a proxy, not direct observation of whales or passive absorption. Fine bins and drawing limits can create incomplete history, and percentile classification changes with its sample.

## Missing information and implementation boundary

- Buy/sell sign rule, bin allocation, percentile window, wick-volume attribution and peak neighborhood/zone lifecycle are not fully specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described input class; source-code parity and complete history remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Bullish volume occurring in upper wicks and bearish volume occurring in lower wicks.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
rolling 5-bar heatmap snapshots
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Local highs in the absorption profile compared against neighboring bins.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cwm8ucfq_whale_liquidity_and_absorption_profile_algoalpha](../tv_cwm8ucfq_whale_liquidity_and_absorption_profile_algoalpha.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/cWm8UcfQ-Whale-Liquidity-and-Absorption-Profile-AlgoAlpha/

Publication ID: cWm8UcfQ. Source SHA-256: bbf8552b70158a0d23d4ce5bdee331f964c2b3d04c7da5651b9c0e9836a5ceac. Raw-description SHA-256: f1cd40ca26f0c0c08443d683659f00e831f8b3e99ad2a7b243e4f0eae3ac3617.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
