---

id: tv_profile_zus134uh

name: "Heat Map Seasons"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Heat Map Seasons uses distance from a regression baseline to label metaphorical warm and cold market phases. It is a deviation/regime display, not a study of calendar seasonality. Warm phases are described as active/upward and cold phases as quieter/sideways-or-bearish, with extreme gradients proposed as potential top/bottom context; those associations are not independently measured."

registry_key: null

runner: null

evaluation: null

---

# Heat Map Seasons

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Heat Map Seasons uses distance from a regression baseline to label metaphorical warm and cold market phases. It is a deviation/regime display, not a study of calendar seasonality. Warm phases are described as active/upward and cold phases as quieter/sideways-or-bearish, with extreme gradients proposed as potential top/bottom context; those associations are not independently measured.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Regression family/source, deviation normalization, gauge equation, color/state thresholds and confirmation rules are absent.

- Regression family/source, deviation normalization, gauge equation, color/state thresholds and confirmation rules are absent.

## How it works

- Fit an unspecified regression over Length and map price deviations through a sensitivity-controlled heatmap and seasonal gauge.

## Outputs and intended use

- Inspect exceptional deviations, warm/cold transitions and optional regression line to choose further trend or range analysis.

## Parameters and stated settings

- Length, Heat Sensitivity and regression visibility are configurable without numeric defaults or state boundaries.

## Failure modes and caveats

- Analytical: one deviation measure does not separately identify volatility, volume and direction; extreme warm values can persist during trends.

## Missing information and implementation boundary

- Regression family/source, deviation normalization, gauge equation, color/state thresholds and confirmation rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
Heat Sensitivity: Controls the sensitivity of the heat map to deviations from the regression line.
```

### E2: outputs_and_use, readiness

```text
"summer" represents a period of heightened volatility and upward price momentum
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zus134uh_heat_map_seasons](../tv_zus134uh_heat_map_seasons.md)

## Source

https://www.tradingview.com/script/zuS134uh-Heat-Map-Seasons/

Publication ID: zuS134uh. Source SHA-256: 65a7a7ad3772003232cb4334fb55d38c691a578fef0cc6624a337cf9ee125fa1. Raw-description SHA-256: 33ed8a0d4002826f887dea05f5b4049af41ba712198a24fa4f700bee7184b70b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
