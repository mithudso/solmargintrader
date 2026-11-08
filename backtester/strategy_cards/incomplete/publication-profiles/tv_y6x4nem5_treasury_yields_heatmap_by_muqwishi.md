---

id: tv_profile_y6x4nem5

name: "Treasury Yields Heatmap [By MUQWISHI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Treasury Yields Heatmap displays yield observations by date and classifies the cross-maturity curve as normal, flat or inverted. It is a bond-market monitoring view, not a forecast that an inversion necessarily predicts a recession or trade outcome. Country and interval selection determine the external series being compared, and the final-column state is derived from a coefficient threshold scheme."

registry_key: null

runner: null

evaluation: null

---

# Treasury Yields Heatmap [By MUQWISHI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Treasury Yields Heatmap displays yield observations by date and classifies the cross-maturity curve as normal, flat or inverted. It is a bond-market monitoring view, not a forecast that an inversion necessarily predicts a recession or trade outcome. Country and interval selection determine the external series being compared, and the final-column state is derived from a coefficient threshold scheme.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Supplied yield-by-date table is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Retrieve selected country yield data across maturities and dates, then calculate the source-described Pearson coefficient for curve shape.
- Color a table of yield values and assign a curve-status category from the coefficient.
- Place supplied country/maturity/date yield observations into corresponding table cells; preserve missing observations as missing and use caller styling. Final-column curve coefficient and external feed access are excluded.

## Outputs and intended use

- Track historical yield changes and broad curve orientation through the heatmap and final status column.
- Usable scope: Supplied yield-by-date table. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Normal R≥0.7; slight normal 0.35≤R<0.7; flat -0.35<R<0.35; slight inverted -0.7<R≤-0.35; inverted R≤-0.7.
- Country, timeframe and fetch-by-start-date or backward-period count are configurable.

## Failure modes and caveats

- Analytical: a correlation-style coefficient compresses curve shape and can hide humps or local inversions; source calls it a linear-regression coefficient ambiguously.

## Missing information and implementation boundary

- Maturity set, exact coefficient inputs, missing-yield handling, historical feed revisions and default country are absent.

## Data requirements

Required inputs: country treasury-yield term-structure histories.

Repository input-class support: unavailable or unresolved. Requires external yields across maturities; chart OHLCV does not supply the term structure.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
R ≥ 0.7 → Normal
[*]0.7 > R ≥ 0.35  → Slight Normal
[*]0.35 > R > -0.35  → Flat
[*]-0.35 ≥ R > -0.7  → Slight Inverted
[*]-0.7 ≥ R → Inverted
```

### E2: mechanism, parameters, outputs_and_use, readiness

```text
The “Treasury Yields Heatmap” generates a dynamic heat map table, showing treasury yield bond values corresponding with dates. In the last column, it presents the status of the yield curve, discerning whether it’s in a normal, flat, or inverted configuration, which determined by using Pearson's linear regression coefficient. This tool is built to offer traders essential insights for effectively tracking bond values and monitoring yield curve status, featuring the flexibility to input a starting period, timeframe, and select from a range of major countries' bond data.
```

### E3: mechanism, parameters, outputs_and_use, readiness

```text
The “Treasury Yields Heatmap” generates a dynamic heat map table, showing treasury yield bond values corresponding with dates. In the last column, it presents the status of the yield curve, discerning whether it’s in a normal, flat, or inverted configuration, which determined by using Pearson's linear regression coefficient. This tool is built to offer traders essential insights for effectively tracking bond values and monitoring yield curve status, featuring the flexibility to input a starting period, timeframe, and select from a range of major countries' bond data.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_y6x4nem5_treasury_yields_heatmap_by_muqwishi](../tv_y6x4nem5_treasury_yields_heatmap_by_muqwishi.md)

## Source

https://www.tradingview.com/script/Y6x4NEm5-Treasury-Yields-Heatmap-By-MUQWISHI/

Publication ID: Y6x4NEm5. Source SHA-256: a61f875e584d2b9652a5f14af57e639677bea5c49916d86e9ad5cef4829a5141. Raw-description SHA-256: bdccadbdabaeaecfe8bed53b66421b230b5dac20f63bef3171f28d1d498e24e6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
