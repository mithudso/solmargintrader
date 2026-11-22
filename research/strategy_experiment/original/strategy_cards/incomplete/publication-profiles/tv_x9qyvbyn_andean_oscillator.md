---

id: tv_profile_x9qyvbyn

name: "Andean Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Andean Oscillator separates directional price variation into bull and bear components using exponential envelopes of prices and squared prices. It aims to show both trend direction and variation amplitude, with an additional signal line to filter component crosses. The source’s descriptions of which envelope creates bull versus bear must be retained as written rather than silently corrected to an assumed implementation."

registry_key: null

runner: null

evaluation: null

---

# Andean Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Andean Oscillator separates directional price variation into bull and bear components using exponential envelopes of prices and squared prices. It aims to show both trend direction and variation amplitude, with an additional signal line to filter component crosses. The source’s descriptions of which envelope creates bull versus bear must be retained as written rather than silently corrected to an assumed implementation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Envelope recursion/alpha, initialization, signal-line input/type and numerical safeguards are missing.

- Envelope recursion/alpha, initialization, signal-line input/type and numerical safeguards are missing.

## How it works

- Build upper/lower exponential envelopes for ordinary and squared prices, subtract squared ordinary-envelope values from squared-price envelope values and take square roots.
- The prose assigns upper-envelope variation to bull and lower-envelope variation to bear; smooth a signal line for additional cross interpretation.

## Outputs and intended use

- Green bull over red bear is interpreted as uptrend and the reverse as downtrend; author suggests component/signal crosses as a stronger filter than component crosses alone.

## Parameters and stated settings

- Length controls variation significance and Signal Length the signal average; no defaults or average type are given.

## Failure modes and caveats

- Analytical: naive second-moment subtraction can suffer cancellation/negative roundoff, and crossing signals can whipsaw; narrative envelope assignment needs code verification.

## Missing information and implementation boundary

- Envelope recursion/alpha, initialization, signal-line input/type and numerical safeguards are missing.

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
exponential envelopes are obtained from both the regular prices and squared prices
```

### E2: mechanism, readiness

```text
bullish component is obtained by first subtracting the upper extremity
```

### E3: mechanism, readiness

```text
bearish component is obtained in the same way, but makes use of the lower extremities
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_x9qyvbyn_andean_oscillator](../tv_x9qyvbyn_andean_oscillator.md)

## Source

https://www.tradingview.com/script/x9qYvBYN-Andean-Oscillator/

Publication ID: x9qYvBYN. Source SHA-256: 961c839b96816a2984f87179e7ec8f27c75fe45f8d5842edc3214b036e8b443c. Raw-description SHA-256: af84ab853ef8ffeb7f63ed1d95b54b78099f2a36f07d87ef0810a72d2423c941.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
