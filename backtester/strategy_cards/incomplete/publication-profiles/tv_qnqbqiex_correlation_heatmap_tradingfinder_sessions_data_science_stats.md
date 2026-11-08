---

id: tv_profile_qnqbqiex

name: "Correlation HeatMap [TradingFinder] Sessions Data Science Stats"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Correlation HeatMap tracks how each selected asset relates to a central reference through time, rather than showing only a static correlation table. Session overlays align relationship changes with market opens, helping users investigate intermarket shifts or portfolio exposure. The source describes color magnitude and sign but does not establish a specific causal interpretation or an executable hedge model."

registry_key: null

runner: null

evaluation: null

---

# Correlation HeatMap [TradingFinder] Sessions Data Science Stats

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Correlation HeatMap tracks how each selected asset relates to a central reference through time, rather than showing only a static correlation table. Session overlays align relationship changes with market opens, helping users investigate intermarket shifts or portfolio exposure. The source describes color magnitude and sign but does not establish a specific causal interpretation or an executable hedge model.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Whether correlation operates on prices or returns is unspecified.

- Whether correlation operates on prices or returns is unspecified.

## How it works

- Calculate rolling correlation between the main symbol and each compared asset and arrange the results as asset rows across a time axis.
- Optionally overlay forex or equity session starts; standard market modes use the active chart symbol as reference while custom mode allows a chosen reference.

## Outputs and intended use

- Warm colors indicate negative correlation and cool colors positive; stronger shades represent greater magnitude. Inspect shifts for setup context or exposure review.

## Parameters and stated settings

- Custom mode supports up to 20 compared symbols. Correlation Period controls the window; market mode, custom symbols and session visibility are configurable without numeric defaults.

## Failure modes and caveats

- Analytical: correlations can change rapidly, common trends can create misleading price-level correlation and correlation alone does not establish capital flow or hedge ratios.

## Missing information and implementation boundary

- Price-versus-return input, coefficient formula, synchronization/missing-bar handling, session timezone and default symbol sets are unspecified.

## Data requirements

Required inputs: main and caller-selected comparison-symbol price histories, optional caller session settings.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to 20 Compared Symbols.
```

### E2: mechanism, parameters, readiness

```text
Correlation Period: Allows you to set how many historical bars are used for calculating correlation.
```

### E3: outputs_and_use, readiness

```text
Warm colors (e.g. red, orange) suggest strong negative correlation
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_intermarket_correlation](../../tv_method_intermarket_correlation.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_qnqbqiex_correlation_heatmap_tradingfinder_sessions_data_science_stats](../tv_qnqbqiex_correlation_heatmap_tradingfinder_sessions_data_science_stats.md)
- [xs_momentum](../../xs_momentum.md)

## Source

https://www.tradingview.com/script/QNqBQIEx-Correlation-HeatMap-TradingFinder-Sessions-Data-Science-Stats/

Publication ID: QNqBQIEx. Source SHA-256: 6d03c5e1d11d555b83f98b1005a333d66eca3cf096116af4998ea1a75e679928. Raw-description SHA-256: 29a2f3a601cdecaefe3b1d565b311333d89b6ceb26c27b7e0d8d6afe392dd575.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
