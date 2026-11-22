---

id: tv_profile_dogvqoph

name: "Stochastic Weights - Basic [BigBitsIO]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Stochastic Weights combines enabled oscillator components into a shared consensus reading. The design tries to temper a fast stochastic-RSI measure with a slower stochastic measure, so disagreement produces an intermediate level rather than allowing the fastest component alone to dominate. It is an equally weighted blend of selected K-like readings, not a fitted weighting model or proof that oscillator agreement creates a stronger predictive edge."

registry_key: null

runner: null

evaluation: null

---

# Stochastic Weights - Basic [BigBitsIO]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Stochastic Weights combines enabled oscillator components into a shared consensus reading. The design tries to temper a fast stochastic-RSI measure with a slower stochastic measure, so disagreement produces an intermediate level rather than allowing the fastest component alone to dominate. It is an equally weighted blend of selected K-like readings, not a fitted weighting model or proof that oscillator agreement creates a stronger predictive edge.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The equal arithmetic mean of enabled standard stochastic/StochRSI K values defines the principal consensus output; custom variants and D smoothing need separate definitions.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate enabled stochastic-family components and optional RSI, then equally average their K contributions.
- Calculate D as a moving average of the blended K rather than blending separate D lines.

## Outputs and intended use

- Read the aggregate K/D display for alignment or disagreement among the selected components; high agreement is offered as a possible stronger signal context.

## Parameters and stated settings

- Stochastic and Stochastic RSI are enabled by default; other stochastic variants and RSI can be included.
- The example averages 100 and 50 to 75; adding RSI 50 gives approximately 67. No lookback or D-smoothing defaults are supplied.

## Failure modes and caveats

- Analytical: correlated components can create apparent confirmation without independent information; averaging can dilute an informative extreme.

## Missing information and implementation boundary

- Custom stochastic equations, component scales, D average type/length and entry/exit thresholds are not documented.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Stochastic and Stochastic RSI are both enabled
```

### E2: mechanism, readiness

```text
Only the K value is weighted, as the D value is just a moving average of the weighted K.
```

### E3: parameters, readiness

```text
If Stochastic RSI is 100 and Stochastic is 50, K would be 75
```

### E4: parameters, readiness

```text
If you add in a 50 RSI, the K would be 67
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dogvqoph_stochastic_weights_basic_bigbitsio](../tv_dogvqoph_stochastic_weights_basic_bigbitsio.md)

## Source

https://www.tradingview.com/script/DOgvQOPh-Stochastic-Weights-Basic-BigBitsIO/

Publication ID: DOgvQOPh. Source SHA-256: 307ad57a028dc571519d4f7fd83568232f29ffc9e967871b030990b15b2d3676. Raw-description SHA-256: eec85e77a2bb23be2f9438c3ac53cf59e274bf260bca35181586ddc781590908.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
