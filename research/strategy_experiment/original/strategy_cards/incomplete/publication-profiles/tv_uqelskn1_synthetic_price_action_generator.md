---

id: tv_profile_uqelskn1

name: "Synthetic Price Action Generator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Generate controllable synthetic candles for developing and stress-testing trading indicators without depending on a particular market history."

registry_key: null

runner: null

evaluation: null

---

# Synthetic Price Action Generator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Generate controllable synthetic candles for developing and stress-testing trading indicators without depending on a particular market history.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The tool is financially relevant testing infrastructure, but the synthetic data-generating process is not specified.

- Random generator and seed
- OHLC construction/constraints
- EMA periods and initialization

## How it works

- Produce randomized OHLC-like values with three EMAs managing close/high/low randomness. Allow parameter changes to create ordinary-looking formations or extreme wicks/bodies, and temporarily substitute generated series for built-in market variables in a test script.

## Outputs and intended use

- Use the artificial environment to inspect initialization, recursive-filter ringing and rare-condition behavior. The author explicitly warns that these values are fake and must not drive trading; the intended financial-testing purpose keeps it in scope.

## Parameters and stated settings

- Generator settings have comfort-zone bounds but their values, seeds and exact smoothing periods are not listed. Candle plotting can be shown/hidden and code insertion boundaries are provided in the unavailable source.

## Failure modes and caveats

- Synthetic resemblance to fractal price patterns does not validate market realism or forecast performance. Variable shadowing can accidentally contaminate a live indicator if test substitutions remain.

## Missing information and implementation boundary

- Random process, seed/reproducibility, OHLC constraints, EMA recurrence/initialization and parameter ranges are missing.

## Data requirements

Required inputs: random generator state and configuration.

Repository input-class support: available. The tool generates synthetic observations and intrinsically needs no external market feed; exact generator implementation is still missing.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
3 EMAs are employed to manage and maintain randomness of CLOSE, HIGH, and LOW.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
testing and troubleshooting indicators AND evaluating how they perform in a "manageable" randomized environment.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Always remember to fully remove this scripts' code and those assignments properly before actual trading use
```

## Source

https://www.tradingview.com/script/uqelSkN1-Synthetic-Price-Action-Generator/

Publication ID: uqelSkN1. Source SHA-256: 8f88cbd1108da71aaae5ca82cc18027cf7a69ae7d251ddadd1af43f93bad99b1. Raw-description SHA-256: a29e009353c7ea08b9163a33bf9f74df88796ba488239a3c96aa4acfe0093087.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
