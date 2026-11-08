---

id: tv_profile_gy4ilk5n

name: "Momentum-based ZigZag (incl. QQE) NON-REPAINTING"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Confirm zigzag swings from momentum reversals rather than waiting a fixed number of bars after a candidate pivot."

registry_key: null

runner: null

evaluation: null

---

# Momentum-based ZigZag (incl. QQE) NON-REPAINTING

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Confirm zigzag swings from momentum reversals rather than waiting a fixed number of bars after a candidate pivot.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Each momentum reversal test, high/low interval, strength calculation and intrabar-versus-close confirmation are not provided.

- Each momentum reversal test, high/low interval, strength calculation and intrabar-versus-close confirmation are not provided.

## How it works

- Select a momentum measure such as MACD, an average or QQE. When it reverses, capture the highest/lowest price of the completed impulse and print the zigzag; also flag impulse strength.

## Outputs and intended use

- Use the plotted structure and strength markings to compare impulses. The author emphasizes marking pivots when noticed rather than backdating their detection.

## Parameters and stated settings

- A momentum-indicator selector is disclosed, but component lengths, QQE modifications, strength thresholds and defaults are absent.

## Failure modes and caveats

- The author strongly claims non-repainting; that remains an unverified claim without code/live testing. Momentum reversal confirmation can still lag and produce false turns in choppy markets.

## Missing information and implementation boundary

- Each momentum reversal test, high/low interval, strength calculation and intrabar-versus-close confirmation are not provided.

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
once it reverses, a highest (or lowest) point from the impulse is caught and ZigZag gets printed.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
my indicator prints pivot points and Zigzag exactly on the moment they have been noticed, not earlier faking to be faster than they could be.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
As a bonus, the indicator marks which impulse had strength in it.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gy4ilk5n_momentum_based_zigzag_incl_qqe_non_repainting](../tv_gy4ilk5n_momentum_based_zigzag_incl_qqe_non_repainting.md)

## Source

https://www.tradingview.com/script/gY4ilk5N-Momentum-based-ZigZag-incl-QQE-NON-REPAINTING/

Publication ID: gY4ilk5N. Source SHA-256: e744941bb3641c8c3a5bbab4f3b72617ab839577c356ef614fbdcd0044676a5e. Raw-description SHA-256: 588eeaf039dcc60637217aadc1a364b345011e09b2f78c6bca72e050d23a2fba.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
