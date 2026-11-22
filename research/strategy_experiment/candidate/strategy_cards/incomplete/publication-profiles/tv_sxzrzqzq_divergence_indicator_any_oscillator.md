---

id: tv_profile_sxzrzqzq

name: "Divergence Indicator (any oscillator)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Divergence Indicator (any oscillator) adapts a platform divergence study to accept another indicator plot and optionally draw its results on price. The publication primarily documents chart setup rather than the divergence algorithm. It lets users keep oscillator-space and price-space annotations together by loading two instances with the same source. This flexibility does not establish that every oscillator has comparable divergence meaning or that a detected mismatch implies a reversal."

registry_key: null

runner: null

evaluation: null

---

# Divergence Indicator (any oscillator)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Divergence Indicator (any oscillator) adapts a platform divergence study to accept another indicator plot and optionally draw its results on price. The publication primarily documents chart setup rather than the divergence algorithm. It lets users keep oscillator-space and price-space annotations together by loading two instances with the same source. This flexibility does not establish that every oscillator has comparable divergence meaning or that a detected mismatch implies a reversal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation needs the listed definitions.

- The divergence algorithm and external oscillator-series contract are undefined.

## How it works

- Use a selected oscillator output as the study source.
- Apply the adapted divergence calculation and choose whether annotations belong on the oscillator or price chart.

## Outputs and intended use

- Attach the study to RSI, Klinger, TSI, CMF or another plotted series and verify the selected plot.
- Add another instance on price with the price-plot option enabled to view corresponding annotations in both locations.

## Parameters and stated settings

- The source names built-in Divergence indicator Version 10 as its starting point; numeric pivot settings and defaults are not listed.

## Failure modes and caveats

- Different oscillator scaling, smoothing and confirmation delays affect interpretation.
- No source-disclosed pivot timing prevents a guarantee about when annotations become known.

## Missing information and implementation boundary

- Regular/hidden divergence inequalities, pivot lengths, pairing rules, allowable separation and confirmation timing are absent.

## Data requirements

Required inputs: ohlcv, selected oscillator series.

Repository input-class support: unavailable or unresolved. The described external or detailed input contract is not available from ordinary chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, parameters

```text
modification of the TV builtin "Divergence indicator" (Version 10)
```

### E2: required_data, mechanism

```text
make sure the source is set to the right plot from your oscillator.
```

### E3: outputs_and_use

```text
plot on price (rather than on indicator)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_sxzrzqzq_divergence_indicator_any_oscillator](../tv_sxzrzqzq_divergence_indicator_any_oscillator.md)

## Source

https://www.tradingview.com/script/sxZRzQzQ-Divergence-Indicator-any-oscillator/

Publication ID: sxZRzQzQ. Source SHA-256: 7c77347fed817dc2a91550ef59bbccef54772a1fd169287904743a4d7a934087. Raw-description SHA-256: de86844e053039286e7f6d7ad78692cb10e11cc8898dcb1ee75bcdeb3ca74db4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
