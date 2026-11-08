---

id: tv_profile_yjxpjg0y

name: "Multi-Asset Performance [Spaghetti] - By Leviathan"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Monitor relative performance across a caller-selected asset group using price, open interest or on-balance volume. The spaghetti display emphasizes leaders, laggards and changes around an anchor, with auxiliary relationship statistics for rotation or pair-research ideas."

registry_key: null

runner: null

evaluation: null

---

# Multi-Asset Performance [Spaghetti] - By Leviathan

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Monitor relative performance across a caller-selected asset group using price, open interest or on-balance volume. The spaghetti display emphasizes leaders, laggards and changes around an anchor, with auxiliary relationship statistics for rotation or pair-research ideas.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Anchored Price return/group mean is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Values reset at a periodic boundary, the visible chart’s left edge, or a chosen timestamp, then accumulate percentage/net changes. Optional SMA smoothing reduces visual noise.
- The benchmark is either the group average or first ticker. Correlation and beta use that reference over a selected lookback, while RSI describes each series.
- A vertical distribution profile groups performance around the mean; ranked highlighting and gradients emphasize extremes.
- For caller-selected symbols and anchor observation a,PriceReturn_i(t)=100*(Price_i(t)/Price_i(a)-1),requiring nonzero anchor. Reset a at caller-selected periodic boundary or use supplied timestamp/visible-range anchor. Group mean=arithmetic average of selected valid returns or the selected first ticker reference. OI/OBV,beta and profile extras excluded.

## Outputs and intended use

- Multi-series lines, areas, columns or circles, labels, screener metrics and the group mean support comparison.
- The author suggests hedging, mean reversion and pairs applications but does not supply a trade spread, hedge ratio execution rule or validated allocation.
- Usable scope: Anchored Price return/group mean. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Three customizable groups of up to 30 tickers; displayed group, data type and source timeframe.
- Anchor mode, SMA length, top/bottom highlight count, reference/RSI lengths and appearance. The profile has 10 nodes.

## Failure modes and caveats

- Visible-range anchoring makes the result dependent on the user’s viewport. OI coverage varies by instrument; OBV can cross zero, complicating percentage returns.
- The prose treats beta as an expected move ratio; it does not establish a stable forecast or capture nonlinear dependence.

## Missing information and implementation boundary

- Exact accumulation/base handling for OI and OBV, beta/correlation input transformation, missing-data treatment and profile bin rules are absent.

## Data requirements

Required inputs: aligned multi-symbol OHLCV for caller asset groups, open interest series when selected, caller anchor timeframe and symbol definitions.

Repository input-class support: unavailable or unresolved. Ordinary caller-selected symbol OHLCV supports anchored Price comparisons; selected cache coverage/alignment is unverified. Optional OI requires a separate unverified external feed; OBV/base conventions remain formula limitations.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, readiness

```text
cumulative percentage changes or returns of 30 symbols
```

### E2: purpose, mechanism, parameters, outputs_and_use, readiness

```text
three groups of up to 30 tickers each
```

### E3: purpose, mechanism, parameters, outputs_and_use, readiness

```text
You can choose between Price, OI, and OBV.
```

### E4: purpose, mechanism, parameters, outputs_and_use, readiness

```text
The input "Visible Range" is auto-adjustable as it starts the accumulation at the leftmost bar on your chart
```

### E5: purpose, mechanism, parameters, outputs_and_use, readiness

```text
vertical volume profile-like display with 10 zones/nodes
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
This indicator visualizes the cumulative percentage changes or returns of 30 symbols over a given period and offers a unique set of tools and data analytics for deeper insight into the performance of different assets.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
This input allows you to select the data that will be considered as the group mean. You can choose between Group Average (the average value of all assets in the group) or First Ticker (the value of the ticker that is positioned first on the group's list). The mean is then used in calculations such as correlation (as the second variable) and beta (as a benchmark). You can also choose to plot the mean by clicking on the checkbox.
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
Periodic inputs (e.g. daily, monthly, etc.) determine when the values are reset to zero and begin accumulating again until the period is over. This visualizes the net change in the data over each period. The input "Visible Range" is auto-adjustable as it starts the accumulation at the leftmost bar on your chart, displaying the net change in your chart's visible range. There's also the "Timestamp" option, which allows you to select a specific point in time from where the values are accumulated. The timestamp anchor can be dragged to a desired bar via Tradingview's interactive option. Timestamp is particularly useful when looking for outperformers/underperformers after a market-wide move. The input positioned next to the period selection determines the timeframe on which the data is based. It's best to leave it at default (Chart Timeframe) unless you want to check the higher timeframe structure of the data.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_yjxpjg0y_multi_asset_performance_spaghetti_by_leviathan](../../../strategy_research/tv_yjxpjg0y_multi_asset_performance_spaghetti_by_leviathan.md)
- [xs_momentum](../../../strategy_research/xs_momentum.md)

## Source

https://www.tradingview.com/script/yJxpjg0Y-Multi-Asset-Performance-Spaghetti-By-Leviathan/

Publication ID: yJxpjg0Y. Source SHA-256: 85e712f55ca10476af2ab0fc9b00867ad1470042a85569bcc65cf7e85248db8c. Raw-description SHA-256: 982ac44852f8b8ea2551e0ad4ec578c11259ca8be96353aefd9d6394153c9f66.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
