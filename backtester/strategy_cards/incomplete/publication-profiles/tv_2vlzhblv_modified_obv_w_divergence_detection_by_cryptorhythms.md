---

id: tv_profile_2vlzhblv

name: "Modified OBV w/ Divergence Detection by Cryptorhythms"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This publication adapts Apirine’s modified on-balance-volume study to help traders compare price direction with volume-derived momentum. Its main addition to classic OBV is smoothing plus a signal line, intended to make changes in the volume trend easier to interpret. The implementation also supplies visual trade-state coloring and divergence marks so the user can inspect possible disagreement between price and the volume measure."

registry_key: null

runner: null

evaluation: null

---

# Modified OBV w/ Divergence Detection by Cryptorhythms

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This publication adapts Apirine’s modified on-balance-volume study to help traders compare price direction with volume-derived momentum. Its main addition to classic OBV is smoothing plus a signal line, intended to make changes in the volume trend easier to interpret. The implementation also supplies visual trade-state coloring and divergence marks so the user can inspect possible disagreement between price and the volume measure.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The modified OBV core and smoothing/signal construction are not defined.

- The modified OBV core and smoothing/signal construction are not defined.

## How it works

- Start from classic on-balance volume, smooth its calculation, and add a signal line that the author associates with entry and exit interpretation.
- Expose alternative moving-average selections and add divergence detection derived from a Ricardo Santos script.

## Outputs and intended use

- Read the smoothed volume measure and signal line together; use bar colors for a quick view of the indicated trade state and divergence plots for contextual review.

## Parameters and stated settings

- Moving-average selection is configurable; exact choices, lengths, divergence parameters and defaults are not disclosed in the description.

## Failure modes and caveats

- Analytical: divergence can persist during a trend; smoothing introduces response delay and the source does not establish signal profitability.

## Missing information and implementation boundary

- The precise OBV modification, smoothing equations, divergence confirmation timing and complete trading rules require code or further documentation.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical price and volume support the OBV calculation class; source-level equivalence is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, outputs_and_use, readiness

```text
Apirine then smooths the calculation and adds a signal line to help denote entry and exit points.
```

### E2: mechanism, parameters, outputs_and_use, readiness

```text
💠MA selection to allow you to experiment with alternate settings
💠Bar coloration based on trade state for easy visual at a glance chart checking
💠Divergence Detection and plotting thanks for Ricardo Santos' script
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_2vlzhblv_modified_obv_w_divergence_detection_by_cryptorhythms](../tv_2vlzhblv_modified_obv_w_divergence_detection_by_cryptorhythms.md)

## Source

https://www.tradingview.com/script/2VlZhblV-Modified-OBV-w-Divergence-Detection-by-Cryptorhythms/

Publication ID: 2VlZhblV. Source SHA-256: d5966cd50c41edd1d6441b4e37c654963ac357f2fce877d47818db870e083087. Raw-description SHA-256: 710a8a3fe658b660de5b34c56be5a0c6d276e24c8995471e700700eb533bdb5b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
