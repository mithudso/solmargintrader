---

id: tv_profile_c8rargoe

name: "Relative Crypto Dominance Polar Chart [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Relative Crypto Dominance Polar Chart compares selected instruments using a custom activity-and-volatility notion of dominance. It is not conventional market-cap dominance: radius represents volatility and arc length represents traded dollar volume. Larger polar regions therefore identify assets with greater combined activity on those dimensions. The display is intended to make cross-asset comparisons immediate and can be applied to tickers beyond the default cryptocurrencies. It does not supply an allocation rule or claim that a larger region forecasts superior returns."

registry_key: null

runner: null

evaluation: null

---

# Relative Crypto Dominance Polar Chart [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Relative Crypto Dominance Polar Chart compares selected instruments using a custom activity-and-volatility notion of dominance. It is not conventional market-cap dominance: radius represents volatility and arc length represents traded dollar volume. Larger polar regions therefore identify assets with greater combined activity on those dimensions. The display is intended to make cross-asset comparisons immediate and can be applied to tickers beyond the default cryptocurrencies. It does not supply an allocation rule or claim that a larger region forecasts superior returns.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Volatility estimator and dollar-volume normalization defining dominance are missing.

- Volatility estimator and dollar-volume normalization defining dominance are missing.

## How it works

- Measure volatility and traded dollar volume over the selected aggregation period.
- Map volatility to polar radius and dollar volume to arc length, with optional sorting and mean reference.
- Automatically select an aggregation period from chart timeframe unless overridden.

## Outputs and intended use

- Polar areas, ticker/percentage labels and optional volatility mean provide comparative activity context.

## Parameters and stated settings

- Up to ten tickers; default set is described as major cryptocurrencies by capitalization, without naming the list.
- Auto maps charts up to 2m/15m/1H/4H to Hourly/Daily/Weekly/Monthly; larger charts use Yearly.
- Sorting, graph-width percentage, curved lines, colors, labels and title are configurable.

## Failure modes and caveats

- Custom dominance should not be confused with market capitalization share.
- Area perception combines radial and angular scaling; exact geometric normalization matters.
- A current top-cap default list is not a point-in-time universe.

## Missing information and implementation boundary

- Volatility formula, dollar-volume conversion, percentage denominator, default tickers and missing-symbol treatment are absent.

## Data requirements

Required inputs: selected multi-asset price and volume histories, price-to-dollar conversion when necessary.

Repository input-class support: unavailable or unresolved. Requires aligned external asset histories and consistent dollar-volume units; universe/feed coverage and conversion are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
volatility (radius) by dollar volume (arc length)
```

### E2: parameters

```text
up to ten different tickers
```

### E3: parameters

```text
timeframes up to 2m:  Hourly
[*]timeframes up to 15m: Daily
[*]timeframes up to 1H:  Weekly
[*]timeframes up to 4H:  Monthly
[*]larger timeframes:    Yearly
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_c8rargoe_relative_crypto_dominance_polar_chart_luxalgo](../tv_c8rargoe_relative_crypto_dominance_polar_chart_luxalgo.md)
- [tv_method_dominance_rotation](../../tv_method_dominance_rotation.md)

## Source

https://www.tradingview.com/script/C8RarGoe-Relative-Crypto-Dominance-Polar-Chart-LuxAlgo/

Publication ID: C8RarGoe. Source SHA-256: 73007477ef4236fac10ce9d76bad334646492d92c11f0b3373442fd534af0c54. Raw-description SHA-256: 0704b2afb1c1b50fe3e4d478d04a9ab7eac6f72ad680bbb4831ae4e1b9bb93bf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
