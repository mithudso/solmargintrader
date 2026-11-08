---

id: tv_profile_b3pcu8qn

name: "CE - 42MACRO Equity Factor Table "

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Combine equity-factor performance and cross-market trend/correlation information into a proposed market-regime and implied-direction dashboard."

registry_key: null

runner: null

evaluation: null

---

# CE - 42MACRO Equity Factor Table

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine equity-factor performance and cross-market trend/correlation information into a proposed market-regime and implied-direction dashboard.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Named inputs and qualitative regime logic do not define reproducible scoring/normalization or an aligned historical dataset.

- Factor/regime weights and classification
- KAMA/correlation/implied-trend equations
- Aligned ETF history/data contract

## How it works

- Track the named equity ETFs across factor/country groups. Calculate their relationship with the chart asset, estimate each trend using a normalized KAMA oscillator, combine correlation with trend and average implied trends. Group factor performance into Goldilocks/Reflation/Inflation/Deflation interpretations.

## Outputs and intended use

- Read risk-on/off, factor strength and possible chart-asset bias. Top-five green and bottom-five red factor cells are the proposed regime pattern; this is a market-implied proxy, not direct measurement of economic growth/inflation.

## Parameters and stated settings

- The description names SPHD,VO,EEM,IWM,QQQ,EWZ,EWU,IWF,SPY,DXJ,MTUM,FXI,SPLV,ACWX,INDA,EZU,QUAL,OEF. Thresholding, normalization/double-normalization, HMA and visual options are mentioned; numerical defaults are absent.

## Failure modes and caveats

- Many correlated ETFs can overrepresent common exposure. Longer-timeframe accuracy and alpha claims are unmeasured; present-day ticker examples do not establish historical holdings or synchronized availability.

## Missing information and implementation boundary

- Factor-to-regime weights, KAMA normalization, correlation window, implied-trend equation, thresholds and companion-model integration are missing.

## Data requirements

Required inputs: aligned histories for listed equity ETFs and chart asset.

Repository input-class support: unavailable or unresolved. The fixed textual ticker list identifies candidate inputs but does not supply their aligned historical series or point-in-time coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
It then Implies a Correlation based on the Trend and the Correlation
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
taking the average of all Implied Trends.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Top 5 Equity Factors
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Bottom 5 Equity Factors
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_b3pcu8qn_ce_42macro_equity_factor_table](../tv_b3pcu8qn_ce_42macro_equity_factor_table.md)

## Source

https://www.tradingview.com/script/b3PcU8qn-CE-42MACRO-Equity-Factor-Table/

Publication ID: b3PcU8qn. Source SHA-256: 127a02cd69635cf37c11bf3a0759a1f9ba0e9e8912c2dfbc9c895966b9fe3ea1. Raw-description SHA-256: eb0838a148295373cba2aa5f80dcf4ec225e1dcd2a67164d11f8b535eff78365.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
