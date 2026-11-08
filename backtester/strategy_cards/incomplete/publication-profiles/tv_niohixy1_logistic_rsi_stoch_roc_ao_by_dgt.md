---

id: tv_profile_niohixy1

name: "Logistic RSI, STOCH, ROC, AO, ... by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Explore repeated logistic-map transformations of familiar technical indicators and summarize the dispersion of the resulting iterations."

registry_key: null

runner: null

evaluation: null

---

# Logistic RSI, STOCH, ROC, AO, ... by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Explore repeated logistic-map transformations of familiar technical indicators and summarize the dispersion of the resulting iterations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Seed selection, indicator normalization, recurrence implementation, dispersion definition and directional interpretation are missing.

- Seed selection, indicator normalization, recurrence implementation, dispersion definition and directional interpretation are missing.

## How it works

- Use AO, ROC, RSI, stochastic or a custom interpretation to supply the logistic-map control variable. Repeatedly apply Xnext=r*X*(1-X), retain iterations in arrays and plot them except the first. Also plot standard deviation across iteration outputs.

## Outputs and intended use

- Choose circles or lines for the iteration display and optionally show only the dispersion line. Color positive/negative values differently as the author's bull/bear visualization.

## Parameters and stated settings

- The author states the assigned control parameter lies strictly between zero and one. Actual mapping from each indicator, iteration count and defaults are omitted.

## Failure modes and caveats

- The stated parameter bound and a positive logistic seed would normally preserve nonnegative iterates, yet the prose discusses negative values. The input normalization/sign treatment therefore needs clarification.

## Missing information and implementation boundary

- Seed selection, indicator normalization, recurrence implementation, dispersion definition and directional interpretation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed feature uses ordinary price/volume history; this is input-class support rather than verified implementation or data-cache parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Here is the Logistic Map Equation : Xn+1 = r * Xn * (1 - Xn)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
0 < r < 1
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Values above and below zero level (0) are coloured differently
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Finally Standard Deviation of Array's Elements is ploted as line.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_niohixy1_logistic_rsi_stoch_roc_ao_by_dgt](../tv_niohixy1_logistic_rsi_stoch_roc_ao_by_dgt.md)

## Source

https://www.tradingview.com/script/NioHIxY1-Logistic-RSI-STOCH-ROC-AO-by-DGT/

Publication ID: NioHIxY1. Source SHA-256: bff62210464a00a5f5f74c1f574d63213548b11f5e20ec9ee0e26a0a62bb0584. Raw-description SHA-256: c645cf086bd442dec2e32a8352d00574ec3961e1ecdf24f3e6cf67111277877a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
