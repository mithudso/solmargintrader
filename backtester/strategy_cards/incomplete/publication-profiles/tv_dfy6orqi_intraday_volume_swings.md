---

id: tv_profile_dfy6orqi

name: "Intraday Volume Swings"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Intraday Volume Swings records price extremes reached during stretches of rising volume, then carries the day’s final selected high and low into the following session. It aims to distinguish participation-supported swings from arbitrary daily extremes, providing possible retracement or support/resistance references. Current-day candidates can also be displayed but may later be replaced by more extreme qualifying swings."

registry_key: null

runner: null

evaluation: null

---

# Intraday Volume Swings

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Intraday Volume Swings records price extremes reached during stretches of rising volume, then carries the day’s final selected high and low into the following session. It aims to distinguish participation-supported swings from arbitrary daily extremes, providing possible retracement or support/resistance references. Current-day candidates can also be displayed but may later be replaced by more extreme qualifying swings.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Volume/price runs and next-day extrema is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Define qualifying runs with increasing volume and higher highs or lower lows over at least three bars.
- Keep the highest high-swing and lowest low-swing during the day and plot those final references on the next day.
- Detect at least3 bars with strictly increasing volume and strictly higher highs or lower lows. Within caller day keep highest qualifying high-swing/lowest qualifying low-swing; carry completed values to following day. Ties terminate strict runs under explicit study convention; live candidates may change.

## Outputs and intended use

- Inspect prior-day swing references and optional developing intraday levels for areas of interest, without a specified entry trigger.
- Usable scope: Volume/price runs and next-day extrema. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Minimum run length is three bars; current-day display is optional. Other defaults and session settings are not disclosed.

## Failure modes and caveats

- Analytical: developing levels are provisional and price can cross a prior participation level without reversing.

## Missing information and implementation boundary

- Exact consecutive comparison rules, day/session boundary, equal-value handling and swing finalization are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
minimum of three bars.
```

### E2: mechanism, outputs_and_use, readiness

```text
plotted over the following day
```

### E3: risks, readiness

```text
may or may not be the final swings for the day
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
Volume swings are defined as increasing volume and higher highs/lower lows over a minimum of three bars.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
This script tracks volume swings over an intraday chart and stores the final lowest low swing / highest high swing over the course of the day. The final high swing and low swing are then plotted over the following day as possible retracement / support & resistance levels.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dfy6orqi_intraday_volume_swings](../../../strategy_research/tv_dfy6orqi_intraday_volume_swings.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/dFY6oRQi-Intraday-Volume-Swings/

Publication ID: dFY6oRQi. Source SHA-256: 7bd98d27d244b2923a67ec6078ae6c20c62470354059c98ab05d75aecbc5e0c4. Raw-description SHA-256: 2b6d19931d4590414ffb3f4ad05290815efe26f319d07ad31be1ad3db37dc628.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
