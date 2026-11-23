---

id: tv_profile_zsmaleyi

name: "RSI Impact Heat Map [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Evaluate the subsequent upside and downside excursion associated with a selected RSI crossing event using a two-dimensional outcome heatmap."

registry_key: null

runner: null

evaluation: null

---

# RSI Impact Heat Map [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Evaluate the subsequent upside and downside excursion associated with a selected RSI crossing event using a two-dimensional outcome heatmap.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for percent-mode post-crossing excursion pairs with caller-selected RSI settings, threshold, direction and N; ATR mode and exact heatmap parity remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Choose an RSI series/length, crossing direction, threshold and future horizon N. A crossover/crossunder through that threshold creates an event at close C. In percentage mode, record the highest upward and lowest downward displacement from C over the subsequent N bars, scaled by 100/C, as that event’s outcome pair.
- Store each completed pair separately. Optional ATR scaling and a percentile-trimmed two-dimensional heatmap visualize the outcome distribution, but their exact ATR reference, clipping and color equations are not specified.

## Outputs and intended use

- Quadrants distinguish two-sided volatility, predominantly bearish outcomes, small moves and predominantly bullish outcomes. This is conditional historical excursion research, not a live prediction of a completed outcome.

## Parameters and stated settings

- Event threshold/direction, horizon, scaling and outlier range are configurable. Grid size ranges ten to ninety and defaults fifty, described as 51 by 51 cells.

## Failure modes and caveats

- Overlapping event windows are dependent. Outcome collection needs future bars, and percentile clipping can hide tail risks if the chart is interpreted without its settings.

## Missing information and implementation boundary

- Exact default RSI settings, equality/boundary conventions for the future horizon, ATR reference bar, percentile cutoff and color normalization are absent. Caller-selected RSI settings and percent-mode excursions are reproducible independently of those display/ATR details.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history; this establishes input class, not verified code, full history or profitability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Impact of the event after N number of bars is measured in terms of highest and lowest displacement from the last close price.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Impact can be collected as either number of times of ATR or percentage of price.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Default value for size is 50 - meaning data is displayed in 51X51 cells.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
can vary from 10 to 90
```

### E5: mechanism, parameters, readiness

```text
Event can be either Crossover or Crossunder of RSI on certain value.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zsmaleyi_rsi_impact_heat_map_trendoscope](../tv_zsmaleyi_rsi_impact_heat_map_trendoscope.md)

## Source

https://www.tradingview.com/script/zsmaLEyI-RSI-Impact-Heat-Map-Trendoscope/

Publication ID: zsmaLEyI. Source SHA-256: 42e3d5110158bd07d4dcc53e1fcc9fac99a02ed6afa77db7b18b4096fd2bb30a. Raw-description SHA-256: 167684d4b05955237817430a0d1779bc58802c0390a26e87bd906ccd1037dca8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
