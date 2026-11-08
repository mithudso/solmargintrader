---

id: tv_profile_snufopt6

name: "Modified Mannarino Market Risk Indicator MMMRI MMRI"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Modified Mannarino Market Risk Indicator displays a dollar-strength/interest-rate risk heuristic and a debt-to-GDP-adjusted variant. It aims to provide broad market-risk context, with customizable source symbols and scale factors. The score is a formula-based research proxy rather than a calibrated probability of loss or a complete trading strategy, as the source itself emphasizes."

registry_key: null

runner: null

evaluation: null

---

# Modified Mannarino Market Risk Indicator MMMRI MMRI

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Modified Mannarino Market Risk Indicator displays a dollar-strength/interest-rate risk heuristic and a debt-to-GDP-adjusted variant. It aims to provide broad market-risk context, with customizable source symbols and scale factors. The score is a formula-based research proxy rather than a calibrated probability of loss or a complete trading strategy, as the source itself emphasizes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** MMRI/MMMRI arithmetic is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Compute MMRI as dollar strength times dollar interest rate divided by the stated constant; multiply by debt/GDP for MMMRI.
- Plot the selected version, color risk bands and optionally show both scores, dollar strength and yield in a table.
- MMRI=(USD_Strength*USD_Interest_Rate)/1.61;MMMRI=(Debt/GDP)*MMRI. Caller must state yield/index/debt/GDP units;do not silently interchange percentage/fraction. Feeds and heuristic thresholds remain limitations.

## Outputs and intended use

- Read the chosen risk band and compare original/modified versions for macro context.
- Usable scope: MMRI/MMMRI arithmetic. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Denominator is 1.61; MMMRI is default. Bands are 0–50 slight, 50–100 low, 100–200 moderate, 200–300 high and 300+ extreme. Symbols/denominators/ratio factors are adjustable.

## Failure modes and caveats

- Analytical: debt/GDP unit scaling and revised macro data materially affect scores; thresholds are heuristic and not validated risk estimates.

## Missing information and implementation boundary

- Exact source tickers, debt/GDP percent-versus-ratio units, release/revision alignment and default configurable factors are not disclosed.

## Data requirements

Required inputs: dollar-strength series, USD interest-rate series, debt/GDP series.

Repository input-class support: unavailable or unresolved. External macro series and their units/releases are required; computation is explicit but the data contract remains incomplete.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
MMRI = (USD Strength * USD Interest Rate) / 1.61

MMMRI = (Debt / GDP) * (USD Strength * USD Interest Rate) / 1.61
```

### E2: parameters, readiness

```text
0-50 slight risk, 50-100 low risk, 100-200 moderate risk, 200-300 high risk, 300+ extreme risk.
```

### E3: parameters, readiness

```text
default choice has been set to MMMRI
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
MMRI = (USD Strength * USD Interest Rate) / 1.61
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
MMMRI = (Debt / GDP) * (USD Strength * USD Interest Rate) / 1.61
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_snufopt6_modified_mannarino_market_risk_indicator_mmmri_mmri](../../../strategy_research/tv_snufopt6_modified_mannarino_market_risk_indicator_mmmri_mmri.md)

## Source

https://www.tradingview.com/script/snuFoPT6-Modified-Mannarino-Market-Risk-Indicator-MMMRI-MMRI/

Publication ID: snuFoPT6. Source SHA-256: dfa3ff23c882b5bca2d015150d65cffd9bb7015dbb4443329eb6f202ab80ede5. Raw-description SHA-256: 807cfaf2013bc34b1ee73e1e85c86f86c9a41a76c5d45b760cbad1c86dd91d1d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
