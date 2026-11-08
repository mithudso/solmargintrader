---

id: tv_profile_icrp4b2u

name: "Stochastic Momentum Index (SMI) of Money Flow Index (MFI)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Measure momentum in a price-and-volume pressure proxy by feeding Money Flow Index into a Stochastic Momentum Index calculation."

registry_key: null

runner: null

evaluation: null

---

# Stochastic Momentum Index (SMI) of Money Flow Index (MFI)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Measure momentum in a price-and-volume pressure proxy by feeding Money Flow Index into a Stochastic Momentum Index calculation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Exact nested SMI formula, MFI source, signal smoothing, divergence detection and bar-close confirmation are missing.

- Exact nested SMI formula, MFI source, signal smoothing, divergence detection and bar-close confirmation are missing.

## How it works

- Calculate MFI from price/volume, then apply an SMI-style transformation to that series rather than raw price. The author proposes adjusting periods for the intended use and comparing with ordinary price SMI.

## Outputs and intended use

- The stated buy cue is signal-line crossing above minus forty and sell cue crossing below plus forty. Price/oscillator divergences are suggested as possible weakening or strengthening momentum.

## Parameters and stated settings

- Thresholds are -40 and +40. MFI/SMI periods, smoothing and signal-line defaults are not disclosed.

## Failure modes and caveats

- MFI represents a constructed pressure proxy, not actual order flow. Divergence can persist and thresholds can whipsaw; no stop, sizing or timing plan accompanies the cues.

## Missing information and implementation boundary

- Exact nested SMI formula, MFI source, signal smoothing, divergence detection and bar-close confirmation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class. Code parity, complete history and forward performance remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
use the MFI as an input to the SMI, rather than just using price.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
When the line crosses above -40, it is considered a buy signal, while the crossing below +40 is considered a sell signal.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_icrp4b2u_stochastic_momentum_index_smi_of_money_flow_index_mfi](../tv_icrp4b2u_stochastic_momentum_index_smi_of_money_flow_index_mfi.md)

## Source

https://www.tradingview.com/script/iCRp4B2U-Stochastic-Momentum-Index-SMI-of-Money-Flow-Index-MFI/

Publication ID: iCRp4B2U. Source SHA-256: f2a778a023a8dd8591f89ccc91f1e45a7a5c62167fa66d83fda1eb7b6b0a545d. Raw-description SHA-256: f298625fcdaaa47745bb5da98c830d984ccd9679b9ec77679861f4209d8f3259.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
