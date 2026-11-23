---

id: tv_profile_195p3ylk

name: "Commitment of Traders: Legacy Metrics"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Commitment of Traders: Legacy Metrics displays selected columns from legacy COT reports for futures-related markets. It exposes positioning, trader counts and concentration information as descriptive market context, rather than inferring a buy/sell signal from commercial or noncommercial activity. The chart symbol can guide report selection, but users can override that mapping with an unrelated CFTC code. Direction and report type matter because not every metric supports the same subdivisions."

registry_key: null

runner: null

evaluation: null

---

# Commitment of Traders: Legacy Metrics

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Commitment of Traders: Legacy Metrics displays selected columns from legacy COT reports for futures-related markets. It exposes positioning, trader counts and concentration information as descriptive market context, rather than inferring a buy/sell signal from commercial or noncommercial activity. The chart symbol can guide report selection, but users can override that mapping with an unrelated CFTC code. Direction and report type matter because not every metric supports the same subdivisions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The principal output is a selected published Legacy COT metric using explicit report/code/direction/type choices; release lag and data access affect use but do not hide an indicator equation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Retrieve legacy-report data for a mapped or explicit CFTC market code and select a metric/direction combination.
- Expose open interest, reportable/nonreportable positions, trader categories and gross/net concentration; nonreportable positions are derived from total minus reportable positions.
- Select all, old or other crop-year aggregation where supported, plus futures/options coverage.

## Outputs and intended use

- Inspect weekly positioning and concentration context for the selected market; unsupported mappings produce an error rather than invented values.

## Parameters and stated settings

- Automatic selection tries root, base currency and quote currency modes; a nonempty CFTC code overrides selection.
- Type options are All, Old and Other; concentration metrics concern the largest four or eight traders. The sample explicit wheat code is 001602.

## Failure modes and caveats

- Analytical: reported positions are delayed descriptive aggregates, not contemporaneous orders or pure speculative conviction. Crop-year distinctions do not apply to all commodities.

## Missing information and implementation boundary

- Exact feed release timestamps, historical revision handling, display defaults and any trading interpretation are not supplied.

## Data requirements

Required inputs: CFTC legacy COT report histories, symbol-to-CFTC market mapping.

Repository input-class support: unavailable or unresolved. Weekly COT reports and market-code mapping are external inputs, absent from ordinary chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
It is weekly data
```

### E2: parameters, readiness

```text
Concentration Gross/Net LT 4/8 TDR
```

### E3: parameters, readiness

```text
Possible values are: All, Old, Other.
```

### E4: parameters, readiness

```text
001602 for wheat futures.
```

### E5: outputs_and_use, readiness

```text
If no COT data can be found, a runtime error is generated.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_195p3ylk_commitment_of_traders_legacy_metrics](../tv_195p3ylk_commitment_of_traders_legacy_metrics.md)

## Source

https://www.tradingview.com/script/195p3YlK-Commitment-of-Traders-Legacy-Metrics/

Publication ID: 195p3YlK. Source SHA-256: 0e538f571765b7b57c7d574487599a686c5874059eecf481bdeef868b5d81f30. Raw-description SHA-256: e733cb1c56a0f9b4ed97faa6b8a88cabf8253c3b5f49a3d4633c55464d1cbb95.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
