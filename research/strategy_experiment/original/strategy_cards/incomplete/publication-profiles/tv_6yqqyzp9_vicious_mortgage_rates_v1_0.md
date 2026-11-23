---

id: tv_profile_6yqqyzp9

name: "Vicious Mortgage Rates V1.0"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Vicious Mortgage Rates displays lender mortgage-rate series as a lower-pane financial reference. It is intended for comparison with a chart such as the US ten-year Treasury yield, helping a reader inspect mortgage borrowing costs alongside broader rates. The source describes a broad catalogue of purchase and refinance products, each separated into interest-rate and APR series. That distinction supports comparison of quoted rate and broader borrowing-cost measures, but the publication does not describe a trading signal. It explicitly says some catalogue entries are not operational and lists trend studies, oscillators and alerts as future work."

registry_key: null

runner: null

evaluation: null

---

# Vicious Mortgage Rates V1.0

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Vicious Mortgage Rates displays lender mortgage-rate series as a lower-pane financial reference. It is intended for comparison with a chart such as the US ten-year Treasury yield, helping a reader inspect mortgage borrowing costs alongside broader rates. The source describes a broad catalogue of purchase and refinance products, each separated into interest-rate and APR series. That distinction supports comparison of quoted rate and broader borrowing-cost measures, but the publication does not describe a trading signal. It explicitly says some catalogue entries are not operational and lists trend studies, oscillators and alerts as future work.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable as a raw mortgage-rate reporting specification: the source identifies the Wells Fargo catalogue and product codes. Feed availability and unfinished predictive additions do not block the stated retrieval/display output.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Retrieve mortgage-rate data attributed to Wells Fargo through a Quandl link.
- Select among catalogue codes for purchase/refinance, conforming/government/larger-eligible/jumbo products and rate/APR variants.

## Outputs and intended use

- Lower-pane rate plots support discretionary comparison with US10Y or another main-chart series.
- The description lists VIX as planned addition rather than an established implemented input.

## Parameters and stated settings

- Catalogue includes fixed-rate and ARM products, with product-specific codes; no default series or chart settings are specified.

## Failure modes and caveats

- The historical description’s real-time language does not establish present feed availability or update frequency.
- APR and interest rate represent different quantities and should not be treated interchangeably.
- Some series were explicitly not running at publication.

## Missing information and implementation boundary

- Implemented subset, update cadence, units, missing-value treatment and predictive/trading rules are absent.
- Trending, oscillators and alerts are advertised as future features, not described calculations.

## Data requirements

Required inputs: Wells Fargo mortgage interest-rate and APR series via Quandl, comparison yield series when used.

Repository input-class support: unavailable or unresolved. These external mortgage datasets are not available from ordinary price candles, and the source itself flags incomplete series coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, required_data, readiness

```text
real time mortgage rates from Wells Fargo using the QUANDL data link.
```

### E2: outputs_and_use

```text
Use this lower indicator with US10Y or others on the top.
```

### E3: risks

```text
Not all indicators are up and running yet
```

### E4: missing_information

```text
Feature to be Added:
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_6yqqyzp9_vicious_mortgage_rates_v1_0](../tv_6yqqyzp9_vicious_mortgage_rates_v1_0.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/6yQQYzp9-Vicious-Mortgage-Rates-V1-0/

Publication ID: 6yQQYzp9. Source SHA-256: e61063ece339ecded04b05321d578a1b937af193d8c60f398bc2a248bfbea20b. Raw-description SHA-256: d6e9b3aa60a41b0ba087f74e29803b69c7a0c50e6412cf66420f6ae8895d1109.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
