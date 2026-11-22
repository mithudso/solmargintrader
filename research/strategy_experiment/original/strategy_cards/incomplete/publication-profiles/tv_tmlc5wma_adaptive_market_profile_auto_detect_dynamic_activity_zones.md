---

id: tv_profile_tmlc5wma

name: "Adaptive Market Profile – Auto Detect & Dynamic Activity Zones"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Choose an adaptive trend channel and map the most active price regions in coordinates parallel to that channel."

registry_key: null

runner: null

evaluation: null

---

# Adaptive Market Profile – Auto Detect & Dynamic Activity Zones

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Choose an adaptive trend channel and map the most active price regions in coordinates parallel to that channel.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Search range/objective, channel width, touch counting, volume allocation and active-level ranking/ties are missing.

- Search range/objective, channel width, touch counting, volume allocation and active-level ranking/ties are missing.

## How it works

- Scan candidate regression lengths and select the strongest Pearson-R fit, or use a manual period. Divide the channel range into zones and tally volume or price touches, then highlight active parallel levels.

## Outputs and intended use

- Use the combined channel and activity profile to inspect trend-relative concentrations and potential reaction areas. The calculation does not identify actual resting liquidity despite the descriptive liquidity language.

## Parameters and stated settings

- Auto period detection is the default. Manual override, profile section count, activity basis and linear/logarithmic mode are configurable; candidate lengths and numerical defaults are not listed.

## Failure modes and caveats

- Choosing the strongest in-sample correlation does not establish statistical significance after scanning many windows. Adaptive channel changes can move apparent activity zones.

## Missing information and implementation boundary

- Search range/objective, channel width, touch counting, volume allocation and active-level ranking/ties are missing.

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
calculation is based on maximizing the statistical significance of the trend using Pearson’s R coefficient
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
distribution of volume or price touches inside the trend channel
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
By default, the script automatically detects the optimal channel period
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_profile](../tv_method_market_profile.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_tmlc5wma_adaptive_market_profile_auto_detect_dynamic_activity_zones](../tv_tmlc5wma_adaptive_market_profile_auto_detect_dynamic_activity_zones.md)

## Source

https://www.tradingview.com/script/TMLC5Wma-Adaptive-Market-Profile-Auto-Detect-Dynamic-Activity-Zones/

Publication ID: TMLC5Wma. Source SHA-256: 3964d7a62cf67073e0fb9cc1a0eae1e224c484bef95e34601054a3ff66649228. Raw-description SHA-256: 3c5b362e71ebdb8e1bd8af6beaa34c5bfe435f28758fdf7bfc1f4c9056f13997.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
