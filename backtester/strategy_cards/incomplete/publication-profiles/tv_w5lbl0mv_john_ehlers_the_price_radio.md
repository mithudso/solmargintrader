---

id: tv_profile_w5lbl0mv

name: "John Ehlers - The Price Radio"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "The Price Radio applies a signal-processing metaphor to financial prices: treat the price curve as a radio wave and use amplitude/frequency demodulation to separate useful behavior from noise. The description identifies the conceptual technique and its Ehlers article origin, but provides no filter equations, parameterization or signal definitions. It is retained as a financial research indicator because its purpose is explicitly trade-signal extraction. A faithful explanation cannot turn the radio analogy into an invented Hilbert transform, oscillator formula or entry rule without the missing implementation."

registry_key: null

runner: null

evaluation: null

---

# John Ehlers - The Price Radio

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

The Price Radio applies a signal-processing metaphor to financial prices: treat the price curve as a radio wave and use amplitude/frequency demodulation to separate useful behavior from noise. The description identifies the conceptual technique and its Ehlers article origin, but provides no filter equations, parameterization or signal definitions. It is retained as a financial research indicator because its purpose is explicitly trade-signal extraction. A faithful explanation cannot turn the radio analogy into an invented Hilbert transform, oscillator formula or entry rule without the missing implementation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core AM/FM demodulation and signal-output algorithms are undisclosed.

## How it works

- Apply unspecified AM and FM demodulation techniques to the price curve.

## Outputs and intended use

- Intended output is noise-separated trade information; actual plots and interpretation are not described.

## Parameters and stated settings

- No parameter names or defaults are supplied.

## Failure modes and caveats

- Signal/noise separation is model-dependent and can introduce lag or artifacts.
- The analogy does not establish predictive content.

## Missing information and implementation boundary

- Demodulation equations, preprocessing, frequencies/windows, output mapping and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed input is a financial price curve, available as OHLCV data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Treat the price curve like a radio wave. Apply AM and FM demodulating technology
```

### E2: purpose, outputs_and_use

```text
separating trade signals from the underlying noise.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_w5lbl0mv_john_ehlers_the_price_radio](../tv_w5lbl0mv_john_ehlers_the_price_radio.md)

## Source

https://www.tradingview.com/script/W5lBL0MV-John-Ehlers-The-Price-Radio/

Publication ID: W5lBL0MV. Source SHA-256: 6ab7c4302707984442ff8f047c520fe7a95ae4abd090d2a4d2a2cf3940a63e81. Raw-description SHA-256: 961e3ff5d042e77d39ba8dda3e4bfd5fafae61970408b9cd9cf0ad907669691c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
