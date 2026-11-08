---

id: tv_profile_pco280uj

name: "LSMA - A Fast And Simple Alternative Calculation"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This publication derives a simpler calculation for the least-squares moving average by expressing its linear-filter weights as a combination of WMA and SMA. The purpose is computational simplification of a familiar trend smoother, rather than a new forecast signal. The author notes that regression extrapolation is rarely accurate and favors smoothing use; the claimed numerical match is described from source examples and is not independently benchmarked here."

registry_key: null

runner: null

evaluation: null

---

# LSMA - A Fast And Simple Alternative Calculation

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This publication derives a simpler calculation for the least-squares moving average by expressing its linear-filter weights as a combination of WMA and SMA. The purpose is computational simplification of a familiar trend smoother, rather than a new forecast signal. The author notes that regression extrapolation is rarely accurate and favors smoothing use; the claimed numerical match is described from source examples and is not independently benchmarked here.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The equal-period identity 3WMA minus2SMA explicitly defines the LSMA output.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Represent the rolling linear-regression endpoint with a linear combination of equal-period WMA and SMA.
- Use negative effective weights to match the LSMA impulse response and reduce lag relative to an ordinary positive-weight average.

## Outputs and intended use

- Use the resulting LSMA as a trend-smoothing reference or reusable calculation; no entry/exit rule is specified.

## Parameters and stated settings

- The disclosed identity is LSMA = 3WMA - 2SMA, equivalently WMA + 2(WMA - SMA). All averages use the same period; no default length is stated.

## Failure modes and caveats

- Analytical: negative filter weights can overshoot near changes; computational equivalence does not establish predictive accuracy.

## Missing information and implementation boundary

- Exact WMA orientation, initialization/warmup, supported input series and empirical runtime/numerical parity require code verification.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; source-code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
LSMA = 3WMA - 2SMA = WMA + 2(WMA - SMA)
```

### E2: purpose, risks, readiness

```text
such forecast is rarely accurate and the LSMA is mostly used as a smoother.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_builtin_least_squares_moving_average](../../tv_builtin_least_squares_moving_average.md)

## Source

https://www.tradingview.com/script/PcO280uj-LSMA-A-Fast-And-Simple-Alternative-Calculation/

Publication ID: PcO280uj. Source SHA-256: 017fe1526444275faffe4b2ee2e568774cd4198a6c6676ed1913a07ecaf2a247. Raw-description SHA-256: 7e9e6fd6f7210ad1d07f89553630bb0f95a4a29046c137cb2a9e2fe88bdd1a96.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
