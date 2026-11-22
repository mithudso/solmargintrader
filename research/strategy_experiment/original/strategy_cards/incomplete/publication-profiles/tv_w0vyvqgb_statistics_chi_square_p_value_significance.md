---

id: tv_profile_w0vyvqgb

name: "Statistics • Chi Square • P-value • Significance"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This chi-square research tool tests whether grouped prior market conditions and subsequent close direction are associated. It forms a contingency table rather than treating raw RSI or price values directly as categorical observations. The user defines mutually exclusive, exhaustive groups and can compare their outcome counts with unconditional behavior. The source supplies the chi-square calculation and a gamma-CDF p-value implementation, making the testing framework reproducible once groups are specified. Statistical significance remains descriptive evidence, not proof of predictability or a deployable trade edge."

registry_key: null

runner: null

evaluation: null

---

# Statistics • Chi Square • P-value • Significance

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This chi-square research tool tests whether grouped prior market conditions and subsequent close direction are associated. It forms a contingency table rather than treating raw RSI or price values directly as categorical observations. The user defines mutually exclusive, exhaustive groups and can compare their outcome counts with unconditional behavior. The source supplies the chi-square calculation and a gamma-CDF p-value implementation, making the testing framework reproducible once groups are specified. Statistical significance remains descriptive evidence, not proof of predictability or a deployable trade edge.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source supplies substantive parameterized calculations sufficient for reproduction.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Count current close up/down/equal outcomes conditional on selected prior-bar groups.
- Compute expected counts from row total×column total/grand total and sum squared observed-minus-expected differences divided by expected.
- Use (rows−1)(columns−1) degrees of freedom and a table or supplied gamma-CDF code for upper-tail p-value.

## Outputs and intended use

- Contingency counts, population checks, significance/p-value and sample-start marker support hypothesis testing.

## Parameters and stated settings

- Population maximum 4990; at least two and up to eleven condition groups, each with compound conditions.
- Equal outcomes can remain separate or merge with up/down. RSI length and grouping levels are configurable.
- Source uses 0.05 significance and recommends counts at least five; these are guidelines.

## Failure modes and caveats

- Serial dependence and repeated hypothesis searches undermine naive p-values.
- Sparse expected counts require care; the source’s movie example totals are inconsistent.
- Significance is association, not causal explanation or guaranteed future edge.

## Missing information and implementation boundary

- Exact user-selected groups/lookbacks are run inputs; multiple-testing correction and out-of-sample protocol are not supplied.

## Data requirements

Required inputs: ohlcv, user-defined categorical condition groups.

Repository input-class support: unavailable or unresolved. OHLCV supplies example features/outcomes, but a concrete group/population contract must be chosen.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Χ² = Σ ( (Observed Value − Expected Value)² / Expected Value )
```

### E2: mechanism, readiness

```text
(rows − 1) × (columns − 1)
```

### E3: parameters

```text
max 4990
```

### E4: parameters

```text
up to 11 conditions
```

### E5: parameters

```text
At least two conditions
```

### E6: parameters

```text
lower than 0.05
```

### E7: parameters

```text
Each entry must be five or more.
```

### E8: readiness, mechanism

```text
pValue    = 1 - Chisqcdf
```

## Source

https://www.tradingview.com/script/W0vYvqgB-Statistics-Chi-Square-P-value-Significance/

Publication ID: W0vYvqgB. Source SHA-256: 40f31d91d99c8e96a7956b323ac4cc7bd078a9883ecfde39c9460bab47bfcd2d. Raw-description SHA-256: fbc5b2438aaa32c85872d30a5fdccf655351a11ecd51e9cdd931806a73692a48.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
