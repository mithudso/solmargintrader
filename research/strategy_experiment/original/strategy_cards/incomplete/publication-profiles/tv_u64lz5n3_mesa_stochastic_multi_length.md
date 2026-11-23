---

id: tv_profile_u64lz5n3

name: "MESA Stochastic Multi Length"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "MESA Stochastic Multi Length displays several Ehlers-style super-smoothed stochastic variants together to inspect market waves. The author proposes looking for tops/bottoms and combining the study with another indicator, but the source mostly relies on linked chart examples for signals. Its stated benefits should be treated as intended uses rather than measured pump/dump detection accuracy."

registry_key: null

runner: null

evaluation: null

---

# MESA Stochastic Multi Length

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

MESA Stochastic Multi Length displays several Ehlers-style super-smoothed stochastic variants together to inspect market waves. The author proposes looking for tops/bottoms and combining the study with another indicator, but the source mostly relies on linked chart examples for signals. Its stated benefits should be treated as intended uses rather than measured pump/dump detection accuracy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** MESA stochastic equations, selected lengths, super-smoother settings and actionable signal/exit rules are absent.

- MESA stochastic equations, selected lengths, super-smoother settings and actionable signal/exit rules are absent.

## How it works

- Apply MESA stochastic super-smoothing at multiple lengths and display the resulting oscillator series together.

## Outputs and intended use

- Compare waves at the different lengths for discretionary turn analysis and confirmation with other tools.

## Parameters and stated settings

- Four lengths are shown; their values, thresholds, smoothing coefficients and defaults are not stated.

## Failure modes and caveats

- Analytical: multiple correlated stochastic lines can whipsaw together and extreme readings can persist during trends.

## Missing information and implementation boundary

- MESA stochastic equations, selected lengths, super-smoother settings and actionable signal/exit rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
uses super smoothing
```

### E2: parameters, readiness

```text
4 different lengths displayed
```

### E3: outputs_and_use, readiness

```text
analyze waves and find tops and bottoms.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_u64lz5n3_mesa_stochastic_multi_length](../tv_u64lz5n3_mesa_stochastic_multi_length.md)

## Source

https://www.tradingview.com/script/u64LZ5N3-MESA-Stochastic-Multi-Length/

Publication ID: u64LZ5N3. Source SHA-256: adc0e0a8f90887bcc92563e35fe8c1b7ae85361e1de636d002814bfb850c76a5. Raw-description SHA-256: 04ebe852f99a5127bddf5a6b4d677a9978845f09403c617cdb99f99b1e848bcc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
