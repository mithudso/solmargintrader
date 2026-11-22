---

id: tv_profile_2vmbqbln

name: "Market EKG"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Market EKG offers a price-only view of changing movement when conventional volume indicators cannot be used. Its visual analogy to a medical trace describes the appearance of the oscillator rather than a measured diagnostic capability. It compares the latest closed candle with nearby historical OHLC averages to make deviations from recent behavior visible, aiming to help assess volatility on indices and other markets without useful volume."

registry_key: null

runner: null

evaluation: null

---

# Market EKG

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market EKG offers a price-only view of changing movement when conventional volume indicators cannot be used. Its visual analogy to a medical trace describes the appearance of the oscillator rather than a measured diagnostic capability. It compares the latest closed candle with nearby historical OHLC averages to make deviations from recent behavior visible, aiming to help assess volatility on indices and other markets without useful volume.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** OHLC component aggregation and oscillator normalization are ambiguous.

- OHLC component aggregation and oscillator normalization are ambiguous.

## How it works

- Take the previous period’s OHLC and compare it with averages of the preceding three periods, then plot their differences.
- The summary describes four OHLC inputs combined into an EKG-like oscillator; the step list describes the latest confirmation relative to the local trend.

## Outputs and intended use

- Use the oscillating deviations as a relative price-volatility display rather than as a supplied directional entry rule.

## Parameters and stated settings

- The description identifies a previous candle and three-period OHLC averages; exact toggles, averaging equations and defaults are not specified.

## Failure modes and caveats

- Analytical: this is a bespoke relative-movement measure; the EKG shape does not establish comparability across assets or timeframes.

## Missing information and implementation boundary

- It is unclear exactly how each OHLC component is aggregated, normalized or scaled; a closing reference to an RSI script is inconsistent with the stated mechanism.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart price/volume data supports the described calculation class; matching Pine implementation remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
Taking Previous 3 Periods OHLC Avgs
```

### E2: mechanism, outputs_and_use, readiness

```text
The difference is then placed into an oscillator that when all four inputs are scrolled back on, shows an EKG appearing oscillator / volatility measure
```

### E3: missing_information, readiness

```text
This RSI Script is intended for public use
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_2vmbqbln_market_ekg](../tv_2vmbqbln_market_ekg.md)

## Source

https://www.tradingview.com/script/2VmbQBLn-Market-EKG/

Publication ID: 2VmbQBLn. Source SHA-256: 07df41ae4ce81592f69a297c0f0ee3bb07f3685aff94a7f88f3391212190774d. Raw-description SHA-256: 2051375a240ba6731cdcb50fc2dab40922c3572b1d17eaad23154a6a196a3d84.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
