---

id: tv_profile_vdzfb2wa

name: "Quality Screen"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Screen company quality through a grouped view of solvency, liquidity and profitability statistics with author-proposed qualitative bands."

registry_key: null

runner: null

evaluation: null

---

# Quality Screen

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Screen company quality through a grouped view of solvency, liquidity and profitability statistics with author-proposed qualitative bands.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The identifiers and many numerical bands are disclosed, but interval gaps, overlapping endpoints and the equity-return comparator prevent a complete deterministic quality-label dashboard without adding rules.

- Resolve unspecified intervals and endpoint/label precedence.
- Define the intended Healthy:10% RETURN_ON_EQUITY comparison and reporting-period contract.

## How it works

- Display leverage ratios, Altman/Springate distress scores, liquidity ratios, Sloan accrual quality and returns on assets/equity/invested capital. Classify individual values using the listed good/healthy/risk ranges.

## Outputs and intended use

- Use the labels to compare dimensions of financial condition. The source does not define a composite quality score or a buy/sell decision.

## Parameters and stated settings

- DEBT_TO_EQUITY: very good 0–1, good 1–2, high risk >2. DEBT_TO_ASSET and LONG_TERM_DEBT_TO_ASSETS: very good <0.4, good 0.4–0.6, high risk >0.6.
- ALTMAN_Z_SCORE: very good >3, good 1.8–3, high risk <1.8. SPRINGATE_SCORE: high risk <0.862; other labels are not supplied.
- CURRENT_RATIO: very good 1.2–2, good 2+ (too high/inefficient), high risk <1. QUICK_RATIO: very good 1–2, good 2+ (too high/inefficient), high risk <0.9.
- SLOAN_RATIO: very good -10% to +10%; good -25% to -10% or +10% to +25%; high risk <-25% or >+25%.
- RETURN_ON_ASSETS: healthy >5%, great >20%. RETURN_ON_EQUITY: Healthy:10%, great >40%. RETURN_ON_INVESTED_CAPITAL: healthy >2%, great >10%. These are stated labels, not resolved precedence rules.

## Failure modes and caveats

- The bands are author heuristics, not universally valid sector-adjusted thresholds. Several boundaries or intervals are unspecified, and financial reports can be stale or revised.

## Missing information and implementation boundary

- The source explicitly names its financial identifiers. Reporting periods, negative-equity treatment and complete boundary/gap handling are not disclosed; for example CURRENT_RATIO between 1 and 1.2 and exact overlapping endpoints lack a complete rule.
- RETURN_ON_EQUITY states Healthy:10% without defining whether this means equality or a threshold. No composite quality score is proposed.

## Data requirements

Required inputs: company financial-statement ratios and distress scores.

Repository input-class support: unavailable or unresolved. Financial statements and derived ratios are external data; the source lists fields and bands but does not supply their histories.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
DEBT_TO_EQUITY
[list]
[*]Very Good : 0 - 1
[*]Good : 1 - 2
[*]High risk : > 2
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
ALTMAN_Z_SCORE
[list]
[*]Very good: > 3
[*]Good : 1.8 - 3
[*]High Risk : < 1.8
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
RETURN_ON_INVESTED_CAPITAL
[list]
[*]Healthy : > 2%
[*]Great : > 10%
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_vdzfb2wa_quality_screen](../tv_vdzfb2wa_quality_screen.md)

## Source

https://www.tradingview.com/script/vdzfb2WA-Quality-Screen/

Publication ID: vdzfb2WA. Source SHA-256: 4ef153c72bb573adfc65b1eea37855c379cf94317993b91d0df2086fe4b375fc. Raw-description SHA-256: 500357f7f85284a956b9584a67e2b93b1ff220c2b0f27794c3f2c428cd8192c2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
