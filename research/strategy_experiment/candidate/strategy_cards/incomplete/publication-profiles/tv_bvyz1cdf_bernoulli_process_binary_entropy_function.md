---

id: tv_profile_bvyz1cdf

name: "Bernoulli Process - Binary Entropy Function"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Bernoulli Process Binary Entropy compares information-theory-style measurements of price and volume. It aims to produce a MACD-like difference and histogram for discretionary divergence inspection, with individual price/volume measures optionally visible. The source invokes Bernoulli and Shannon entropy but never defines how continuous market observations become binary probabilities. Its statements about volume leading price, Nyquist limits and sigma significance are author assertions rather than established properties of the disclosed calculation."

registry_key: null

runner: null

evaluation: null

---

# Bernoulli Process - Binary Entropy Function

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Bernoulli Process Binary Entropy compares information-theory-style measurements of price and volume. It aims to produce a MACD-like difference and histogram for discretionary divergence inspection, with individual price/volume measures optionally visible. The source invokes Bernoulli and Shannon entropy but never defines how continuous market observations become binary probabilities. Its statements about volume leading price, Nyquist limits and sigma significance are author assertions rather than established properties of the disclosed calculation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Binary probability construction and entropy/signal normalization are not specified.

## How it works

- Calculate an unspecified binary-entropy measure separately for price and volume, with an averaging summation.
- Subtract volume entropy from price entropy and flag high-ranked information states.

## Outputs and intended use

- Difference histogram and optional component plots support exploratory divergence analysis.

## Parameters and stated settings

- Suggested entropy lengths 9–22; shorter examples 7/9/11.
- Source cautions below length5 and describes a 5%/two-sigma highlight adjustable with Percent Rank.

## Failure modes and caveats

- Entropy does not directly measure predictability or trading edge.
- Percentile and sigma significance are not interchangeable without distribution assumptions.

## Missing information and implementation boundary

- Binary event/probability definition, entropy equations, summation/percent-rank mapping, defaults and signal rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The declared inputs are price and volume; their unavailable transformations are algorithm gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
values between 9 and 22
```

### E2: parameters

```text
below a length of 5
```

### E3: parameters, risks

```text
5% level (2 sigma)
```

### E4: parameters

```text
shorter time frames (7, 9, 11)
```

### E5: mechanism

```text
subtracted the volume from the price
```

### E6: readiness

```text
Binary Entropy measurement
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bvyz1cdf_bernoulli_process_binary_entropy_function](../tv_bvyz1cdf_bernoulli_process_binary_entropy_function.md)

## Source

https://www.tradingview.com/script/bvYZ1CdF-Bernoulli-Process-Binary-Entropy-Function/

Publication ID: bvYZ1CdF. Source SHA-256: 6c5517b0dd188174956f428ca742fbac6d4e9d2898f9af1702153d92c2742d42. Raw-description SHA-256: e29ea7616c0181a73562b4a77a2164fc77a57b891e0abfe519911cc3b09e144d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
