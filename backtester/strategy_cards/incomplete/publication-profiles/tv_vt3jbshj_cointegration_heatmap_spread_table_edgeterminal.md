---

id: tv_profile_vt3jbshj

name: "Cointegration Heatmap & Spread Table [EdgeTerminal]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare pairwise regression residuals and standardized spreads across a watchlist as a proposed mean-reversion research screen."

registry_key: null

runner: null

evaluation: null

---

# Cointegration Heatmap & Spread Table [EdgeTerminal]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare pairwise regression residuals and standardized spreads across a watchlist as a proposed mean-reversion research screen.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The residual formula is given, but score scaling and the selected aligned data contract are unresolved; genuine cointegration testing is not defined.

- Price/return and alignment contract
- Inverse-dispersion-to-percent mapping
- Selected asset histories and hedge sizing

## How it works

- Regress Y on X, calculate Y-(alpha+beta*X), estimate residual standard deviation and label its inverse a cointegration score. Show spread mean/Z-score and long/short/neutral suggestions.

## Outputs and intended use

- The author proposes entry beyond plus/minus two Z and exit near zero. Pair ordering matters: its example regresses the second asset on the first and a negative Z suggests long second/short first.

## Parameters and stated settings

- Symbols are comma-separated, return sampling is weekly or monthly and Max periods limits history. Residual dispersion defaults one hundred samples; heuristic score cutoffs are twenty-five/forty percent.

## Failure modes and caveats

- Inverse residual standard deviation is not a stationarity test or proof of cointegration. It is scale dependent and cannot directly be read as a percentage probability; the text's always-revert statement conflicts with its later breakdown warning.

## Missing information and implementation boundary

- Price-versus-return regression, percent-score mapping, hedge sizing, aligned spread-ticker adjustments and actual stationarity checks are missing.

## Data requirements

Required inputs: aligned selected-asset price or return histories, corporate-action-adjusted spread tickers.

Repository input-class support: unavailable or unresolved. The chosen universe and aligned adjusted histories are not supplied; a list of possible markets is not a point-in-time dataset.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Spreadt​=Yt​−(α+βXt​)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default: 100 samples
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
S=1/Standard Deviation of Residuals
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
z-score is either over +2 or below -2
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Any assets with a cointegration value of 25%
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
score of over 40%
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_vt3jbshj_cointegration_heatmap_spread_table_edgeterminal](../tv_vt3jbshj_cointegration_heatmap_spread_table_edgeterminal.md)

## Source

https://www.tradingview.com/script/Vt3jBShj-Cointegration-Heatmap-Spread-Table-EdgeTerminal/

Publication ID: Vt3jBShj. Source SHA-256: e00d3de8e39f954bdf203ea8d464ce0667967e5001744de4528a49f10426077b. Raw-description SHA-256: d35f6216ffbd0557dac7bb527de945ae9eeab67c4efc402c727a629fdf5ea911.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
